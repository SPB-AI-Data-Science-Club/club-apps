"""
Language Model Playground
Character-level n-gram models built from classic texts. The order
slider demonstrates the core tradeoff behind all language models:
short contexts generalize but produce gibberish, long contexts read
fluently but start memorizing the training data. Modern LLMs solve
this with neural networks; the sampling loop here is the same idea.
"""
import math
import os
import random
from collections import Counter, defaultdict
from functools import lru_cache

from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
# Custom-corpus mode builds a model from whatever text is posted, so cap the
# request body. nginx defaults to 1 MB in front of this, but the app must not
# depend on a proxy it might not be behind (a member running `python app.py`
# has no nginx at all).
app.config["MAX_CONTENT_LENGTH"] = 512 * 1024

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(BASE_DIR, "corpora")

CORPORA = {
    "shakespeare": {"file": "shakespeare.txt", "label": "Shakespeare's plays"},
    "sherlock":    {"file": "sherlock.txt",    "label": "The Adventures of Sherlock Holmes"},
    "grimm":       {"file": "grimm.txt",       "label": "Grimms' Fairy Tales"},
}

MAX_ORDER  = 6
MAX_LENGTH = 1200


@lru_cache(maxsize=3)
def load_corpus(name: str) -> str:
    path = os.path.join(CORPUS_DIR, CORPORA[name]["file"])
    with open(path, encoding="utf-8") as f:
        return f.read()


@lru_cache(maxsize=2)
def build_model(name: str, order: int):
    """Map each length-`order` context to a Counter of next characters."""
    text  = load_corpus(name)
    model = defaultdict(Counter)
    for i in range(len(text) - order):
        model[text[i:i + order]][text[i + order]] += 1
    return dict(model)


def sample_char(counter: Counter, temperature: float) -> str:
    chars, counts = zip(*counter.items())
    if temperature < 0.05:
        return chars[counts.index(max(counts))]
    weights = [c ** (1.0 / temperature) for c in counts]
    return random.choices(chars, weights=weights, k=1)[0]


def pick_seed(text: str, order: int) -> str:
    """Start generation at the beginning of a real sentence."""
    for _ in range(200):
        i = random.randrange(len(text) - order - 1)
        if text[i] in ".!?\n" and text[i + 1] in " \n":
            seed = text[i + 2:i + 2 + order]
            if len(seed) == order:
                return seed
    return text[:order]


@app.route("/")
def index():
    corpora = [{"id": k, "label": v["label"]} for k, v in CORPORA.items()]
    return render_template("index.html", corpora=corpora,
                           max_order=MAX_ORDER, max_length=MAX_LENGTH)


def build_model_from_text(text: str, order: int):
    """Same as build_model but for ad-hoc user text (not cached)."""
    model = defaultdict(Counter)
    for i in range(len(text) - order):
        model[text[i:i + order]][text[i + order]] += 1
    return dict(model)


def _clamp(raw, lo, hi, default, cast):
    """Coerce one slider value, falling back to the default on junk input.

    The sliders are the only intended caller, but this is a public endpoint:
    without the cast guard, any non-numeric value raised straight out of the
    view and turned a malformed request into a 500.
    """
    try:
        return max(lo, min(hi, cast(raw)))
    except (TypeError, ValueError):
        return default


@app.route("/api/generate", methods=["POST"])
def generate():
    cfg = request.get_json(silent=True)
    if not isinstance(cfg, dict):
        return jsonify({"error": "Expected a JSON object."}), 400
    corpus      = cfg.get("corpus", "shakespeare")
    order       = _clamp(cfg.get("order", 4),         1, MAX_ORDER,  4,   int)
    temperature = _clamp(cfg.get("temperature", 1.0), 0.05, 2.5,     1.0, float)
    length      = _clamp(cfg.get("length", 500),      100, MAX_LENGTH, 500, int)

    if corpus == "custom":
        raw = cfg.get("custom_text") or ""
        if not isinstance(raw, str):
            return jsonify({"error": "custom_text must be text."}), 400
        text = raw.strip()[:200_000]
        if len(text) < order * 20:
            return jsonify({"error": "Paste at least a few sentences of training text."}), 400
        model = build_model_from_text(text, order)
    elif corpus in CORPORA:
        text  = load_corpus(corpus)
        model = build_model(corpus, order)
    else:
        return jsonify({"error": "Unknown corpus"}), 400

    out = pick_seed(text, order)
    dead_ends = 0
    while len(out) < length:
        counter = model.get(out[-order:])
        if counter is None:
            # Context never seen: restart from a fresh sentence start
            out += "\n\n" + pick_seed(text, order)
            dead_ends += 1
            continue
        out += sample_char(counter, temperature)

    # Average branching factor gives a feel for model uncertainty
    avg_branching = sum(len(c) for c in model.values()) / len(model)

    return jsonify({
        "text":          out[:length],
        "stats": {
            "contexts":      len(model),
            "corpus_chars":  len(text),
            "avg_branching": round(avg_branching, 2),
            "dead_ends":     dead_ends,
        },
    })



@app.after_request
def _no_html_cache(resp):
    # Browsers heuristically cache HTML served without Cache-Control, which
    # leaves visitors on stale pages after a deploy. Force revalidation.
    if resp.mimetype == "text/html":
        resp.headers["Cache-Control"] = "no-cache"
    return resp

if __name__ == "__main__":
    app.run(debug=False, port=5009)
