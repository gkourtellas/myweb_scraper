#!/bin/bash
# Runs the daily translate + bet pipeline.
# Call this from cron once a day.
set -e

cd "$(dirname "$0")"

echo "[$(date)] Starting translate step..."
python3 translate_tips.py

echo "[$(date)] Starting bet placement step..."
python3 place_bets.py

echo "[$(date)] Done."
