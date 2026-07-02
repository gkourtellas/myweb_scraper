#!/usr/bin/env bash
set -euo pipefail

cd /app

case "${1:-scraper}" in
  scraper)
    exec /app/docker/run-scraper.sh
    ;;
  status)
    exec python status_web.py "${STATUS_PORT:-8001}"
    ;;
  homepage)
    exec python home_page.py "${HOMEPAGE_PORT:-6969}"
    ;;
  once)
    exec python main.py
    ;;
  *)
    exec "$@"
    ;;
esac
