#!/usr/bin/env bash
set -euo pipefail
SERVICE_FILE="status_web.service"
if [[ ! -f "$SERVICE_FILE" ]]; then
  echo "ERROR: $SERVICE_FILE not found in $(pwd)"
  exit 1
fi
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now status_web
sudo systemctl status status_web --no-pager
