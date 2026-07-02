# autobet

Reads daily tips, translates team names, places small bets on Matchbook.
Sends a Telegram message when it can't do something automatically.

## Files

- `translate_tips.py` — adds English team names to the tips file
- `place_bets.py` — places the actual bets
- `run_autobet.sh` — runs both, in order (use this in cron)
- `.env` — your credentials (fill in, never commit to git)
- `requirements.txt` — Python packages needed

## Setup

1. Fill in `.env`
2. Make sure `TIPS_FILE` in `.env` points to where your scraper writes
   `last_sent.json` inside the container
3. Add to your Dockerfile (see below)
4. Add a cron entry to run `run_autobet.sh` once a day

## Wiring into the existing Dockerfile

Add these lines after the existing `COPY` steps:

```dockerfile
COPY autobet/ autobet/
RUN pip install -r autobet/requirements.txt \
    && chmod +x autobet/run_autobet.sh
```

## Running manually (to test)

```bash
docker exec -it <container_name> bash
cd autobet
python3 translate_tips.py
python3 place_bets.py
```

## Cron (inside the container, or via host cron + docker exec)

```cron
0 9 * * * /app/autobet/run_autobet.sh >> /app/logs/autobet_cron.log 2>&1
```

## Notes

- Only handles simple 1 / 2 / draw bets for now
- Anything else (combo bets, cards, corners) gets sent to you on
  Telegram instead of guessed
- Add new team names to `KNOWN_TEAMS` in `translate_tips.py` as they show up,
  for faster/more reliable translation
