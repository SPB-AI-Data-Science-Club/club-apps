"""
Photo Editor
Generates a high-quality, photorealistic image from a text prompt, optionally
guided by a reference photo the visitor uploads. Runs RealVisXL on the club's
GPU servers; submission returns a job id the page polls until the image is ready.
"""
import os
import re as _re
from flask import Flask, render_template, request, jsonify
import requests as http
import time
import threading

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024

NECRON          = os.environ.get("GPU_WORKER_URL", "http://gpu-worker:15100")
# Bearer token for the GPU worker. The worker refuses every request without it
# (see necron-worker/app.py); network reachability alone is not authorisation.
# Same value as WORKER_TOKEN in the worker's .env.
WORKER_TOKEN = os.environ.get("WORKER_TOKEN", "")
WORKER_AUTH = ({"Authorization": f"Bearer {WORKER_TOKEN}"} if WORKER_TOKEN else {})
CONNECT_TIMEOUT = 4
READ_TIMEOUT    = 120

# The GPU is a shared club resource, so cap how often one visitor can submit.
# A photo takes only seconds, so this is looser than the old video tool. Soft,
# in-memory guard (one gunicorn worker) behind the nginx per-IP rate limit.
DAILY_CAP   = 40      # generations per IP per rolling 24h
COOLDOWN    = 8       # seconds between submissions from the same IP
_LIMIT_LOCK = threading.Lock()
_HISTORY    = {}      # ip -> list[float] submit timestamps (last 24h)


def _client_ip():
    fwd = request.headers.get("X-Real-IP") or request.headers.get("X-Forwarded-For", "")
    return fwd.split(",")[0].strip() or request.remote_addr or "?"


def _rate_check(ip):
    """Return None if allowed, else (message, retry_after_seconds)."""
    now = time.time()
    with _LIMIT_LOCK:
        hits = [t for t in _HISTORY.get(ip, []) if now - t < 86400]
        if hits and now - hits[-1] < COOLDOWN:
            return ("Please wait a moment before generating another photo.",
                    int(COOLDOWN - (now - hits[-1])) + 1)
        if len(hits) >= DAILY_CAP:
            return ("You have reached today's limit for this shared GPU tool. "
                    "Please try again tomorrow.",
                    int(86400 - (now - hits[0])) + 1)
        hits.append(now)
        _HISTORY[ip] = hits
    return None


PROMPT_IDEAS = [
    "A candid street photograph of a red bicycle leaning on a brick wall, golden hour, 35mm",
    "A photorealistic portrait of an elderly fisherman, weathered face, soft window light",
    "A misty pine forest at dawn, sunbeams cutting through the trees, ultra detailed",
    "A steaming bowl of ramen on a wooden table, shallow depth of field, food photography",
    "A snowy alpine village at blue hour, warm lights glowing in the windows",
    "An astronaut floating above Earth, the planet reflected in the visor, cinematic",
]


@app.route("/")
def index():
    return render_template("index.html", ideas=PROMPT_IDEAS)


@app.route("/api/generate", methods=["POST"])
def generate():
    """Submit a photo generation job to the GPU queue; returns a job id to poll.
    Prompt is required; a reference image is optional (enables image-to-image)."""
    prompt = (request.form.get("prompt") or "").strip()
    if not prompt:
        return jsonify({"error": "Describe the photo you want first."}), 400
    if len(prompt) > 500:
        return jsonify({"error": "Prompt too long (max 500 characters)."}), 400

    limited = _rate_check(_client_ip())
    if limited:
        msg, retry = limited
        return jsonify({"error": msg}), 429, {"Retry-After": str(retry)}

    data = {
        "prompt":   prompt,
        "aspect":   request.form.get("aspect", "square"),
        "strength": request.form.get("strength", "0.6"),
    }
    files = None
    f = request.files.get("image")
    if f and f.filename:
        files = {"image": (f.filename, f.read(), f.content_type)}

    try:
        resp = http.post(
            f"{NECRON}/jobs/generate",
            data=data, files=files,
            headers=WORKER_AUTH,
            timeout=(CONNECT_TIMEOUT, 30),
        )
        return (resp.content, resp.status_code, {"Content-Type": "application/json"})
    except http.exceptions.RequestException:
        return jsonify({
            "error": "The club's GPU servers are offline right now. Try again later.",
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
        resp = http.get(f"{NECRON}/jobs/{jid}", headers=WORKER_AUTH,
                        timeout=(CONNECT_TIMEOUT, 15))
        return (resp.content, resp.status_code, {"Content-Type": "application/json"})
    except http.exceptions.RequestException:
        return jsonify({"error": "GPU server unreachable", "gpu_offline": True}), 503


@app.route("/api/job/<jid>/result")
def job_result(jid):
    if not _JID_RE.match(jid):
        return jsonify({"error": "Bad job id"}), 400
    try:
        resp = http.get(f"{NECRON}/jobs/{jid}/result", headers=WORKER_AUTH,
                        timeout=(CONNECT_TIMEOUT, 60))
        return (resp.content, resp.status_code,
                {"Content-Type": resp.headers.get("Content-Type", "application/octet-stream")})
    except http.exceptions.RequestException:
        return jsonify({"error": "GPU server unreachable"}), 503


@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp


if __name__ == "__main__":
    app.run(debug=False, port=5010)
