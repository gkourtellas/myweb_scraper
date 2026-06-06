#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p logs

INTERVAL="${SCRAPE_INTERVAL_SECONDS:-3600}"

echo "Scraper loop started (interval=${INTERVAL}s)" | tee -a logs/scraper.log

while true; do
  echo "===== $(date -Is) run start =====" | tee -a logs/scraper.log
  python main.py 2>&1 | tee -a logs/scraper.log
  echo "===== $(date -Is) run end, sleeping ${INTERVAL}s =====" | tee -a logs/scraper.log
  sleep "${INTERVAL}"
done
