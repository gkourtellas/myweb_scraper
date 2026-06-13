# Matchbook Simple Bot (V1)

This project now has two modes:
- a browser UI for local inspection and testing
- a headless live bot for a Ubuntu server

The live bot is intentionally narrow:
- Football only
- Match Odds only
- Back bets only
- Odds between 1.45 and 1.60
- Minimum stake

## Browser UI

- Live dashboard for the headless bot
- Shows current balance, free funds, open bets, current stake step, P&L, yield, and recent bets
- Displays the full 6-step staking ladder and highlights the active step
- Keeps the simulation panel below the dashboard for ad-hoc testing

## Live headless bot

- Logs in with your Matchbook username/password through the official API
- Finds football events
- Filters Match Odds markets
- Checks back prices between 1.45 and 1.60
- Places a back bet at the minimum stake when the signal matches
- Uses a 6-step staking ladder: 0.1, 0.3, 0.9, 2.7, 8.1, 24.3
- Resets to 0.1 after a win and advances one step after a loss
- Persists state so it does not repeat the same signal

## Local login details

If you are testing with your Matchbook browser login, put the values in a local `.env` file or keep them in `.env.example` for now.

Required fields:

- `MATCHBOOK_USERNAME`
- `MATCHBOOK_PASSWORD`
- `MATCHBOOK_LOGIN_URL`

The bot reads these locally and uses them for the official Matchbook API session login.

## Telegram notifications

Create `tginfo_test.txt` with two lines:

1. Telegram bot token
2. Telegram chat id

The live bot sends notifications when:

- a bet is placed
- a bet is settled (with next staking step)

## Files

- `app.py`: local web server and API endpoints
- `templates/index.html`: browser UI
- `matchbook_client.py`: official Matchbook API client
- `matchbook_live_bot.py`: headless live football bot
- `simple_bot.py`: legacy paper-mode simulator
- `live_config.example.json`: live bot settings
- `state.json`: persistent bot state

## Run the headless bot

```powershell
.\.venv\Scripts\python.exe .\matchbook_live_bot.py
```

You can override the Telegram file path:

```powershell
.\.venv\Scripts\python.exe .\matchbook_live_bot.py --tg-info .\tginfo_test.txt
```

To run a single scan and exit:

```powershell
.\.venv\Scripts\python.exe .\matchbook_live_bot.py --once
```

## Run on Ubuntu with systemd

Use the service template in [matchbook-bot.service.example](matchbook-bot.service.example) as the basis for a systemd unit file on your server.

Typical layout:

- project at `/opt/matchbook`
- local secrets in `/opt/matchbook/.env`
- service enabled through `systemctl enable --now matchbook-bot`

## Run in Browser

```powershell
.\.venv\Scripts\python.exe .\app.py
```

Then open:

```text
http://127.0.0.1:5000
```

## Optional legacy simulator

```powershell
.\.venv\Scripts\python.exe .\simple_bot.py --config .\config.example.json --markets .\markets.example.json
```

## Next step for live mode

When you obtain official Matchbook API credentials, we can add:
1. Authenticated API client
2. Rate limiter and retry/backoff
3. Live order placement/cancel
4. Reconciliation and persistent state
5. Kill switch and watchdogs
