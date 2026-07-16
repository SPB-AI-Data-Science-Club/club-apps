#!/usr/bin/env bash
# Run this ON the GPU box once to install and start the worker service.
# Assumes /opt/spb-venv/ already has torch + torchvision + transformers + pillow
# (+ diffusers for the photo-editor / style-transfer pipes).
set -euo pipefail

WORKER_DIR=/opt/necron-worker
SRC_DIR="$(cd "$(dirname "$0")" && pwd)"

# The worker listens on loopback + the private Tailscale address only, never on
# 0.0.0.0 (home LAN + vast.ai renters share this host). See setup.md section 3.
TS_IP="${TS_IP:-$(tailscale ip -4 2>/dev/null | head -1 || true)}"
if [ -z "$TS_IP" ]; then
  echo "ERROR: no Tailscale IPv4 found. Bring tailscale up first, or pass TS_IP=<addr>." >&2
  exit 1
fi
BIND_FLAGS="-b 127.0.0.1:15100 -b ${TS_IP}:15100"

echo "==> Copying worker files..."
sudo mkdir -p "$WORKER_DIR"
sudo cp "$SRC_DIR/app.py" "$WORKER_DIR/"
sudo chown -R www-data:www-data "$WORKER_DIR"

echo "==> Installing systemd service (bind: ${BIND_FLAGS})..."
sed "s|__BIND_FLAGS__|${BIND_FLAGS}|" "$SRC_DIR/spb-necron-worker.service.template" \
  | sudo tee /etc/systemd/system/spb-necron-worker.service > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable spb-necron-worker
sudo systemctl restart spb-necron-worker
sleep 3
sudo systemctl is-active spb-necron-worker

echo "==> Verifying the worker is NOT listening on a wildcard address..."
if sudo ss -tlnp | grep -q '0\.0\.0\.0:15100\|\*:15100'; then
  echo "FAIL: worker is bound to a wildcard address. Fix before exposing this box." >&2
  exit 1
fi
sudo ss -tlnp | grep ':15100' || true

echo "==> Worker running on ${TS_IP}:15100 (+ loopback)."
