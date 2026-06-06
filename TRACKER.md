# Project tracker — myweb_scraper

Living list of fixes, ideas, and follow-ups. Update as things ship or new issues appear.

---

## To verify

| Priority | Item | Notes |
|----------|------|--------|
| High | **Kingbet scraping** | After date-tab fix: confirm both `to-dynato-simeio-imeras` and `favori-imeras` click **today’s** tab when it exists, skip when it doesn’t (weekends/holidays), and don’t send stale Friday tips. Check logs for `Selected kingbet date tab:` or `No kingbet date tab for today`. Run once: `docker compose run --rm scraper once`. |

---

## To fix (known issues)

| Priority | Item | Notes |
|----------|------|--------|
| Medium | **Bethome** | Selector often times out (`betting-tips-listing--is-active-tip...`). May be “no tip today” OR page layout change. Re-check when site posts again; update `urls.txt` selector if needed. |
| Medium | **Status dashboard** (`status` container, port 8001) | Page reported not working. Scraper is fine; debug UI separately (logs, port, Docker socket permissions). |
| Low | **Docker image slimming** | `openpyxl` removed from code; optional `docker compose build` to drop unused dependency from image. |
| Low | **Old `tips_log_*.xlsx` files** | No longer written. Archive or delete on host if not needed. |

---

## To create / improve (future)

| Priority | Item | Notes |
|----------|------|--------|
| Medium | **Health check** | Simple script or compose `healthcheck` that verifies scraper ran recently (e.g. `logs/scraper.log` timestamp). |
| Medium | **Alert on scrape failure** | Telegram message when a URL errors N times in a row (optional). |
| Low | **Single `restart.py --all`** | Already exists; document in README / DOCKER.md. |
| Low | **`.env` in repo** | Keep only `.env.example`; ensure `tginfo.txt` stays out of git. |
| Low | **Remove legacy systemd units** | Files still on disk under `/etc/systemd/system/`; safe to delete after Docker stable for a week. |
| Low | **Homepage container** | Optional; stop if unused (`docker compose stop homepage`). |

---

## Done recently (reference)

- [x] Docker stack (`scraper`, `status`, `homepage`) — see `DOCKER.md`
- [x] Foxbet **stantar** selectors → `prediction_bet_1_3cols` (was hitting history table)
- [x] Kingbet date tabs — click today only; skip if no tab; no second `page.goto` wiping selection
- [x] Excel tip logging disabled (`notify.py` / `tips_log_*.xlsx`)
- [x] `restart.py` for `docker compose restart scraper`
- [x] `MATCHBOT_OUTPUT_DIR` env for matchbot JSON output
- [x] Shell scripts LF line endings + `.gitattributes`

---

## Config reminders

| Setting | Where | Default |
|---------|--------|---------|
| Scrape interval | `.env` → `SCRAPE_INTERVAL_SECONDS` | `3600` (1 hour) |
| Matchbot JSON output | `.env` → `MATCHBOT_HOST_DIR` | `/home/gk/matchbot` |
| Active URLs | `urls.txt` | Commented lines = disabled |
| Telegram | `tginfo.txt` (not in image) | — |

---

## Quick commands

```bash
python3 restart.py              # restart scraper
docker compose logs -f scraper  # watch a run
docker compose run --rm scraper once   # one-off scrape
```

---

*Last updated: 2026-06-01*
