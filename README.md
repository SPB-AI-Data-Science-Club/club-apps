# SPB AI & Data Science Club — Web Apps

Backend code for the club's interactive demo apps and members portal, served at
`*.spbdatascience.org`. The public portfolio site lives in its own repository
(`SPB-AI-Data-Science-Club/portfolio`); this repo holds the application code that
sits behind it.

## Apps
| App | Subdomain | What it is |
|-----|-----------|------------|
| `members` | club.spbdatascience.org | Members portal + LMS (curriculum, live Kahoot-style game engine, admin) |
| `chess-bot` | chess | Chess-playing bot demo |
| `digit-recognizer` | digits | Handwritten-digit (MNIST) recognition |
| `image-classifier` | classifier | Image classification demo |
| `neural-net-visualizer` | neural | Interactive neural-network visualizer |
| `pathfinding-visualizer` | pathfinding | Pathfinding-algorithm visualizer |
| `photo-editor` | photo | AI photo editor / generator (GPU-backed) |
| `sentiment-analyzer` | sentiment | Text sentiment analysis |
| `style-transfer` | style | Neural style transfer |
| `text-generator` | textgen | Text generation demo |

## Running an app
Each app is a Flask service run under gunicorn. Secrets and config are provided at
runtime via environment variables (a `.env` per app) and are **never** committed —
see `docs/DEPLOY-REFERENCE.txt` for the required variable names, the nginx site
config, and the systemd unit definitions.

```bash
cd <app>
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# provide the app's .env (see docs/DEPLOY-REFERENCE.txt for variable names)
gunicorn -w 1 -b 127.0.0.1:<port> app:app
```

## Notes
- No secrets, databases, or model weights are stored here (see `.gitignore`).
- ML model weights are downloaded at runtime / cached locally, not committed.
