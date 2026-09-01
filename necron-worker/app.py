"""
Necron GPU Worker
Unified inference server running on the club's GPU workstation.
Reachable only over the private network AND only with a valid WORKER_TOKEN
bearer header; see the Authentication note below.

Handles:
  GET  /status              -> GPU/job status
  POST /sentiment/analyze   -> single headline
  POST /sentiment/batch     -> up to 20 headlines
  POST /classify            -> image classification (multipart)
"""
import io
import os
import sys
import hmac
import base64
import threading
import urllib.request
import time
from pathlib import Path
from flask import Flask, request, jsonify
from PIL import Image
import torch

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024 * 1024
# Cap decoded pixels so a small huge-dimension upload can't exhaust GPU-box RAM.
Image.MAX_IMAGE_PIXELS = 50_000_000  # ~50 MP

# ── Authentication ───────────────────────────────────────────────────────────
# Every route requires a shared bearer token, checked below in _require_token.
#
# The network boundary is NOT the security boundary. That was the lesson of the
# July 2026 compromise: reaching the private network was made equivalent to full
# control of this box, so one stolen SSH key was enough. Anything that can route
# to port 15100 must still prove it holds the token before it can queue GPU work.
#
# Set WORKER_TOKEN in the worker's .env and in the calling app's .env. Generate
# one with:  python3 -c "import secrets; print(secrets.token_urlsafe(32))"
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
# Escape hatch for someone poking at the worker on the GPU box itself. It must be
# set deliberately; it is never the default, so a missing token fails closed.
ALLOW_NO_AUTH = os.environ.get("WORKER_ALLOW_NO_AUTH") == "1"

if not WORKER_TOKEN and not ALLOW_NO_AUTH:
    sys.exit(
        "necron-worker: refusing to start with no WORKER_TOKEN.\n"
        "  Set WORKER_TOKEN in the worker's .env (and in each app that calls it):\n"
        '    python3 -c "import secrets; print(secrets.token_urlsafe(32))"\n'
        "  For a deliberate local no-auth run, set WORKER_ALLOW_NO_AUTH=1."
    )


@app.before_request
def _require_token():
    if ALLOW_NO_AUTH:
        return None
    header = request.headers.get("Authorization", "")
    presented = header[7:] if header.startswith("Bearer ") else ""
    # compare_digest, not ==, so a wrong token cannot be recovered by timing.
    if not hmac.compare_digest(presented, WORKER_TOKEN):
        return jsonify({"error": "Unauthorized"}), 401
    return None

# ── Job tracking ─────────────────────────────────────────────────────────────
_lock        = threading.Lock()
_active_jobs = 0
_last_model  = ""


def job_start(model_name: str = ""):
    global _active_jobs, _last_model
    with _lock:
        _active_jobs += 1
        if model_name:
            _last_model = model_name


def job_end():
    global _active_jobs
    with _lock:
        _active_jobs = max(0, _active_jobs - 1)


# ── GPU info ──────────────────────────────────────────────────────────────────
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
GPU_NAME = (
    torch.cuda.get_device_name(0) if torch.cuda.is_available() else "CPU"
)

# Streaming-multiprocessor count of the real device, read once. Used to derive a
# live FP32 TFLOPS figure from the current clock (honest: device props x clock,
# not a hardcoded spec sheet). 128 FP32 cores/SM x 2 flops/FMA.
_SM_COUNT = (
    torch.cuda.get_device_properties(0).multi_processor_count
    if torch.cuda.is_available() else 0
)

# Utilization comes from nvidia-smi, cached briefly because /status is polled
# by every open page on the public site.
_util_lock = threading.Lock()
_util_cache = {"t": 0.0, "util": None, "mem_used": None, "mem_total": None,
               "occupied": None}


def _num(x):
    """Parse one nvidia-smi cell to int, or None if it is '[N/A]' etc."""
    try:
        return int(float(x.strip()))
    except (ValueError, AttributeError):
        return None


def _vast_rented():
    """True when a vast.ai renter is actively on the box. The vast host daemon
    launches each rental as a docker container named 'C.<contract_id>', so the
    presence of one is the authoritative 'the GPU is rented right now' signal —
    distinct from our own jobs or the background miner, which both also use the
    card. Returns None when docker can't be queried (shown as 'unknown')."""
    import subprocess, re
    try:
        out = subprocess.run(
            ["sudo", "-n", "docker", "ps", "--format", "{{.Names}}"],
            capture_output=True, text=True, timeout=4,
        )
    except Exception:
        return None
    if out.returncode != 0:
        return None
    return any(re.match(r"C\.\d+", n.strip()) for n in out.stdout.splitlines())


_uptime_cache = {"t": 0.0, "pct": None, "days": None}


def _uptime_refresh():
    """Compute 7-day uptime from the journal's boot sessions (gaps between them
    are downtime): an aggregate percentage plus a per-day breakdown (7 values,
    oldest first) for the sparkline. Cached 60s since it barely moves."""
    now = time.time()
    if _uptime_cache["pct"] is not None and now - _uptime_cache["t"] < 60:
        return
    import subprocess, json
    try:
        boots = json.loads(subprocess.run(
            ["journalctl", "--list-boots", "-o", "json"],
            capture_output=True, text=True, timeout=8).stdout)
        maxidx = max(b["index"] for b in boots)
        # The current boot is still running, so its real end is "now".
        intervals = [(b["first_entry"] / 1e6,
                      now if b["index"] == maxidx else b["last_entry"] / 1e6)
                     for b in boots]

        def up_in(lo, hi):
            return sum(max(0.0, min(e, hi) - max(s, lo)) for s, e in intervals)

        pct = round(min(100.0, up_in(now - 7 * 86400, now) / (7 * 86400) * 100), 2)
        days = [round(min(100.0, up_in(now - k * 86400, now - (k - 1) * 86400)
                          / 86400 * 100), 1)
                for k in range(7, 0, -1)]
    except Exception:
        pct, days = None, None
    _uptime_cache.update(t=now, pct=pct, days=days)


def _uptime():
    _uptime_refresh()
    return _uptime_cache["pct"]


def _uptime_days():
    _uptime_refresh()
    return _uptime_cache["days"]


def gpu_utilization():
    import subprocess
    with _util_lock:
        now = time.time()
        # 1s cap: fresh enough for the live popup, while still bounding nvidia-smi
        # to at most once per second no matter how many viewers are polling.
        if now - _util_cache["t"] < 1:
            return _util_cache
        try:
            out = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=utilization.gpu,memory.used,memory.total,"
                 "power.draw,power.limit,temperature.gpu,fan.speed,"
                 "clocks.current.sm,utilization.memory",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=4,
            ).stdout.strip().splitlines()[0]
            p = [c.strip() for c in out.split(",")]
            util, mem_used, mem_total = _num(p[0]), _num(p[1]), _num(p[2])
            power, power_limit, temp, fan = _num(p[3]), _num(p[4]), _num(p[5]), _num(p[6])
            sm_clock, mem_util = _num(p[7]), _num(p[8])
            tflops = (round(_SM_COUNT * 128 * 2 * sm_clock * 1e6 / 1e12, 1)
                      if sm_clock and _SM_COUNT else None)
            _util_cache.update(
                t=now, util=util, mem_used=mem_used, mem_total=mem_total,
                power=power, power_limit=power_limit, temp=temp, fan=fan,
                sm_clock=sm_clock, mem_util=mem_util, tflops=tflops)
        except Exception:
            _util_cache.update(
                t=now, util=None, mem_used=None, mem_total=None,
                power=None, power_limit=None, temp=None, fan=None,
                sm_clock=None, mem_util=None, tflops=None)
        # Vast.ai rental state shares the 1s cache budget (it drives the "occ" dot).
        _util_cache["occupied"] = _vast_rented()
        return _util_cache


# ── Sentiment model ───────────────────────────────────────────────────────────
_sentiment_pipeline = None
_sentiment_lock = threading.Lock()

SENTIMENT_LABEL_MAP = {
    "positive": ("Bullish", "#4ade80"),
    "neutral":  ("Neutral", "#fbbf24"),
    "negative": ("Bearish", "#f87171"),
}


def get_sentiment_pipeline():
    global _sentiment_pipeline
    with _sentiment_lock:
        if _sentiment_pipeline is None:
            from transformers import pipeline
            _sentiment_pipeline = pipeline(
                "text-classification",
                model="mrm8488/distilroberta-finetuned-financial-news-sentiment-analysis",
                top_k=None,
                device=0 if torch.cuda.is_available() else -1,
            )
    return _sentiment_pipeline


def score_text(text: str) -> dict:
    nlp = get_sentiment_pipeline()
    results = nlp(text[:512])[0]
    scores = {r["label"].lower(): round(r["score"] * 100, 1) for r in results}
    top = max(scores, key=scores.get)
    label, color = SENTIMENT_LABEL_MAP.get(top, ("Neutral", "#fbbf24"))
    return {
        "label": label,
        "color": color,
        "scores": {
            "Bullish": scores.get("positive", 0),
            "Neutral":  scores.get("neutral",  0),
            "Bearish":  scores.get("negative", 0),
        },
    }


# ── Image classification models ───────────────────────────────────────────────
from torchvision.models import (
    resnet50,      ResNet50_Weights,
    mobilenet_v3_large, MobileNet_V3_Large_Weights,
    efficientnet_b0, EfficientNet_B0_Weights,
)

_classifier_models: dict = {}
_classifier_lock = threading.Lock()

IMAGENET_LABELS_URL = (
    "https://raw.githubusercontent.com/pytorch/hub/master/imagenet_classes.txt"
)
_LABELS_CACHE = Path(".imagenet_labels.txt")


def get_labels() -> list[str]:
    if not _LABELS_CACHE.exists():
        urllib.request.urlretrieve(IMAGENET_LABELS_URL, _LABELS_CACHE)
    return _LABELS_CACHE.read_text().strip().splitlines()


LABELS = get_labels()


def get_classifier(name: str):
    with _classifier_lock:
        if name not in _classifier_models:
            if name == "resnet50":
                w = ResNet50_Weights.IMAGENET1K_V2
                m = resnet50(weights=w).to(DEVICE).eval()
            elif name == "mobilenet":
                w = MobileNet_V3_Large_Weights.IMAGENET1K_V2
                m = mobilenet_v3_large(weights=w).to(DEVICE).eval()
            elif name == "efficientnet":
                w = EfficientNet_B0_Weights.IMAGENET1K_V1
                m = efficientnet_b0(weights=w).to(DEVICE).eval()
            else:
                raise ValueError(f"Unknown model: {name}")
            _classifier_models[name] = (m, w.transforms())
    return _classifier_models[name]


def classify_image(img: Image.Image, model_name: str = "resnet50", top_n: int = 10) -> list[dict]:
    model, preprocess = get_classifier(model_name)
    tensor = preprocess(img.convert("RGB")).unsqueeze(0).to(DEVICE)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1)[0]
    topk = probs.topk(min(top_n, len(LABELS)))
    return [
        {"label": LABELS[idx], "confidence": round(prob.item() * 100, 2)}
        for prob, idx in zip(topk.values, topk.indices)
    ]


def make_thumb(img: Image.Image, max_dim: int = 600) -> str:
    thumb = img.copy()
    thumb.thumbnail((max_dim, max_dim))
    buf = io.BytesIO()
    thumb.convert("RGB").save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/status")
def status():
    with _lock:
        jobs = _active_jobs
        model = _last_model
    u = gpu_utilization()
    # Busy when our own queue is working OR when anything else (e.g. a
    # vast.ai rental) is loading the GPU past a meaningful threshold.
    external_load = u["util"] is not None and u["util"] >= 25
    state = "busy" if (jobs > 0 or external_load) else "ready"
    return jsonify({
        "status":      state,
        "gpu":         GPU_NAME,
        "device":      str(DEVICE),
        "active_jobs": jobs,
        "last_model":  model,
        "util":        u["util"],
        "mem_used":    u["mem_used"],
        "mem_total":   u["mem_total"],
        "power":       u.get("power"),
        "power_limit": u.get("power_limit"),
        "temp":        u.get("temp"),
        "fan":         u.get("fan"),
        "sm_clock":    u.get("sm_clock"),
        "mem_util":    u.get("mem_util"),
        "tflops":      u.get("tflops"),
        "uptime":      _uptime(),
        "uptime_days": _uptime_days(),
        "occupied":    u.get("occupied"),
    })


@app.route("/sentiment/analyze", methods=["POST"])
def sentiment_analyze():
    data = request.get_json(force=True)
    text = (data.get("text") or "").strip()
    if not text:
        return jsonify({"error": "No text provided"}), 400
    if len(text) > 1000:
        return jsonify({"error": "Text too long (max 1000 chars)"}), 400
    job_start("sentiment")
    try:
        return jsonify(score_text(text))
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        job_end()


@app.route("/sentiment/batch", methods=["POST"])
def sentiment_batch():
    data = request.get_json(force=True)
    headlines = [h.strip() for h in (data.get("headlines") or []) if h.strip()][:20]
    if not headlines:
        return jsonify({"error": "No headlines provided"}), 400
    job_start("sentiment-batch")
    try:
        results = []
        bull_total = neu_total = bear_total = 0.0
        for h in headlines:
            r = score_text(h)
            results.append({"text": h, **r})
            bull_total += r["scores"]["Bullish"]
            neu_total  += r["scores"]["Neutral"]
            bear_total += r["scores"]["Bearish"]
        n = len(results)
        aggregate = {
            "Bullish": round(bull_total / n, 1),
            "Neutral":  round(neu_total  / n, 1),
            "Bearish":  round(bear_total / n, 1),
        }
        top = max(aggregate, key=aggregate.get)
        agg_label, agg_color = {
            "Bullish": ("Bullish", "#4ade80"),
            "Neutral":  ("Neutral",  "#fbbf24"),
            "Bearish":  ("Bearish",  "#f87171"),
        }[top]
        return jsonify({
            "results":         results,
            "aggregate":       aggregate,
            "aggregate_label": agg_label,
            "aggregate_color": agg_color,
            "count":           n,
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        job_end()


@app.route("/classify", methods=["POST"])
def classify_route():
    model_name = request.form.get("model", "resnet50")
    top_n      = min(max(int(request.form.get("top_n", 10)), 1), 20)

    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    file = request.files["image"]
    raw  = file.read()
    try:
        img = Image.open(io.BytesIO(raw))
    except Exception:
        return jsonify({"error": "Could not open image"}), 400

    MAX_DIM = 1600
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    job_start(f"classify/{model_name}")
    try:
        predictions = classify_image(img, model_name, top_n)
        thumb_b64   = make_thumb(img)
        return jsonify({
            "predictions": predictions,
            "thumb":       thumb_b64,
            "info": {
                "width":   img.size[0],
                "height":  img.size[1],
                "size_kb": round(len(raw) / 1024, 1),
                "model":   model_name,
            },
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        job_end()


if __name__ == "__main__":
    # Loopback by default. README and setup.sh both promise this worker is never
    # exposed to the internet, but this entrypoint used to bind 0.0.0.0 and hand
    # that promise to whatever firewall happened to be in front of it. Production
    # runs under gunicorn bound to the private address by setup.sh; set
    # WORKER_BIND explicitly if you need that here.
    app.run(host=os.environ.get("WORKER_BIND", "127.0.0.1"), port=15100, debug=False)

# ── Generative job queue (SDXL-Turbo img2img + LTX image-to-video) ───────────
# GPU work is serialized through a single worker thread. Submitting returns a
# job id immediately; clients poll for status. This keeps every HTTP request
# short, which matters because Cloudflare cuts proxied requests at ~100 s.
import os
import shutil
import tempfile
import uuid
from collections import deque

from flask import send_file

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)
JOB_TTL = 3600  # results live for an hour

_jobs       = {}            # id -> dict(status, type, error, file, mime, created)
_job_queue  = deque()       # ids waiting to run
_queue_cond = threading.Condition()

_sd_pipe   = None  # SDXL-Turbo img2img (Style Transfer app)
_flux_pipe = None  # FLUX.1-dev text2img (Photo Editor app)
_flux_i2i  = None  # FLUX.1-dev img2img (Photo Editor, with a reference image)


def get_sd_pipe():
    """SDXL-Turbo img2img: much better output than sd-turbo, still seconds per image."""
    global _sd_pipe
    if _sd_pipe is None:
        from diffusers import AutoPipelineForImage2Image
        _sd_pipe = AutoPipelineForImage2Image.from_pretrained(
            "stabilityai/sdxl-turbo", torch_dtype=torch.float16, variant="fp16",
        ).to(DEVICE)
        _sd_pipe.set_progress_bar_config(disable=True)
    return _sd_pipe


FLUX_REPO = "black-forest-labs/FLUX.1-dev"   # 12B DiT + T5-XXL encoder (Photo Editor)


def get_flux_pipe():
    """FLUX.1-dev text-to-image. The 12B transformer is loaded in 4-bit NF4 and
    the T5-XXL text encoder in 8-bit (bitsandbytes), with model CPU offload, so
    it peaks ~12 GB and fits the 16 GB card while coexisting with the other GPU
    tools. The T5 encoder gives far stronger prompt adherence than SDXL's CLIP,
    which is the whole point of the upgrade."""
    global _flux_pipe
    if _flux_pipe is None:
        from diffusers import FluxPipeline, FluxTransformer2DModel
        from diffusers import BitsAndBytesConfig as DiffBnb
        from transformers import T5EncoderModel, BitsAndBytesConfig as TfBnb
        t5 = T5EncoderModel.from_pretrained(
            FLUX_REPO, subfolder="text_encoder_2",
            quantization_config=TfBnb(load_in_8bit=True), torch_dtype=torch.bfloat16,
        )
        tr = FluxTransformer2DModel.from_pretrained(
            FLUX_REPO, subfolder="transformer",
            quantization_config=DiffBnb(
                load_in_4bit=True, bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16,
            ),
            torch_dtype=torch.bfloat16,
        )
        p = FluxPipeline.from_pretrained(
            FLUX_REPO, transformer=tr, text_encoder_2=t5, torch_dtype=torch.bfloat16,
        )
        # CPU offload keeps each component on the GPU only while it runs, so FLUX
        # is a good citizen on the shared card (it sits in RAM between requests).
        p.enable_model_cpu_offload()
        p.set_progress_bar_config(disable=True)
        _flux_pipe = p
    return _flux_pipe


def get_flux_i2i():
    """FLUX.1-dev image-to-image, reusing the loaded text2img weights (shares the
    same offloaded modules, no extra VRAM) for visitor reference photos."""
    global _flux_i2i
    if _flux_i2i is None:
        from diffusers import FluxImg2ImgPipeline
        _flux_i2i = FluxImg2ImgPipeline(**get_flux_pipe().components)
        _flux_i2i.set_progress_bar_config(disable=True)
    return _flux_i2i


# ── Prompt rewriter (CPU) ───────────────────────────────────────────────────
# A small instruct model expands a short/vague user prompt into a clear, detailed
# one before it reaches FLUX, so the image lands closer to what the visitor meant.
# Runs on the CPU (Ryzen, 24 threads) so it never competes with FLUX for VRAM, and
# only ever ENRICHES — it must not invent new subjects or change the request.
_rewriter      = None
_rewriter_lock = threading.Lock()
REWRITER_REPO  = "bartowski/Qwen2.5-3B-Instruct-GGUF"
REWRITER_FILE  = "*Q4_K_M.gguf"

_REWRITE_SYSTEM = (
    "You expand a short image prompt into one clear, detailed prompt for a "
    "photorealistic text-to-image model. Keep the user's exact subject and intent. "
    "Add realistic detail they implied but did not state: lighting, setting, "
    "composition, and a photographic style. Do NOT add new subjects, and do NOT "
    "invent specific attributes (colors, brands, counts, text) the user did not "
    "give. Output ONE prompt under 55 words: no preamble, no quotes, no lists."
)


def _get_rewriter():
    global _rewriter
    with _rewriter_lock:
        if _rewriter is None:
            from llama_cpp import Llama
            _rewriter = Llama.from_pretrained(
                repo_id=REWRITER_REPO, filename=REWRITER_FILE,
                n_ctx=1024, n_threads=12, verbose=False,
            )
    return _rewriter


def _enhance_prompt(prompt: str) -> str:
    """Return an enriched version of `prompt`, or the original on any failure
    (missing model, load error, empty output) so generation never breaks."""
    prompt = (prompt or "").strip()
    if len(prompt) < 3:
        return prompt
    try:
        out = _get_rewriter().create_chat_completion(
            messages=[
                {"role": "system", "content": _REWRITE_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            max_tokens=110, temperature=0.6,
        )
        text = (out["choices"][0]["message"]["content"] or "").strip().strip('"')
        # Only accept a genuine expansion; otherwise keep the user's own words.
        return text if len(text) >= len(prompt) else prompt
    except Exception:
        return prompt


# ── External-GPU guard ──────────────────────────────────────────────────────
_extbusy_cache = {"t": 0.0, "busy": None}
_EXT_VRAM_BLOCK_MIB = 2500   # a non-worker process holding more than this blocks new jobs


def _external_compute_vram():
    """Total VRAM (MiB) held by GPU processes that are NOT our worker — vast.ai
    renters or any other running workload. The small background miner stays well
    under the block threshold, so it does not lock visitors out."""
    import subprocess, os, sys
    try:
        lines = subprocess.run(
            ["nvidia-smi", "--query-compute-apps=pid,process_name,used_memory",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=4,
        ).stdout.strip().splitlines()
    except Exception:
        return 0
    ours, our_exec, total = {os.getpid(), os.getppid()}, sys.executable, 0
    for line in lines:
        if not line.strip():
            continue
        parts = [c.strip() for c in line.split(",")]
        pid = _num(parts[0])
        name = parts[1] if len(parts) > 1 else ""
        if pid in ours or name == our_exec:
            continue
        total += _num(parts[2]) or 0
    return total


def _external_busy():
    """True when the GPU is in use by an external workload — an active vast.ai
    rental, or any non-worker process holding significant VRAM. New generative
    jobs are refused while this holds, so the club's demo tools never contend
    with (or OOM) a paying rental or another running process. Cached ~2s."""
    now = time.time()
    if _extbusy_cache["busy"] is not None and now - _extbusy_cache["t"] < 2:
        return _extbusy_cache["busy"]
    busy = bool(_vast_rented()) or _external_compute_vram() >= _EXT_VRAM_BLOCK_MIB
    _extbusy_cache.update(t=now, busy=busy)
    return busy


def _fit_image(img: Image.Image, max_side: int, multiple: int) -> Image.Image:
    w, h = img.size
    scale = min(max_side / max(w, h), 1.0)
    w, h = int(w * scale), int(h * scale)
    w -= w % multiple
    h -= h % multiple
    return img.resize((max(w, multiple), max(h, multiple)), Image.LANCZOS)


def _fit_image_box(img: Image.Image, long_side: int, short_side: int, multiple: int) -> Image.Image:
    """Fit within a long x short box (orientation-aware), snapped to multiples.
    Wan 2.2 TI2V-5B is trained at 1280x704; staying near that box is what
    produces its best output."""
    w, h = img.size
    box = (long_side, short_side) if w >= h else (short_side, long_side)
    scale = min(box[0] / w, box[1] / h)
    w, h = int(w * scale), int(h * scale)
    w -= w % multiple
    h -= h % multiple
    return img.resize((max(w, multiple), max(h, multiple)), Image.LANCZOS)


def _step_callback(job, span=(0, 100)):
    """diffusers callback_on_step_end that maps denoising progress onto a
    percentage span of the overall job."""
    lo, hi = span
    def cb(pipe, step, timestep, callback_kwargs):
        total = getattr(pipe, "num_timesteps", None) or 1
        job["progress"] = int(lo + (hi - lo) * (step + 1) / total)
        return callback_kwargs
    return cb


def _run_stylize(job):
    img      = Image.open(job["image_path"]).convert("RGB")
    img      = _fit_image(img, max_side=768, multiple=8)
    strength = job["strength"]
    pipe     = get_sd_pipe()
    # More steps = longer, cleaner renders; scaled with strength so low-strength
    # edits stay subtle and high-strength ones get the full treatment.
    steps = max(4, int(round(strength * 14)))
    out = pipe(
        prompt=job["prompt"], image=img,
        num_inference_steps=steps, strength=strength,
        guidance_scale=0.0,
        callback_on_step_end=_step_callback(job),
    ).images[0]
    path = RESULTS_DIR / f"{job['id']}.jpg"
    out.save(path, format="JPEG", quality=93)
    return str(path), "image/jpeg"


# FLUX.1-dev resolutions the Photo Editor offers (all multiples of 16, which the
# FLUX VAE requires). Wide enough to feel like a real online image tool.
_ASPECTS = {"square": (1024, 1024), "portrait": (832, 1216), "landscape": (1216, 832)}


def _run_generate(job):
    """Photo Editor: text-to-image, or image-to-image when the visitor gives a
    reference photo (the prompt then reshapes that photo). FLUX.1-dev is
    guidance-distilled, so it takes no negative prompt and uses a low guidance
    scale (~4.0); steps trade speed for fidelity."""
    # Enrich the visitor's prompt (CPU model) so FLUX has the detail it needs to
    # match intent; falls back to the original prompt if the rewriter is absent.
    prompt = _enhance_prompt(job["prompt"])
    job["enhanced_prompt"] = prompt
    ref = job.get("image_path")
    if ref and os.path.exists(ref):
        img = Image.open(ref).convert("RGB")
        img.load()
        img = _fit_image(img, max_side=1024, multiple=16)
        out = get_flux_i2i()(
            prompt=prompt, image=img,
            num_inference_steps=30, strength=job["strength"], guidance_scale=4.0,
            callback_on_step_end=_step_callback(job),
        ).images[0]
    else:
        out = get_flux_pipe()(
            prompt=prompt,
            num_inference_steps=24, guidance_scale=4.0,
            width=job.get("width", 1024), height=job.get("height", 1024),
            callback_on_step_end=_step_callback(job),
        ).images[0]
    path = RESULTS_DIR / f"{job['id']}.jpg"
    out.save(path, format="JPEG", quality=94)
    return str(path), "image/jpeg"


RUNNERS = {"stylize": _run_stylize, "generate": _run_generate}


def _make_room(job_type: str):
    """Keep only one generative model on the 16 GB card at a time. Drop the one
    the next job does not need; it reloads from the local cache when next used."""
    import gc
    global _sd_pipe, _flux_pipe, _flux_i2i
    if job_type == "generate" and _sd_pipe is not None:
        _sd_pipe = None
    elif job_type == "stylize" and _flux_pipe is not None:
        _flux_pipe = None
        _flux_i2i = None
    gc.collect()
    torch.cuda.empty_cache()


def _gpu_worker():
    while True:
        with _queue_cond:
            while not _job_queue:
                _queue_cond.wait()
            jid = _job_queue.popleft()
        job = _jobs.get(jid)
        if job is None:
            continue
        job["status"] = "running"
        job_start(f"{job['type']}/queued")
        try:
            _make_room(job["type"])
            path, mime = RUNNERS[job["type"]](job)
            job["file"], job["mime"] = path, mime
            job["status"] = "done"
        except Exception as e:
            job["status"] = "error"
            msg = str(e)
            if "out of memory" in msg.lower():
                # Usually another workload (a compute rental) is holding the
                # GPU. Free everything we still hold so we are not the one
                # blocking the card, and report it in plain language.
                global _sd_pipe, _flux_pipe, _flux_i2i
                _sd_pipe = None
                _flux_pipe = None
                _flux_i2i = None
                import gc
                gc.collect()
                torch.cuda.empty_cache()
                job["error"] = ("The club GPU is fully loaded by another workload "
                                "right now. Please try again in a little while.")
            else:
                job["error"] = msg[:300]
        finally:
            job_end()
            if job.get("image_path"):
                try:
                    os.unlink(job["image_path"])
                except OSError:
                    pass


threading.Thread(target=_gpu_worker, daemon=True).start()


def _cleanup_jobs():
    cutoff = time.time() - JOB_TTL
    for jid in [j for j, v in _jobs.items() if v["created"] < cutoff]:
        job = _jobs.pop(jid)
        if job.get("file"):
            try:
                os.unlink(job["file"])
            except OSError:
                pass


def _submit(job_type: str):
    if "image" not in request.files:
        return jsonify({"error": "No image provided"}), 400
    prompt = (request.form.get("prompt") or "").strip()[:400]
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    if _external_busy():
        return jsonify({
            "error": "The club GPU is currently in use by another workload. "
                     "Please try again in a little while.",
            "gpu_busy": True,
        }), 503

    _cleanup_jobs()
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".img")
    request.files["image"].save(tmp.name)
    tmp.close()

    jid = uuid.uuid4().hex[:12]
    _jobs[jid] = {
        "id": jid, "type": job_type, "status": "queued",
        "prompt": prompt, "image_path": tmp.name,
        "strength": max(0.3, min(0.9, float(request.form.get("strength", 0.6)))),
        "error": None, "file": None, "mime": None, "progress": 0,
        "created": time.time(),
    }
    with _queue_cond:
        _job_queue.append(jid)
        position = len(_job_queue)
        _queue_cond.notify()
    return jsonify({"job_id": jid, "position": position})


@app.route("/jobs/stylize", methods=["POST"])
def submit_stylize():
    return _submit("stylize")


@app.route("/jobs/generate", methods=["POST"])
def submit_generate():
    """Photo Editor: prompt required, reference image optional."""
    prompt = (request.form.get("prompt") or "").strip()[:500]
    if not prompt:
        return jsonify({"error": "No prompt provided"}), 400
    if _external_busy():
        return jsonify({
            "error": "The club GPU is currently in use by another workload. "
                     "Please try again in a little while.",
            "gpu_busy": True,
        }), 503
    _cleanup_jobs()
    image_path = None
    f = request.files.get("image")
    if f and f.filename:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".img")
        f.save(tmp.name)
        tmp.close()
        image_path = tmp.name
    w, h = _ASPECTS.get(request.form.get("aspect", "square"), (1024, 1024))
    jid = uuid.uuid4().hex[:12]
    _jobs[jid] = {
        "id": jid, "type": "generate", "status": "queued",
        "prompt": prompt, "image_path": image_path,
        "width": w, "height": h,
        "strength": max(0.25, min(0.85, float(request.form.get("strength", 0.6)))),
        "error": None, "file": None, "mime": None, "progress": 0,
        "created": time.time(),
    }
    with _queue_cond:
        _job_queue.append(jid)
        position = len(_job_queue)
        _queue_cond.notify()
    return jsonify({"job_id": jid, "position": position})


@app.route("/jobs/<jid>")
def job_status(jid):
    job = _jobs.get(jid)
    if job is None:
        return jsonify({"error": "Unknown or expired job"}), 404
    position = 0
    if job["status"] == "queued":
        with _queue_cond:
            try:
                position = list(_job_queue).index(jid) + 1
            except ValueError:
                position = 0
    return jsonify({
        "status":   job["status"],
        "position": position,
        "error":    job["error"],
        "progress": 100 if job["status"] == "done" else job.get("progress", 0),
        "enhanced": job.get("enhanced_prompt"),
    })


@app.route("/jobs/<jid>/result")
def job_result(jid):
    job = _jobs.get(jid)
    if job is None or job["status"] != "done":
        return jsonify({"error": "Result not ready"}), 404
    return send_file(job["file"], mimetype=job["mime"])
