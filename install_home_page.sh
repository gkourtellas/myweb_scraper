#!/usr/bin/env bash
set -euo pipefail
SERVICE_FILE="home_page.service"
if [[ ! -f "$SERVICE_FILE" ]]; then
  echo "ERROR: $SERVICE_FILE not found in $(pwd)"
  exit 1
fi
sudo cp "$SERVICE_FILE" /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now home_page
sudo systemctl status home_page --no-pager
