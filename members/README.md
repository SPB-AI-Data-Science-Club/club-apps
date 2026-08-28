# Members Portal

The club's members-only portal and lesson platform: curriculum pages, a live
Kahoot-style game engine for club sessions, and an admin area.

**Not currently deployed.** The portal ran at `club.spbdatascience.org` until
July 2026 and is not part of the current site. The code is kept here so it can
be redeployed; see `docs/REBUILD.md`.

## Layout

| Path | What it is |
|------|------------|
| `app.py` | Flask application: auth, routing, the game engine's socket handlers |
| `curriculum_content.py` | Session-by-session curriculum data |
| `learning_content.py` | Lesson and explainer content |
| `game_content.py` | Question sets for the live game |
| `games/` | Saved question sets, including `sets/EXAMPLE-neural-networks.json` |
| `templates/`, `static/` | Jinja templates and front-end assets |

## Access model

Sign-in is Google OAuth (any Google account), followed by a one-time
verification code sent to the member's school email address. Verified addresses
are recorded in an `email_verifications` table. Both the OAuth client and the
SMTP credentials are supplied at runtime through the app's `.env` and are never
committed.

## Local development

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
# provide .env (see docs/DEPLOY-REFERENCE.txt for the variable names)
python app.py
```

The member database (`members.db`) is not in this repo and never should be: it
holds student names and email addresses.
