#!/usr/bin/env bash
# Run this ON THE VPS to push the worker to the GPU box and (re)start its service
# over the private link.
#
#   ./deploy-from-vps.sh <gpu-box-tailscale-name-or-ip>
#
# The old hardcoded address (necron, 100.72.210.90) is dead: that box was wiped and
# the tailnet deleted after the July 2026 compromise. The rebuilt box gets a new
# name/IP, so pass it in.
set -euo pipefail

NECRON_HOST="${1:-${NECRON_HOST:-}}"
if [ -z "$NECRON_HOST" ]; then
  echo "usage: $0 <gpu-box-tailscale-name-or-ip>   (or set NECRON_HOST)" >&2
  exit 1
fi
WORKER_SRC="/var/www/spb-club/necron-worker"

echo "==> Checking ${NECRON_HOST} is reachable..."
ssh -o ConnectTimeout=8 "$NECRON_HOST" "echo connected" || {
  echo "ERROR: ${NECRON_HOST} not reachable" >&2; exit 1; }

echo "==> Copying worker files..."
ssh "$NECRON_HOST" "sudo mkdir -p /opt/necron-worker && sudo chown \$(whoami) /opt/necron-worker"
scp "$WORKER_SRC/app.py" "$WORKER_SRC/setup.sh" \
    "$WORKER_SRC/spb-necron-worker.service.template" \
    "$NECRON_HOST:/opt/necron-worker/"

# setup.sh owns the unit file (correct bind flags, no --max-requests) so the two
# install paths can never drift apart again.
echo "==> Installing + starting the service on ${NECRON_HOST}..."
ssh "$NECRON_HOST" "cd /opt/necron-worker && bash setup.sh"

echo "==> Testing worker status endpoint..."
curl -sS --max-time 10 "http://${NECRON_HOST}:15100/status" || {
  echo "WARN: /status did not respond. Check: ssh ${NECRON_HOST} journalctl -u spb-necron-worker -n 50" >&2; }
echo ""
echo "==> Done. Worker is live on ${NECRON_HOST}:15100 (private link only)."
