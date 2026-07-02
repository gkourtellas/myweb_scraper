#!/usr/bin/env python3
"""
Reads daily football tips from last_sent.json, finds the matching
match on Matchbook, and places a small bet automatically.

If a tip can't be matched safely, it sends a Telegram message
instead of guessing.

Run this once a day with cron.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime, timedelta, timezone

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# SETTINGS - fill these in
# ---------------------------------------------------------------------------

TIPS_FILE = os.environ.get("TIPS_FILE", "/app/last_sent.json")
LOG_FILE = os.environ.get("LOG_FILE", "/app/logs/matchbook_bets.log")

MATCHBOOK_USERNAME = os.environ.get("MATCHBOOK_USERNAME", "")
MATCHBOOK_PASSWORD = os.environ.get("MATCHBOOK_PASSWORD", "")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

STAKE = float(os.environ.get("STAKE", "0.10"))  # fixed amount per bet, in your account currency

MATCHBOOK_API = "https://api.matchbook.com"
SOCCER_SPORT_ID = 15  # confirmed from Matchbook reference data

# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("matchbook_bot")


# ---------------------------------------------------------------------------
# TELEGRAM ALERT
# ---------------------------------------------------------------------------

def send_telegram_alert(message: str):
    """Send a message to your own Telegram so you can act manually."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        log.warning("Telegram not configured, skipping alert: %s", message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": message}, timeout=10)
    except Exception as e:
        log.error("Failed to send Telegram alert: %s", e)


# ---------------------------------------------------------------------------
# MATCHBOOK API HELPERS
# ---------------------------------------------------------------------------

class MatchbookClient:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.session_token = None
        self.session = requests.Session()

    def login(self):
        url = f"{MATCHBOOK_API}/bpapi/rest/security/session"
        payload = {"username": self.username, "password": self.password}
        headers = {"content-type": "application/json;charset=UTF-8", "accept": "*/*"}
        r = self.session.post(url, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        data = r.json()
        self.session_token = data["session-token"]
        log.info("Logged into Matchbook as %s", self.username)

    def _headers(self):
        return {
            "session-token": self.session_token,
            "content-type": "application/json;charset=UTF-8",
            "accept": "application/json",
        }

    def get_events(self, sport_ids, after=None, before=None):
        """List upcoming football events."""
        url = f"{MATCHBOOK_API}/edge/rest/events"
        params = {"sport-ids": sport_ids, "per-page": 500}
        if after:
            params["after"] = int(after.timestamp())
        if before:
            params["before"] = int(before.timestamp())
        r = self.session.get(url, headers=self._headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("events", [])

    def get_markets(self, event_id):
        url = f"{MATCHBOOK_API}/edge/rest/events/{event_id}/markets"
        r = self.session.get(url, headers=self._headers(), timeout=15)
        r.raise_for_status()
        return r.json().get("markets", [])

    def get_runners(self, event_id, market_id):
        url = f"{MATCHBOOK_API}/edge/rest/events/{event_id}/markets/{market_id}/runners"
        params = {"include-prices": "true"}
        r = self.session.get(url, headers=self._headers(), params=params, timeout=15)
        r.raise_for_status()
        return r.json().get("runners", [])

    def submit_offer(self, runner_id, odds, stake, side="back"):
        url = f"{MATCHBOOK_API}/edge/rest/v2/offers"
        payload = {
            "odds-type": "DECIMAL",
            "exchange-type": "back-lay",
            "offers": [
                {
                    "runner-id": runner_id,
                    "side": side,
                    "odds": odds,
                    "stake": stake,
                    "keep-in-play": False,
                }
            ],
        }
        r = self.session.post(url, headers=self._headers(), json=payload, timeout=15)
        r.raise_for_status()
        return r.json()


# ---------------------------------------------------------------------------
# TIP PARSING
# ---------------------------------------------------------------------------

# Maps the Greek-derived translated bet codes to what we look for in the
# Match Odds market. "1" = home win, "2" = away win, "X" = draw.
SELECTION_CODE_MAP = {
    "1": "home",
    "2": "away",
    "x": "draw",
}


def normalize_team_name(name: str) -> str:
    """Lowercase, strip accents-ish noise, trim spaces, for fuzzy matching."""
    name = name.strip().lower()
    name = re.sub(r"[^a-z0-9\s]", "", name)
    name = re.sub(r"\s+", " ", name)
    return name


def parse_tip_text(raw_text: str, translated_home: str, translated_away: str):
    """
    Pulls out the bet selection code (1/2/X) and odds from the raw scraped
    text. Returns None if it's not a simple 1/2/X match-odds tip (skip
    anything fancier like "Over 1.5 cards" for now -- those don't map to
    Matchbook's Match Odds market and should go to manual review).
    """
    # Look for a standalone "1", "2", or "X" token, and a decimal odds number
    odds_match = re.search(r"\b(\d+\.\d+)\b", raw_text)
    odds = float(odds_match.group(1)) if odds_match else None

    # Find a selection token: standalone digit 1/2 or letter X, not part of
    # a longer combination like "1 & Over 1.5"
    selection = None
    for line in raw_text.replace("\t", "\n").split("\n"):
        line = line.strip()
        if line in ("1", "2", "X", "x"):
            selection = line.lower()
            break
        # foxbet style: "2 1.60" on one line
        m = re.match(r"^([12xX])\s+\d", line)
        if m:
            selection = m.group(1).lower()
            break

    is_combo = "&" in raw_text or "over" in raw_text.lower() or "under" in raw_text.lower()

    if selection is None or odds is None or is_combo:
        return None  # not a plain 1/2/X tip, needs manual handling

    return {
        "selection": selection,
        "odds": odds,
        "home": translated_home,
        "away": translated_away,
    }


# ---------------------------------------------------------------------------
# MATCHING TIP TO MATCHBOOK EVENT/RUNNER
# ---------------------------------------------------------------------------

def find_event(client: MatchbookClient, home: str, away: str, tip_date: str):
    """Search Matchbook events around the tip date for a team-name match."""
    day = datetime.strptime(tip_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    after = day - timedelta(days=1)
    before = day + timedelta(days=2)

    events = client.get_events(SOCCER_SPORT_ID, after=after, before=before)

    home_n = normalize_team_name(home)
    away_n = normalize_team_name(away)

    for event in events:
        name_n = normalize_team_name(event.get("name", ""))
        if home_n in name_n and away_n in name_n:
            return event
    return None


def find_match_odds_runner(client: MatchbookClient, event, selection, home, away):
    """Find the Match Odds market and the runner for the given selection."""
    markets = client.get_markets(event["id"])
    market = next((m for m in markets if m.get("market-type") == "one_x_two"), None)
    if not market:
        return None, None

    runners = client.get_runners(event["id"], market["id"])

    home_n = normalize_team_name(home)
    away_n = normalize_team_name(away)

    target_runner = None
    if selection == "1":
        target_runner = next((r for r in runners if normalize_team_name(r["name"]) == home_n), None)
    elif selection == "2":
        target_runner = next((r for r in runners if normalize_team_name(r["name"]) == away_n), None)
    elif selection == "x":
        target_runner = next((r for r in runners if normalize_team_name(r["name"]) in ("draw", "the draw")), None)

    return market, target_runner


def best_back_price(runner):
    """Pull the best available back price from a runner's price list."""
    prices = runner.get("prices", [])
    back_prices = [p for p in prices if p.get("side") == "back"]
    if not back_prices:
        return None
    return min(back_prices, key=lambda p: p["odds"])


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def main():
    if not os.path.exists(TIPS_FILE):
        log.error("Tips file not found: %s", TIPS_FILE)
        sys.exit(1)

    with open(TIPS_FILE, "r", encoding="utf-8") as f:
        tips = json.load(f)

    if not MATCHBOOK_USERNAME or not MATCHBOOK_PASSWORD:
        log.error("Matchbook credentials not set (MATCHBOOK_USERNAME / MATCHBOOK_PASSWORD env vars)")
        sys.exit(1)

    client = MatchbookClient(MATCHBOOK_USERNAME, MATCHBOOK_PASSWORD)
    client.login()

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    for key, tip in tips.items():
        raw_text = tip.get("text", "")
        tip_date = tip.get("date", today)

        # Pull team names from translated text -- this script expects the
        # translated home/away teams to already be present. If you're
        # piping straight from the Greek scraper, run translation first
        # and add "home_en" / "away_en" fields to each tip before this
        # script runs.
        home = tip.get("home_en")
        away = tip.get("away_en")

        if not home or not away:
            log.warning("Tip missing translated team names, skipping: %s", key)
            send_telegram_alert(
                f"⚠️ Tip needs manual review (no translated team names):\n{raw_text}"
            )
            continue

        parsed = parse_tip_text(raw_text, home, away)
        if not parsed:
            log.info("Tip is not a simple 1/2/X bet, sending for manual review: %s", raw_text)
            send_telegram_alert(
                f"⚠️ Tip needs manual review (not a simple 1/2/X bet):\n{home} - {away}\n{raw_text}"
            )
            continue

        event = find_event(client, home, away, tip_date)
        if not event:
            log.warning("No Matchbook event found for %s vs %s", home, away)
            send_telegram_alert(
                f"⚠️ Could not find match on Matchbook:\n{home} vs {away} ({tip_date})\nPlease place manually."
            )
            continue

        market, runner = find_match_odds_runner(client, event, parsed["selection"], home, away)
        if not market or not runner:
            log.warning("No matching market/runner for %s vs %s", home, away)
            send_telegram_alert(
                f"⚠️ Found the match but not the right betting market:\n{home} vs {away}\nPlease place manually."
            )
            continue

        price = best_back_price(runner)
        if not price:
            log.warning("No price available for runner %s", runner.get("name"))
            send_telegram_alert(
                f"⚠️ No price currently available:\n{home} vs {away} - {runner.get('name')}\nPlease place manually."
            )
            continue

        try:
            result = client.submit_offer(runner["id"], price["odds"], STAKE, side="back")
            placed = result["offers"][0]
            log.info(
                "Bet placed: %s vs %s, selection=%s, odds=%s, stake=%s, status=%s",
                home, away, parsed["selection"], placed["odds"], placed["stake"], placed["status"],
            )
            send_telegram_alert(
                f"✅ Bet placed: {home} vs {away}\n"
                f"Selection: {runner.get('name')}\n"
                f"Odds: {placed['odds']} | Stake: {placed['stake']}\n"
                f"Status: {placed['status']}"
            )
        except Exception as e:
            log.error("Failed to place bet for %s vs %s: %s", home, away, e)
            send_telegram_alert(
                f"❌ Failed to place bet automatically:\n{home} vs {away}\nError: {e}\nPlease place manually."
            )


if __name__ == "__main__":
    main()
