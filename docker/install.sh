#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [[ ! -f tginfo.txt ]]; then
  echo "ERROR: tginfo.txt not found in $ROOT"
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example — review MATCHBOT_HOST_DIR and SCRAPE_INTERVAL_SECONDS"
fi

echo "Building images..."
docker compose build

echo "Starting containers..."
docker compose up -d

echo
docker compose ps
echo
echo "Status UI: http://$(hostname -f 2>/dev/null || hostname):${STATUS_PORT:-8001}/"
echo "Homepage:  http://$(hostname -f 2>/dev/null || hostname):${HOMEPAGE_PORT:-6969}/"
echo
echo "To stop old systemd units (run once, on the host):"
echo "  sudo systemctl disable --now myweb_scraper status_web home_page || true"
