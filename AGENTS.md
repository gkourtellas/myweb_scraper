# AGENTS.md

## Project map
- This repo is a Python Playwright scraper plus two small HTTP servers.
- `main.py` is the headless scraper: it reads `urls.txt`, dedupes via `sent_log.json`/`last_sent.json`, and writes Matchbook tip JSON into `MATCHBOT_OUTPUT_DIR/autobet/tips/`.
- `status_web.py` serves the status dashboard on `:8001`; it can control the scraper via Docker (`myweb_scraper`) or systemd, depending on runtime detection.
- `home_page.py` serves the bookmarks/homepage UI on `:6969` with `/api/bookmarks`, `/api/stats`, and `/api/action`.
- `notify.py` owns Telegram delivery; it reads `tginfo.txt` (or `TGINFO_PATH`) and normalizes message text before sending.
- `simple_bot.py` is legacy paper-mode only; it intentionally refuses live mode.

## Data/config conventions
- `urls.txt` is the scraper’s main config file: pipe-delimited rows of `url|type|selector|date_format|lines_to_trim`; commented lines are disabled entries.
- Site-specific behavior is baked into `main.py` and `notify.py` for domains like `kingbet.com.cy`, `foxbet.gr`, `bethome.gr`, and `bet-on-arme.com`.
- Keep persistent/generated files local: `.env`, `tginfo.txt`, `sent_log.json`, `last_sent.json`, `state.json`, and `tginfo_test.txt` are git-ignored.
- `bookmarks.json` is the homepage data store; Docker also mounts it directly in `docker-compose.yml`.

## Developer workflow
- Local run: `python main.py`, `python status_web.py 8001`, or `python home_page.py 6969`.
- Docker stack: `docker compose up -d`, `docker compose logs -f scraper`, `docker compose run --rm scraper once`, `python restart.py`.
- The `scraper`, `status`, and `homepage` services in `docker-compose.yml` all use the same image; the `status` container mounts `/var/run/docker.sock` so its buttons can manage `myweb_scraper`.
- There is no dedicated test suite in the repo; use smoke runs and logs (`logs/scraper.log`, `docker logs myweb_scraper`, or `journalctl -u myweb_scraper`) to verify changes.

## Editing rules for this codebase
- Preserve backward compatibility in JSON/log formats unless you intentionally migrate the stored files.
- Be careful when touching selector logic or dedupe logic in `main.py`; those paths prevent duplicate Telegram alerts.
- Keep the UI/API contracts stable for `status_web.py` and `home_page.py` because the front-end JavaScript calls those exact endpoints.
- When adding a new scraper target, update `urls.txt` first and then mirror any special-case labeling in `notify.py` if Telegram output should show a friendly site name.
