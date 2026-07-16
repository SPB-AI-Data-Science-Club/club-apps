"""
Handwritten Digit Recognizer
A small convolutional network trained on MNIST, served on CPU.
The client draws on a canvas, preprocesses to the MNIST format
(20x20 bounding box centered by mass in a 28x28 field), and the
server returns the full softmax distribution over digits 0-9.
"""
import io
import json
import os
import time

import numpy as np
import torch
from flask import Flask, render_template, request, jsonify

from model_def import DigitCNN

app = Flask(__name__)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "model", "digit_cnn.pt")
META_PATH  = os.path.join(BASE_DIR, "model", "meta.json")


_model = None
_meta  = {}


def get_model():
    global _model, _meta
    if _model is None:
        m = DigitCNN()
        m.load_state_dict(torch.load(MODEL_PATH, map_location="cpu"))
        m.eval()
        _model = m
        if os.path.exists(META_PATH):
            with open(META_PATH) as f:
                _meta = json.load(f)
    return _model


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/model-info")
def model_info():
    get_model()
    params = sum(p.numel() for p in _model.parameters())
    return jsonify({
        "parameters":    params,
        "test_accuracy": _meta.get("test_accuracy"),
        "epochs":        _meta.get("epochs"),
        "trained_on":    _meta.get("trained_on", "MNIST (60,000 images)"),
    })


@app.route("/api/predict", methods=["POST"])
def predict():
    data   = request.get_json(force=True)
    pixels = data.get("pixels")
    if not pixels or len(pixels) != 784:
        return jsonify({"error": "Expected 784 pixel values"}), 400

    arr = np.asarray(pixels, dtype=np.float32).reshape(1, 1, 28, 28)
    # Same normalization used during training
    arr = (arr - 0.1307) / 0.3081

    model = get_model()
    t0 = time.perf_counter()
    with torch.no_grad():
        logits = model(torch.from_numpy(arr))
        probs  = torch.softmax(logits, dim=1)[0]
    elapsed_ms = (time.perf_counter() - t0) * 1000

    dist = [round(float(p), 4) for p in probs]
    best = int(np.argmax(dist))
    return jsonify({
        "digit":        best,
        "confidence":   round(dist[best] * 100, 1),
        "distribution": dist,
        "inference_ms": round(elapsed_ms, 2),
    })



@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5007)
