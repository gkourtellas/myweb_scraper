# Docker deployment

Run the web scraper stack with Docker instead of systemd.

## Services

| Service | Container | Port | Role |
|---------|-----------|------|------|
| `scraper` | `myweb_scraper` | — | Playwright scraper loop (`main.py`) |
| `status` | `myweb_scraper_status` | 8001 | Status dashboard (`status_web.py`) |
| `homepage` | `myweb_scraper_homepage` | 6969 | Bookmarks homepage (`home_page.py`) |

## Quick start (on the Linux host)

```bash
cd /home/gk/myweb_scraper   # or your project path

cp .env.example .env
# Edit .env: MATCHBOT_HOST_DIR, SCRAPE_INTERVAL_SECONDS

docker compose build
docker compose up -d
```

Or use the helper script:

```bash
chmod +x docker/install.sh
./docker/install.sh
```

## Migrate from systemd

1. **Stop old services** (keeps your data files in the project dir):

   ```bash
   sudo systemctl disable --now myweb_scraper status_web home_page || true
   ```

2. **Ensure** `tginfo.txt`, `urls.txt`, `sent_log.json`, and `last_sent.json` stay in the project folder (they are mounted into containers).

3. **Start Docker** as above. Ports 8001 and 6969 stay the same, so bookmarks like `http://monitor:8001/` keep working.

4. **Matchbot JSON output** still goes to the host path configured as `MATCHBOT_HOST_DIR` (default `/home/gk/matchbot`).

## Useful commands

```bash
docker compose ps
docker compose logs -f scraper
docker compose restart scraper
docker compose run --rm scraper once    # single scrape, then exit
docker compose down
```

## Status UI controls

With `RUNTIME=docker`, the dashboard **Start / Stop / Restart** buttons control the `myweb_scraper` container via the Docker socket (mounted into the `status` service).

Logs are read from `logs/scraper.log` and `docker logs myweb_scraper`.

## Configuration

| Variable | Default | Meaning |
|----------|---------|---------|
| `SCRAPE_INTERVAL_SECONDS` | `3600` | Delay between scraper runs |
| `MATCHBOT_HOST_DIR` | `/home/gk/matchbot` | Host directory mounted at `/matchbot` |
| `MATCHBOT_OUTPUT_DIR` | `/matchbot` | Path used by `main.py` inside the container |
| `STATUS_PORT` | `8001` | Host port for status UI |
| `HOMEPAGE_PORT` | `6969` | Host port for homepage |

## Notes

- The project directory is bind-mounted to `/app`, so code and config changes on the host apply after `docker compose restart scraper` (no rebuild needed for Python edits).
- Rebuild after changing `requirements.txt` or `Dockerfile`: `docker compose build && docker compose up -d`.
- `tginfo.txt` is not copied into the image; keep it on the host and out of git.
