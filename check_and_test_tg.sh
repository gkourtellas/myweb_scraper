#!/usr/bin/env bash
set -euo pipefail

# Usage: ./check_and_test_tg.sh [PROJECT_DIR]
# Default PROJECT_DIR is /home/gk/myweb_scraper
DIR="${1:-/home/gk/myweb_scraper}"

echo "-> Using project directory: $DIR"
cd "$DIR" || { echo "ERROR: cannot cd to $DIR"; exit 1; }

# Ensure tginfo.txt exists
if [ ! -f tginfo.txt ]; then
  echo "ERROR: tginfo.txt not found in $DIR"
  exit 1
fi

# Read token/chat (strip CRLF)
TOKEN=$(sed -n '1p' tginfo.txt | tr -d '\r' | tr -d '\n')
CHAT=$(sed -n '2p' tginfo.txt | tr -d '\r' | tr -d '\n')

echo "TOKEN len=${#TOKEN}  CHAT len=${#CHAT}"
if [ ${#TOKEN} -gt 8 ]; then
  echo "TOKEN masked=${TOKEN:0:4}...${TOKEN: -4}"
fi

# Check curl
if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl not installed. Install it: sudo apt install -y curl"
  exit 1
fi

# Call getMe
echo "-> Calling Telegram getMe..."
curl -s "https://api.telegram.org/bot${TOKEN}/getMe" -w "\nHTTP_CODE:%{http_code}\n" -o /tmp/tg_getme_resp.txt || true
cat /tmp/tg_getme_resp.txt
echo

# Send test message
TEXT="TEST from $(hostname) $(date)"
echo "-> Sending test message to chat_id=${CHAT}..."
curl -s -X POST "https://api.telegram.org/bot${TOKEN}/sendMessage" -d chat_id="${CHAT}" -d text="${TEXT}" -w "\nHTTP_CODE:%{http_code}\n" -o /tmp/tg_send_resp.txt || true
cat /tmp/tg_send_resp.txt
echo

# Validate last_sent.json (backup + reset if invalid)
if [ -f last_sent.json ]; then
  echo "-> Validating last_sent.json..."
  if command -v jq >/dev/null 2>&1; then
    if ! jq empty last_sent.json >/dev/null 2>&1; then
      ts=$(date +%s)
      echo "last_sent.json invalid JSON. Backing up to last_sent.json.bak.$ts and creating empty {}"
      mv last_sent.json last_sent.json.bak.$ts
      echo "{}" > last_sent.json
    else
      echo "last_sent.json OK (validated with jq)."
    fi
  else
    # fallback to python check
    if ! python3 -c "import json,sys; json.load(open('last_sent.json'))" >/dev/null 2>&1; then
      ts=$(date +%s)
      echo "last_sent.json invalid JSON (python check). Backing up and creating {}"
      mv last_sent.json last_sent.json.bak.$ts
      echo "{}" > last_sent.json
    else
      echo "last_sent.json OK (validated with python)."
    fi
  fi
else
  echo "last_sent.json not found — creating empty {}"
  echo "{}" > last_sent.json
fi
echo

# Show systemd status for myweb_scraper
echo "-> systemd status for myweb_scraper (may ask for sudo):"
if command -v systemctl >/dev/null 2>&1; then
  sudo systemctl status myweb_scraper --no-pager || true
else
  echo "systemctl not available on this machine."
fi

echo "-> Done."