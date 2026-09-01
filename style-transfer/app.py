"""
Art Style Transfer
Apply artistic effects to any uploaded image using PIL/NumPy algorithms.
No GPU required — runs on CPU only.
Also exposes /api/gpu-status which pings the necron GPU worker.
"""
import os
import io
import base64
import math
import re as _re
import time
import threading
import requests as http
from flask import Flask, render_template, request, jsonify
from PIL import Image, ImageFilter, ImageEnhance, ImageOps, ImageDraw
import numpy as np

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB
# Cap decoded pixel count so a small but huge-dimension upload can't blow up
# memory (decompression bomb). Pillow raises DecompressionBombError past this.
Image.MAX_IMAGE_PIXELS = 50_000_000  # ~50 MP

NECRON = os.environ.get("GPU_WORKER_URL", "http://gpu-worker:15100")
# Bearer token for the GPU worker. The worker refuses every request without it
# (see necron-worker/app.py); network reachability alone is not authorisation.
# Same value as WORKER_TOKEN in the worker's .env.
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
WORKER_AUTH = ({"Authorization": f"Bearer {WORKER_TOKEN}"} if WORKER_TOKEN else {})


# ── Style functions ──────────────────────────────────────────────────────────

def to_numpy(img: Image.Image) -> np.ndarray:
    return np.array(img.convert("RGB"), dtype=np.uint8)

def to_pil(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def style_pencil_sketch(img: Image.Image) -> Image.Image:
    """Classic pencil sketch using edge detection."""
    gray = img.convert("L")
    # Inverted blur subtraction for sketch look
    inverted = ImageOps.invert(gray)
    blurred  = inverted.filter(ImageFilter.GaussianBlur(radius=12))
    blurred_inv = ImageOps.invert(blurred)
    arr_gray = np.array(gray, dtype=np.float32)
    arr_blur = np.array(blurred_inv, dtype=np.float32)
    sketch = arr_gray / (256.0 - arr_blur + 1e-6) * 256.0
    sketch = np.clip(sketch, 0, 255).astype(np.uint8)
    result = Image.fromarray(sketch).convert("RGB")
    return result


def style_watercolor(img: Image.Image) -> Image.Image:
    """Watercolor painterly effect using bilateral-style blur + saturation boost."""
    arr = to_numpy(img)
    # Repeated median-like smoothing with PIL
    smooth = img.filter(ImageFilter.MedianFilter(5))
    smooth = smooth.filter(ImageFilter.SMOOTH_MORE)
    smooth = smooth.filter(ImageFilter.SMOOTH_MORE)
    smooth = smooth.filter(ImageFilter.SMOOTH_MORE)
    # Boost saturation and contrast
    smooth = ImageEnhance.Color(smooth).enhance(1.8)
    smooth = ImageEnhance.Contrast(smooth).enhance(1.2)
    # Edge overlay: blend edges from original
    edges = img.filter(ImageFilter.FIND_EDGES).convert("RGB")
    edges_arr = np.array(edges, dtype=np.float32)
    smooth_arr = np.array(smooth, dtype=np.float32)
    result_arr = smooth_arr * 0.88 + (255 - edges_arr) * 0.12
    return to_pil(result_arr)


def style_oil_painting(img: Image.Image) -> Image.Image:
    """Oil painting effect using quantization and strong smoothing."""
    # Reduce colors then smooth
    quantized = img.quantize(colors=48).convert("RGB")
    result = quantized
    for _ in range(4):
        result = result.filter(ImageFilter.SMOOTH_MORE)
    result = ImageEnhance.Color(result).enhance(1.6)
    result = ImageEnhance.Contrast(result).enhance(1.15)
    return result


def style_neon_glow(img: Image.Image) -> Image.Image:
    """Neon glow: dark bg + colored glowing edges."""
    gray = img.convert("L")
    edges = gray.filter(ImageFilter.FIND_EDGES)
    edges = edges.filter(ImageFilter.GaussianBlur(radius=1))
    edges_arr = np.array(edges, dtype=np.float32)

    orig_arr = to_numpy(img).astype(np.float32)

    # Build neon channels from edges tinted by original color
    r = np.clip(edges_arr * (orig_arr[:,:,0] / 255.0 + 0.2), 0, 255)
    g = np.clip(edges_arr * (orig_arr[:,:,1] / 255.0 + 0.2), 0, 255)
    b = np.clip(edges_arr * (orig_arr[:,:,2] / 255.0 + 0.5), 0, 255)  # blue boost

    neon = np.stack([r, g, b], axis=2)

    # Dark background
    bg = orig_arr * 0.12
    result_arr = bg + neon * 1.4
    return to_pil(result_arr)


def style_mosaic(img: Image.Image, tile: int = 14) -> Image.Image:
    """Pixelate / mosaic effect."""
    w, h = img.size
    small_w = max(1, w // tile)
    small_h = max(1, h // tile)
    small = img.resize((small_w, small_h), Image.BOX)
    return small.resize((w, h), Image.NEAREST)


def style_vintage(img: Image.Image) -> Image.Image:
    """Vintage film: sepia + vignette + grain."""
    # Sepia
    arr = to_numpy(img).astype(np.float32)
    r = arr[:,:,0] * 0.393 + arr[:,:,1] * 0.769 + arr[:,:,2] * 0.189
    g = arr[:,:,0] * 0.349 + arr[:,:,1] * 0.686 + arr[:,:,2] * 0.168
    b = arr[:,:,0] * 0.272 + arr[:,:,1] * 0.534 + arr[:,:,2] * 0.131
    sepia = np.stack([r, g, b], axis=2)

    # Grain
    noise = np.random.normal(0, 8, sepia.shape)
    sepia = sepia + noise

    # Vignette
    h, w = sepia.shape[:2]
    Y, X = np.ogrid[:h, :w]
    cx, cy = w / 2, h / 2
    dist = np.sqrt(((X - cx) / cx) ** 2 + ((Y - cy) / cy) ** 2)
    vignette = 1 - np.clip(dist * 0.65, 0, 0.75)
    sepia = sepia * vignette[:, :, np.newaxis]

    result = to_pil(sepia)
    result = ImageEnhance.Contrast(result).enhance(1.1)
    return result


STYLES = {
    "pencil":    ("Pencil Sketch",   style_pencil_sketch),
    "watercolor":("Watercolor",      style_watercolor),
    "oil":       ("Oil Painting",    style_oil_painting),
    "neon":      ("Neon Glow",       style_neon_glow),
    "mosaic":    ("Mosaic",          style_mosaic),
    "vintage":   ("Vintage Film",    style_vintage),
}

STYLE_INFO = {
    "pencil":     "Edge-based sketch using dodge-burn inversion.",
    "watercolor": "Repeated smoothing with saturation boost and edge overlay.",
    "oil":        "Color quantization and heavy smoothing for thick-paint look.",
    "neon":       "Dark background with color-tinted glowing edges.",
    "mosaic":     "Pixelation by downsampling and nearest-neighbor upscaling.",
    "vintage":    "Sepia tone, film grain, and radial vignette.",
}


def encode_image(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=88)
    return base64.b64encode(buf.getvalue()).decode()


@app.route("/")
def index():
    style_list = [
        {"id": k, "name": v[0], "desc": STYLE_INFO[k]}
        for k, v in STYLES.items()
    ]
    return render_template("index.html", styles=style_list, ai_templates=AI_STYLE_TEMPLATES)


@app.route("/api/transform", methods=["POST"])
def transform():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    style_id = request.form.get("style", "pencil")
    if style_id not in STYLES:
        return jsonify({"error": "Unknown style"}), 400

    file = request.files["image"]
    try:
        img = Image.open(io.BytesIO(file.read()))
        img.load()  # force decode now so a decompression bomb is caught here
    except Image.DecompressionBombError:
        return jsonify({"error": "Image dimensions are too large."}), 400
    except Exception:
        return jsonify({"error": "Could not open image"}), 400

    # Resize large images to protect memory
    MAX_DIM = 1200
    w, h = img.size
    if max(w, h) > MAX_DIM:
        scale = MAX_DIM / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)

    _, fn = STYLES[style_id]
    try:
        result = fn(img)
    except Exception as e:
        return jsonify({"error": f"Style transfer failed: {e}"}), 500

    # Thumbnails for original + result
    orig_thumb = img.copy()
    orig_thumb.thumbnail((600, 600))
    result_thumb = result.copy()
    result_thumb.thumbnail((600, 600))

    return jsonify({
        "original": encode_image(orig_thumb),
        "result": encode_image(result_thumb),
        "style": STYLES[style_id][0],
        "size": f"{img.size[0]}x{img.size[1]}",
    })


AI_STYLE_TEMPLATES = [
    {"name": "Oil Painting",   "prompt": "an oil painting with thick impasto brushstrokes, rich warm colors, impressionist style"},
    {"name": "Watercolor",     "prompt": "a delicate watercolor painting, soft washes of color, white paper showing through"},
    {"name": "Anime",          "prompt": "anime style illustration, clean line art, cel shading, vibrant colors"},
    {"name": "Cyberpunk",      "prompt": "cyberpunk scene, neon lights, rain-slicked streets, dramatic violet and cyan glow"},
    {"name": "Pencil Sketch",  "prompt": "a detailed graphite pencil sketch, fine crosshatching, monochrome"},
    {"name": "Van Gogh",       "prompt": "a painting in the style of swirling post-impressionist brushwork, starry textures, bold color"},
]


@app.route("/api/restyle", methods=["POST"])
def restyle():
    """Submit an AI restyle job to the GPU queue; returns a job id to poll."""
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400
    prompt   = (request.form.get("prompt") or "").strip()
    strength = request.form.get("strength", "0.6")
    if not prompt:
        return jsonify({"error": "Write a style prompt first."}), 400
    if len(prompt) > 300:
        return jsonify({"error": "Prompt too long (max 300 characters)."}), 400

    file = request.files["image"]
    try:
        resp = http.post(
            f"{NECRON}/jobs/stylize",
            files={"image": (file.filename, file.read(), file.content_type)},
            data={"prompt": prompt, "strength": strength},
            headers=WORKER_AUTH,
            timeout=(3, 30),
        )
        return (resp.content, resp.status_code, {"Content-Type": "application/json"})
    except http.exceptions.RequestException:
        return jsonify({
            "error": "The club's GPU servers are offline. The classic filters still work.",
            "gpu_offline": True,
        }), 503


# Job ids come from the worker as uuid4().hex[:12]. Validate before interpolating
# into the worker URL: an unchecked id lets a caller steer the proxied path (".."
# segments are normalised away by requests/urllib3) and reach worker endpoints
# this app never meant to expose.
_JID_RE = _re.compile(r"\A[0-9a-f]{12}\Z")


@app.route("/api/job/<jid>")
def job_status(jid):
    if not _JID_RE.match(jid):
        return jsonify({"error": "Bad job id"}), 400
    try:
        resp = http.get(f"{NECRON}/jobs/{jid}", headers=WORKER_AUTH, timeout=(3, 15))
        return (resp.content, resp.status_code, {"Content-Type": "application/json"})
    except http.exceptions.RequestException:
        return jsonify({"error": "GPU server unreachable", "gpu_offline": True}), 503


@app.route("/api/job/<jid>/result")
def job_result(jid):
    if not _JID_RE.match(jid):
        return jsonify({"error": "Bad job id"}), 400
    try:
        resp = http.get(f"{NECRON}/jobs/{jid}/result", headers=WORKER_AUTH,
                        timeout=(3, 60))
        return (resp.content, resp.status_code,
                {"Content-Type": resp.headers.get("Content-Type", "application/octet-stream")})
    except http.exceptions.RequestException:
        return jsonify({"error": "GPU server unreachable"}), 503


# Short server-side cache so the public GPU pill can poll often (on every open
# page) without multiplying load on the VPS or the necron worker: no matter how
# many visitors poll, necron is hit at most ~once/second.
#
# The offline result is cached too, and that is the important half. This app runs
# under `gunicorn -w 1`; a request that misses the cache calls necron with a 3s
# timeout and holds the single worker for the whole wait. Caching only successes
# means that the moment necron goes slow or unreachable -- exactly when load
# matters -- every poll becomes an uncached 3s block, the worker is permanently
# occupied by the status pill, and the actual style-transfer demo queues behind
# it. Offline gets a shorter TTL so recovery is still noticed promptly.
_GPU_CACHE = {"t": 0.0, "payload": None}
_GPU_CACHE_LOCK = threading.Lock()
_GPU_CACHE_TTL = 1.0
_GPU_CACHE_TTL_OFFLINE = 5.0


@app.route("/api/gpu-status")
def gpu_status():
    """Ping the necron GPU worker and return its status. Called by the public
    Projects page and the GPU pill on every site surface. Cached ~1s."""
    now = time.time()
    with _GPU_CACHE_LOCK:
        cached = _GPU_CACHE["payload"]
        if cached is not None:
            ttl = (_GPU_CACHE_TTL_OFFLINE if cached.get("status") == "offline"
                   else _GPU_CACHE_TTL)
            if now - _GPU_CACHE["t"] < ttl:
                return jsonify(cached)
    try:
        resp = http.get(f"{NECRON}/status", headers=WORKER_AUTH, timeout=3)
        data = resp.json()
        # Normalise status label for the frontend
        status = data.get("status", "unknown")
        payload = {
            "status":      status,           # "ready" | "busy"
            "gpu":         data.get("gpu", "Club GPU"),
            "active_jobs": data.get("active_jobs", 0),
            "last_model":  data.get("last_model", ""),
            "util":        data.get("util"),
            "mem_used":    data.get("mem_used"),
            "mem_total":   data.get("mem_total"),
            "power":       data.get("power"),
            "power_limit": data.get("power_limit"),
            "temp":        data.get("temp"),
            "fan":         data.get("fan"),
            "sm_clock":    data.get("sm_clock"),
            "mem_util":    data.get("mem_util"),
            "tflops":      data.get("tflops"),
            "uptime":      data.get("uptime"),
            "uptime_days": data.get("uptime_days"),
            "occupied":    data.get("occupied"),
        }
        with _GPU_CACHE_LOCK:
            _GPU_CACHE["t"], _GPU_CACHE["payload"] = now, payload
        return jsonify(payload)
    except http.exceptions.RequestException:
        # Cache this too -- see the note on _GPU_CACHE_TTL_OFFLINE above.
        payload = {"status": "offline", "gpu": "Club GPU", "active_jobs": 0}
        with _GPU_CACHE_LOCK:
            _GPU_CACHE["t"], _GPU_CACHE["payload"] = now, payload
        return jsonify(payload)



@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

if __name__ == "__main__":
    app.run(debug=False, port=5006)
