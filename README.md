# myweb_scraper — Rebuild & Recovery Guide

This document contains all steps required to rebuild, configure, and recover the project from scratch.
Keep a copy off the server (USB, cloud vault) so you can restore if the machine is lost.

Summary
- Repo: https://github.com/gkourtellas/myweb_scraper
- Services: `myweb_scraper` (bot), `home_page` (web homepage), `status_web` (status console)
- Runtime files: `/var/lib/myweb_scraper` (bookmarks.json, sent_log.json, last_sent.json)

Requirements
- Ubuntu/Debian or similar Linux with systemd.
- Python 3.10+ (recommended).
- System user: `gk` (service units use this user in this repo); adapt if different.

Files and locations
- Repository root: project source, service installers and systemd unit examples.
- Runtime directory (persistent, outside repo): `/var/lib/myweb_scraper` (bookmarks.json saved here).
- Telegram credentials: `tginfo.txt` (NOT committed). Format:
  - Line 1: Telegram bot token
  - Line 2: chat id (numeric)

Quick rebuild (minimal)
1. Clone repository

   git clone git@github.com:gkourtellas/myweb_scraper.git
   cd myweb_scraper

2. Create Python venv and install dependencies

   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   # Install playwright browsers (if using playwright)
   python -m playwright install

3. Create runtime directory and set ownership (run as root once)

   sudo mkdir -p /var/lib/myweb_scraper
   sudo chown gk:gk /var/lib/myweb_scraper
   sudo chmod 700 /var/lib/myweb_scraper

4. Add Telegram credentials (secure)

   # Create tginfo.txt locally (DO NOT commit)
   # Line1 = BOT_TOKEN
   # Line2 = CHAT_ID

   chmod 600 tginfo.txt

5. Install systemd services

   ./install_home_page.sh
   ./install_status_web.sh

   # For the main bot service `myweb_scraper` create a systemd unit if missing.
   # Example unit (create /etc/systemd/system/myweb_scraper.service):

   [Unit]
   Description=MyWeb Scraper Bot
   After=network.target

   [Service]
   Type=simple
   User=gk
   WorkingDirectory=/home/gk/myweb_scraper
   Environment=PYTHONUNBUFFERED=1
   ExecStart=/home/gk/myweb_scraper/venv/bin/python3 /home/gk/myweb_scraper/main.py
   Restart=always
   RestartSec=5

   [Install]
   WantedBy=multi-user.target

   # Then:
   sudo systemctl daemon-reload
   sudo systemctl enable --now myweb_scraper

6. Start / check services

   sudo systemctl status myweb_scraper --no-pager
   sudo systemctl status home_page --no-pager
   sudo systemctl status status_web --no-pager

7. Test Telegram connectivity

   ./check_and_test_tg.sh

Security notes
- `tginfo.txt` contains secrets. Keep locally, set `chmod 600 tginfo.txt`, and DO NOT add to git.
- Rotate bot token via @BotFather immediately if exposed.
- Consider storing secrets in environment variables or a vault (vault, AWS Secrets Manager).
- Lock dashboards: bind to `127.0.0.1` or protect with HTTP auth / reverse proxy.

Sudoers recommendation (restrict UI commands)
- Use `sudo visudo -f /etc/sudoers.d/myweb_scraper` to add:
  gk ALL=(root) NOPASSWD: /bin/systemctl start myweb_scraper, /bin/systemctl stop myweb_scraper, /bin/systemctl restart myweb_scraper, /bin/systemctl restart home_page, /bin/systemctl restart status_web, /sbin/reboot

Backups and restore
- Rotate backups of `tginfo.txt` before editing: `cp tginfo.txt tginfo.txt.bak.YYYYMMDD`.
- Runtime state to back up regularly: `/var/lib/myweb_scraper/bookmarks.json`, `sent_log.json`, `last_sent.json`, `output.log`, `nohup.out`.
- To restore: replace the files in repo or runtime dir and restart services.

Logs & troubleshooting
- Journalctl: `sudo journalctl -u myweb_scraper --no-pager -n 500`
- Local logs: `output.log`, `nohup.out` in repo root (may be used by startup scripts)

Rebuild checklist (one-liner order)

1. Clone → 2. venv & deps → 3. playwright install → 4. runtime dir → 5. tginfo.txt (secure) → 6. install services → 7. start services → 8. test Telegram

Recent updates
- Added JSON output support for SendraGoal and KingBet tips.
- Added files written to `/home/gk/matchbot/autobet/tips/`.
- Added separate outputs for `kingbet_to_dynato.json` and `kingbet_to_favori.json`.
- Confirmed `myweb_scraper` restart command: `sudo systemctl restart myweb_scraper`.

If you want, I can convert these into a single `bootstrap.sh` that performs safe, reviewable steps.
