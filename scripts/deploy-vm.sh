#!/usr/bin/env bash
# After: git pull (from repo root on the VM)
# Run:    ./scripts/deploy-vm.sh
#
# Requires: backend/.venv, nginx web root, systemd unit (see HOSTING_GCP.md).
# Override: WEBROOT=/var/www/glamr SYSTEMD_SERVICE=glamr-api ./scripts/deploy-vm.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEBROOT="${WEBROOT:-/var/www/glamr}"
SYSTEMD_SERVICE="${SYSTEMD_SERVICE:-glamr-api}"

if [[ ! -d "$ROOT/backend/.venv" ]]; then
  echo "Missing backend/.venv — on the VM run once:" >&2
  echo "  cd \"$ROOT/backend\" && python3 -m venv .venv && source .venv/bin/activate && pip install -U pip && pip install -r requirements.txt" >&2
  exit 1
fi

echo "==> Backend deps ($ROOT/backend)"
cd "$ROOT/backend"
# shellcheck source=/dev/null
source .venv/bin/activate
pip install -r requirements.txt

echo "==> Frontend build ($ROOT/frontend)"
cd "$ROOT/frontend"
npm ci
npm run build

echo "==> Sync to $WEBROOT"
sudo rsync -a --delete dist/ "$WEBROOT/"

echo "==> Restart $SYSTEMD_SERVICE"
sudo systemctl restart "$SYSTEMD_SERVICE"
sudo systemctl is-active --quiet "$SYSTEMD_SERVICE" || {
  echo "Service failed — check: sudo journalctl -u $SYSTEMD_SERVICE -n 50 --no-pager" >&2
  exit 1
}

echo "Deploy finished."
