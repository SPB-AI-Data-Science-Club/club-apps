# SPB AI & Data Science Club — Web Apps

Application code for the club's interactive demos, the members portal, and the
GPU worker. The public website is a separate repository,
[`portfolio`](https://github.com/SPB-AI-Data-Science-Club/portfolio).

This repository is the source of truth for all app code.

## Demos

Each demo is a self-contained Flask app in its own directory. Three run on the
club's server today; the rest need either PyTorch (too large for the current
1 GB VPS) or the GPU box, and run locally.

| App | Status | What it is |
|-----|--------|------------|
| [`pathfinding-visualizer`](pathfinding-visualizer) | [Live](https://pathfinding.spbdatascience.org) | A*, Dijkstra, Greedy, BFS and DFS animated on an interactive grid |
| [`style-transfer`](style-transfer) | [Live](https://style.spbdatascience.org) | Six artistic filters built from classical image-processing operations |
| [`text-generator`](text-generator) | [Live](https://textgen.spbdatascience.org) | Character-level n-gram language model with adjustable context and temperature |
| [`chess-bot`](chess-bot) | Local | Stockfish opponent at calibrated strength, with hints and evaluation |
| [`digit-recognizer`](digit-recognizer) | Local | CNN trained on MNIST, reading digits drawn on a canvas |
| [`image-classifier`](image-classifier) | Local | ImageNet classification with GPU-to-CPU failover |
| [`neural-net-visualizer`](neural-net-visualizer) | Local | Build a network in the browser and watch the decision boundary form |
| [`sentiment-analyzer`](sentiment-analyzer) | Local | Stock charts with transformer-scored news sentiment |
| [`photo-editor`](photo-editor) | Needs GPU | Prompt-driven image generation on the club's own hardware |

## Also here

| Path | What it is |
|------|------------|
| [`members`](members) | Members portal and lesson platform (not currently deployed) |
| [`necron-worker`](necron-worker) | GPU inference worker the demos proxy to (not currently deployed) |
| [`docs`](docs) | Rebuild guide, deployment reference, and the live nginx config |

## Running an app

Every app is a Flask service run under gunicorn in production.

```bash
cd <app>
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python app.py
```

Apps that need configuration read it from a per-app `.env` at run time. The
variable names are listed in [`docs/DEPLOY-REFERENCE.txt`](docs/DEPLOY-REFERENCE.txt),
along with the systemd units and the port map.

## Secrets

No secrets, databases, or model weights are committed here, and none should be.
`.env` files, keys, `*.db` and model caches are all gitignored. Model weights
download at run time or are reproduced by each app's training script.
