# GPU Worker

The inference server that ran on the club's GPU workstation ("necron", an
RTX 5080). The public demo apps stayed light by proxying their heavy work here
over a private Tailscale network; when the worker was unreachable each app fell
back to CPU or degraded gracefully.

**Not currently deployed.** The GPU box was wiped in July 2026 and the tailnet
deleted. This code is kept so the worker can be stood up again on new hardware.
Nothing here assumes the old machine: the deploy script takes the target host as
an argument and `setup.sh` reads the Tailscale address at run time.

## Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| GET | `/status` | GPU utilization, active jobs, uptime, rental state |
| POST | `/sentiment/analyze` | Score a single headline |
| POST | `/sentiment/batch` | Score up to 20 headlines |
| POST | `/classify` | Image classification (multipart upload) |

## Files

| Path | What it is |
|------|------------|
| `app.py` | The Flask worker: model loading, job tracking, the routes above |
| `setup.sh` | Installs the worker on the GPU box and registers the systemd unit |
| `deploy-from-vps.sh` | Pushes this directory from the web VPS to a GPU host |
| `spb-necron-worker.service.template` | systemd unit template |

## Deploying to a new GPU box

```bash
./deploy-from-vps.sh <gpu-box-tailscale-name-or-ip>
```

The worker binds to the Tailscale interface only, on port 15100. It is never
exposed to the public internet: the VPS reaches it over the tailnet, and the
firewall on the GPU box should not open that port to anything else.

## Authentication

Network reachability is not authorisation. Every route requires a bearer token:

```
Authorization: Bearer $WORKER_TOKEN
```

Set `WORKER_TOKEN` in the worker's `.env` and in the `.env` of each app that
calls it (`style-transfer`, `photo-editor`, `image-classifier`,
`sentiment-analyzer`). Generate one with:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

The worker **refuses to start** without a token, so a misconfiguration fails
closed rather than quietly serving GPU time to anything on the network. For a
deliberate local run without auth, set `WORKER_ALLOW_NO_AUTH=1`.

This is the direct lesson of the July 2026 compromise: the tailnet was the only
thing standing between a stolen credential and root on this box, and one layer
was not enough. Keep the network restriction *and* the token.

Running `python app.py` binds `127.0.0.1` by default. Production binds the
private address via `setup.sh`; override with `WORKER_BIND` if you need to.
