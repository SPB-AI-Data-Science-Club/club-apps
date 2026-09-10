# Rebuilding the SPB Data Science Club website from scratch

This repo (`club-apps`) + the `portfolio` repo contain everything needed to reconstruct the
entire site. A fresh session with no prior context can rebuild from this document.

## What the site is
- **Public site** — `spbdatascience.org`. Lives in the separate repo `SPB-AI-Data-Science-Club/portfolio`
  (was deployed by a 2-minute `git fetch && git reset --hard origin/main` cron on the web server).
- **9 demo apps** — each on its own subdomain, code in this repo:
  chess-bot→chess, digit-recognizer→digits, image-classifier→classifier, neural-net-visualizer→neural,
  pathfinding-visualizer→pathfinding, photo-editor→photo, sentiment-analyzer→sentiment, style-transfer→style,
  text-generator→textgen.

## Architecture
- **1 web VPS** (Debian 13 on the current box; older copies of this guide said Ubuntu): nginx reverse-proxy →
  one gunicorn service per app on `127.0.0.1:15001–15010`;
  Cloudflare in front (wildcard `*.spbdatascience.org`, SSL mode Full).
- **1 GPU box** (optional): ran the heavy generation for `photo-editor` / `style-transfer` via an HTTP worker
  (`/status`, `/jobs/generate`, `/jobs/<id>`), reached from the VPS over a private link (Tailscale, `:15100`).
  The worker code IS in this repo, at `necron-worker/` (earlier copies of this guide wrongly said it was lost).
  It requires a `WORKER_TOKEN` bearer token and refuses to start without one. Those apps degrade gracefully
  (return "GPU busy") when the worker is absent.

## The key config file
`docs/DEPLOY-REFERENCE.txt` — the exact nginx site config, every `spb-*.service` systemd unit (each app's port),
the deploy cron, and the environment-variable NAMES each app needs (values redacted; generate fresh secrets).

## Steps
1. Provision a fresh VPS. The current box is Debian 13 (trixie). Apply the hardening below FIRST.
   Vultr's Debian image ships broken in two silent ways: no SSH host keys (`ssh-keygen -A`) and
   `ListenAddress 127.0.0.1` in `sshd_config`. It also ships with ufw already enabled.
2. `apt install nginx python3-venv git`; create `/var/www/spb-club/`.
3. **Portfolio:** put the `portfolio` repo's contents at `/var/www/spb-club/portfolio`. The current box has NO
   git clone and NO deploy cron: the site is pushed from the Mac with `portfolio/deploy.sh`, which rsyncs to the
   `website` ssh alias. The older read-only-deploy-key + `git fetch && git reset --hard` cron is the better
   design and is worth restoring at rebuild, because hand-copying is what let the live apps drift months behind
   the repo.
4. **Each app in this repo:** `python3 -m venv venv && venv/bin/pip install -r requirements.txt`; create its `.env`
   (variable names in `docs/DEPLOY-REFERENCE.txt`) with FRESH secrets; install its systemd unit from the reference;
   `systemctl enable --now spb-<name>`.
5. **GPU worker apps:** generate one `WORKER_TOKEN` and put the same value in all five `.env` files
   (`necron-worker`, `style-transfer`, `photo-editor`, `image-classifier`, `sentiment-analyzer`):
   `python3 -c "import secrets; print(secrets.token_urlsafe(32))"`. The worker refuses to start without it.
   This is the only secret the site needs.
6. **nginx:** install the site config from the reference (server block per subdomain → `proxy_pass` its port).
   TLS via Cloudflare (origin cert; SSL Full).
7. **DNS:** Cloudflare wildcard `*.spbdatascience.org` → VPS IP; map the subdomains above.
8. **GPU apps:** optional — rebuild a GPU box + worker and connect the VPS to it over a fresh private link.

## Security hardening (REQUIRED — lessons from a 2026-07 compromise)
The previous setup was fully compromised because one unencrypted SSH key granted root everywhere. Do NOT repeat:
- SSH **key-only**, and use **passphrase-protected** keys. Never reuse an old key.
- **No passwordless sudo** (`/etc/sudoers.d/*-nopasswd`) — it was the privilege-escalation path.
- If using Tailscale SSH, **never grant `root` to a user identity** in the ACL — that turned one stolen key into
  instant root on every machine. Scope access tightly.
- Firewall default-deny; allow 80/443 only from Cloudflare; run fail2ban.
- Keep all app secrets in per-app `.env` files (never commit them); rotate them if ever exposed.
