# Web Tip Scraper (Playwright + Telegram)

This project scrapes predefined webpages for daily tips or content, compares new data to previous results, and sends Telegram notifications only when significant changes are detected. It avoids duplicate or trivial notifications and logs all tips in JSON and Excel files.

## Features
- Scrapes multiple sites using Playwright (headless browser)
- Customizable targets via `urls.txt` (URL, type, CSS selector, etc.)
- Deduplication: only notifies for meaningful changes
- Sends Telegram messages using your bot
- Logs tips to JSON and monthly Excel files
- Easy setup and automation (systemd or manual)

## Requirements
- Linux server (Python 3.8+ and bash)
- Internet access
- Telegram bot token and chat ID
- Python packages (all listed in `requirements.txt`):
  - playwright
  - requests
  - openpyxl

## Quick Setup
1. **Clone or copy the project files**
2. **Create and activate a virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```
3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   playwright install --with-deps chromium
   ```
4. **Configure Telegram:**
   - Create a file `tginfo.txt` with two lines:
     - Line 1: BOT_TOKEN
     - Line 2: CHAT_ID
5. **Configure scraping targets in `urls.txt`:**
   - Each line: `url|type|css_selector|date_format_or_lines_to_trim|optional_lines_to_trim`
   - See below for details and examples.

## Usage
- **Manual run:**
  ```bash
  source venv/bin/activate
  python main.py
  ```
- The script loops and checks sites every ~100 minutes.
- All logs and tip history are saved in the project folder.

## File Overview
- `main.py` — scraping and deduplication logic
- `notify.py` — Telegram messaging and Excel logging
- `urls.txt` — list of target sites and selectors
- `tginfo.txt` — Telegram bot token and chat ID
- `last_sent.json` — persistent dedupe store
- `sent_log.json` — daily run log
- `tips_log_YYYY_MM.xlsx` — monthly Excel log

## urls.txt Format
Each line defines a target site:
```
url|type|css_selector|date_format_or_lines_to_trim|optional_lines_to_trim
```
- **type:**
  - `date` — appends today's date to the URL
  - `static` — normal URL
- **date_format:** (optional)
  - `dd/mm`, `dd/mm/yy`, `mm/dd` (used to verify today's tip)
- **lines_to_trim:** (optional)
  - Integer: how many lines from the top to include in the Telegram message
- **Examples:**
  - `https://example.com/tips/|static|.post-title,.post-body|dd/mm|8`
  - `https://betparade.net/to-over-25-tis-imeras-|date|.entry-content|dd/mm|6`

## Automation (systemd)
1. **Create a service file:**
   ```bash
   sudo nano /etc/systemd/system/myweb_scraper.service
   ```
   Paste and adjust paths and username:
   ```ini
   [Unit]
   Description=Web Tip Scraper
   After=network-online.target

   [Service]
   Type=simple
   User=YOUR_LINUX_USER
   WorkingDirectory=/home/YOUR_LINUX_USER/myweb_scraper
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/home/YOUR_LINUX_USER/myweb_scraper/venv/bin/python /home/YOUR_LINUX_USER/myweb_scraper/main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```
2. **Enable and start:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable myweb_scraper
   sudo systemctl start myweb_scraper
   sudo systemctl status myweb_scraper
   ```
   - View logs: `journalctl -u myweb_scraper -f`

## Troubleshooting & Tips
- **Virtual environment commands:**
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  deactivate
  pip install -r requirements.txt
  pip freeze > requirements.txt
  ```
- **Playwright browser install:**
  ```bash
  playwright install --with-deps chromium
  ```
- **Test Playwright install:**
  ```bash
  python -c "from playwright.sync_api import sync_playwright; print('OK')"
  ```
- **Run in background (manual):**
  ```bash
  source venv/bin/activate && nohup python main.py > run.log 2>&1 & echo $! > app.pid
  tail -f run.log
  kill "$(cat app.pid)"
  ```
- **Update code:**
  - If using git: `git pull` then `git push`
  - If copying via scp: `scp -r . USER@SERVER:~/myweb_scraper/`
  - After updates (systemd): `sudo systemctl restart myweb_scraper`

## Security
- Keep `tginfo.txt` private. Never commit it to public repos.

## Project Structure
```
main.py
notify.py
urls.txt
tginfo.txt
last_sent.json
sent_log.json
tips_log_YYYY_MM.xlsx
requirements.txt
README.md
```

---
For questions or improvements, open an issue or contact the maintainer.
