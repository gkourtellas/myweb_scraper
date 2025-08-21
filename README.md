# Web Tip Scraper (Playwright + Telegram)

Scrapes predefined pages for daily tips/content, ignores minor edits (e.g., “win/lose” added) by comparing the trimmed message it actually sends, delivers Telegram notifications, and logs each tip in JSON and a monthly Excel file.

## How it works

- Reads targets from `urls.txt` (URL, type, CSS selector, optional date format and line trim).
- Loads each page with Playwright (headless Chromium), extracts text, and builds a combined content.
- Dedupe: trims to the top N lines (what is sent to Telegram) and compares that against the last sent entry using similarity to avoid notifying on small changes below the fold.
- Sends a Telegram message if the trimmed content is new/significantly different.
- Logs:
  - `sent_log.json`: daily run log (auto-cleared daily)
  - `last_sent.json`: persistent dedupe store (saves the trimmed content)
  - `tips_log_YYYY_MM.xlsx`: monthly Excel log of tips

## Requirements

- Linux server with Python 3.8+ and bash
- Internet access
- Telegram bot token and chat ID

Python packages:

- playwright
- requests
- openpyxl

Install system-wide dependencies and browsers with one command:

- After activating your venv, run: `playwright install --with-deps chromium`

## Installation (Linux)

1. SSH to your server and prepare a folder

   ```bash
   mkdir -p ~/myweb_scraper && cd ~/myweb_scraper
   ```

   - Copy the project files here (git clone or scp)

2. Create a virtual environment

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python -m pip install --upgrade pip
   ```

3. Install dependencies

   ```bash
   pip install playwright requests openpyxl
   playwright install --with-deps chromium
   ```

4. Configure Telegram

   - Create a `tginfo.txt` file with two lines:
     - Line 1: `BOT_TOKEN`
     - Line 2: `CHAT_ID`

5. Configure targets in `urls.txt`

   - One entry per line. Format:
     - `url|type|css_selector|date_format_or_lines_to_trim|optional_lines_to_trim`
   - type:
     - `date` = the site uses a date in the URL (appends DD-MM-YY)
     - `static` = normal URL (or leave anything other than “date”)
   - date_format (optional): one of `dd/mm`, `dd/mm/yy`, `mm/dd` (used to verify today’s tip)
   - lines_to_trim (optional): integer, how many lines from the top of the extracted text to include in the Telegram message (also used for dedupe)
   - Examples:
     - `https://example.com/tips/|static|.post-title,.post-body|dd/mm|8`
     - `https://betparade.net/to-over-25-tis-imeras-|date|.entry-content|dd/mm|6`

## Usage (manual run)

```bash
source .venv/bin/activate
python main.py
```

- The script loops forever and sleeps ~100 minutes between checks.

Files created/used:

- `tginfo.txt` (your token and chat ID)
- `urls.txt` (your targets)
- `sent_log.json` (auto-cleared daily)
- `last_sent.json` (persistent dedupe; stores the trimmed content)
- `tips_log_YYYY_MM.xlsx` (monthly Excel log)

## Optional: Run automatically on startup (systemd)

1. Create a service file

   ```bash
   sudo nano /etc/systemd/system/myweb_scraper.service
   ```

   - Paste and adjust paths and your username:

     ```
     [Unit]
     Description=My Web Scraper (Playwright + Telegram)
     After=network-online.target

     [Service]
     Type=simple
     User=YOUR_LINUX_USER
     WorkingDirectory=/home/YOUR_LINUX_USER/myweb_scraper
     Environment=PYTHONUNBUFFERED=1
     ExecStart=/home/YOUR_LINUX_USER/myweb_scraper/.venv/bin/python /home/YOUR_LINUX_USER/myweb_scraper/main.py
     Restart=always
     RestartSec=10

     [Install]
     WantedBy=multi-user.target
     ```

2. Enable and start

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable myweb_scraper
   sudo systemctl start myweb_scraper
   sudo systemctl status myweb_scraper
   ```

   - Logs: `journalctl -u myweb_scraper -f`

## Useful commands

Navigation and basics:

```bash
cd ~/myweb_scraper
ls -la
pwd
```

Virtual environment:

```bash
# Create
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Deactivate
deactivate

# Install deps
pip install playwright requests openpyxl

# Freeze
pip freeze > requirements.txt

# Install from file
pip install -r requirements.txt
```

Run without systemd:

```bash
source .venv/bin/activate && nohup python main.py > run.log 2>&1 &  echo $! > app.pid
tail -f run.log
```

- Stop: `kill "$(cat app.pid)"` or `pkill -f "python main.py"`

Update code (examples):

- If using git: `git pull` then `git push`
- If you get “Updates were rejected… fetch first”:
  ```bash
  git pull --rebase
  git push
  ```
- If copying via scp: `scp -r . YOURUSER@YOURSERVER:~/myweb_scraper/`
- After updates (systemd): `sudo systemctl restart myweb_scraper`

Playwright troubleshooting:

```bash
# Reinstall browsers/deps
playwright install --with-deps chromium

# Test a quick run
python -c "from playwright.sync_api import sync_playwright as sp; print('OK')"
```

## Project structure (key files)

- `main.py` — scraping and dedupe logic (compares the trimmed message to ignore minor changes)
- `notify.py` — Telegram sender and Excel logging
- `urls.txt` — targets and selectors (you edit this)
- `tginfo.txt` — bot token and chat ID (two lines)
- `last_sent.json` — persistent last trimmed content per URL
- `sent_log.json` — daily run log
- `tips_log_YYYY_MM.xlsx` — monthly tip logs

Tip: Keep `tginfo.txt` private and never commit it to public repos.
