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
