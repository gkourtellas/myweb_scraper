# Useful Recovery Commands

## 1. Restart the server

If the machine or all interfaces are down:

- `sudo systemctl reboot`
- fallback: `sudo reboot`

## 2. Restart the bot service

The bot service is referred to as `myweb_scraper` in the status page code.

- Check status: `sudo systemctl status myweb_scraper --no-pager`
- Restart: `sudo systemctl restart myweb_scraper`
- Start: `sudo systemctl start myweb_scraper`
- Stop: `sudo systemctl stop myweb_scraper`
- View logs: `sudo journalctl -u myweb_scraper --no-pager -n 200`

If the service is not installed or systemctl is unavailable, run the bot directly from the project directory:

- `cd /home/gk/myweb_scraper`
- `python3 main.py`

## 3. Restart the homepage service

This is the service defined by `home_page.service`.

- Check status: `sudo systemctl status home_page --no-pager`
- Restart: `sudo systemctl restart home_page`
- Start: `sudo systemctl start home_page`
- Stop: `sudo systemctl stop home_page`
- View logs: `sudo journalctl -u home_page --no-pager -n 200`

## 4. Restart the status web console

This is the service defined by `status_web.service`.

- Check status: `sudo systemctl status status_web --no-pager`
- Restart: `sudo systemctl restart status_web`
- Start: `sudo systemctl start status_web`
- Stop: `sudo systemctl stop status_web`
- View logs: `sudo journalctl -u status_web --no-pager -n 200`

## 5. Reload systemd service definitions

If you update or reinstall service files:

- `sudo systemctl daemon-reload`

Then re-enable services if needed:

- `sudo systemctl enable --now home_page`
- `sudo systemctl enable --now status_web`

## 6. If interfaces are down, inspect processes and ports

- List Python processes: `ps aux | grep python | grep -v grep`
- Find port usage: `sudo ss -tulpn | grep -E '6969|8001'`
- Check service names on systemd: `systemctl list-units --type=service | grep -E 'home_page|status_web|myweb_scraper'`

## 7. Telegram bot connectivity test

Use this script to validate the Telegram token/chat config:

- `./check_and_test_tg.sh`

## 8. Helpful install commands

If you need to reinstall services from this repo:

- `./install_home_page.sh`
- `./install_status_web.sh`
