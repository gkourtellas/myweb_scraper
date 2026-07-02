#!/usr/bin/env python3
"""
Reads last_sent.json (Greek tips), works out the home/away team names
and translates them to English, then saves a new file with home_en /
away_en added to each tip.

Run this BEFORE place_bets.py.
"""

import json
import logging
import os
import re
import sys
import unicodedata

import requests
from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------------------------

TIPS_FILE = os.environ.get("TIPS_FILE", "/app/last_sent.json")
TRANSLATED_FILE = os.environ.get("TRANSLATED_FILE", "/app/last_sent.json")
LOG_FILE = os.environ.get("TRANSLATE_LOG_FILE", "/app/logs/translate.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("translate")

# ---------------------------------------------------------------------------
# KNOWN TEAM NAMES (Greek -> English)
# Add to this list whenever a new team shows up untranslated.
# Keys are lowercase, no accents removed -- matched as typed by the scraper.
# ---------------------------------------------------------------------------

KNOWN_TEAMS = {
    "βελγιο": "Belgium",
    "ιραν": "Iran",
    "νεα ζηλανδια": "New Zealand",
    "αιγυπτος": "Egypt",
    "ολλανδια": "Netherlands",
    "σουηδια": "Sweden",
    "ισπανια": "Spain",
    "σαουδικη αραβια": "Saudi Arabia",
    "σαμπαντελ": "Sabadell",
    "βαρμπεργκ": "Varbergs Bois",
    "λαντσκρονα": "Landskrona Bois",
}


def translate_via_api(text: str) -> str:
    """Fallback for team names not in KNOWN_TEAMS. Uses Google's free
    translate endpoint (no key needed, but unofficial -- can break)."""
    try:
        r = requests.get(
            "https://translate.googleapis.com/translate_a/single",
            params={
                "client": "gtx",
                "sl": "el",
                "tl": "en",
                "dt": "t",
                "q": text,
            },
            timeout=10,
        )
        r.raise_for_status()
        data = r.json()
        return data[0][0][0].strip()
    except Exception as e:
        log.error("Translation API failed for '%s': %s", text, e)
        return text  # fall back to original, untranslated


def strip_accents(text: str) -> str:
    """Removes Greek accent marks so ΟΛΛΑΝΔΙΑ and Ολλανδία both match
    the same dictionary key as ολλανδια."""
    nfkd = unicodedata.normalize("NFD", text)
    return "".join(c for c in nfkd if unicodedata.category(c) != "Mn")


def translate_team(name: str) -> str:
    name = name.strip()
    key = strip_accents(name.lower())
    if key in KNOWN_TEAMS:
        return KNOWN_TEAMS[key]
    translated = translate_via_api(name)
    log.info("Translated unknown team '%s' -> '%s' (consider adding to KNOWN_TEAMS)", name, translated)
    return translated


def extract_team_names(raw_text: str):
    """
    Pulls the 'Home - Away' or 'HOME - AWAY' line out of the raw scraped
    text. Returns (home, away) in their original (Greek) form, or
    (None, None) if no clear match-up line is found.
    """
    lines = [l.strip() for l in raw_text.split("\n") if l.strip()]

    for line in lines:
        # Matches lines like "Βέλγιο - Ιράν" or "ΟΛΛΑΝΔΙΑ - ΣΟΥΗΔΙΑ 20/06 20:00 1 & Over 1.5 2.08"
        m = re.match(r"^([^-\d][^-]*?)\s*-\s*([^-\d][^-]*?)(?:\s+\d|\s*$)", line)
        if m:
            home = m.group(1).strip()
            away = m.group(2).strip()
            # Strip trailing junk like dates that slipped in
            away = re.split(r"\s{2,}|\t", away)[0].strip()
            if home and away:
                return home, away

    # Fallback: sentragoal-style tips list date, time, then each team on
    # its own line with no dash (e.g. "21/06", "19:00", "Ισπανία",
    # "Σαουδική Αραβία", "1 & ...", "1.95"). Find two consecutive lines
    # that look like plain team names (letters only, no digits/slashes).
    def looks_like_team_name(s):
        return bool(re.match(r"^[A-Za-zΑ-Ωα-ωΆ-Ώά-ώ\s]+$", s)) and not re.search(r"\d", s)

    for i in range(len(lines) - 1):
        if looks_like_team_name(lines[i]) and looks_like_team_name(lines[i + 1]):
            return lines[i], lines[i + 1]

    return None, None


def main():
    if not os.path.exists(TIPS_FILE):
        log.error("Tips file not found: %s", TIPS_FILE)
        sys.exit(1)

    with open(TIPS_FILE, "r", encoding="utf-8") as f:
        tips = json.load(f)

    for key, tip in tips.items():
        raw_text = tip.get("text", "")
        home_gr, away_gr = extract_team_names(raw_text)

        if not home_gr or not away_gr:
            log.warning("Could not find team names in tip: %s", raw_text)
            continue

        tip["home_en"] = translate_team(home_gr)
        tip["away_en"] = translate_team(away_gr)
        log.info("%s vs %s -> %s vs %s", home_gr, away_gr, tip["home_en"], tip["away_en"])

    with open(TRANSLATED_FILE, "w", encoding="utf-8") as f:
        json.dump(tips, f, ensure_ascii=False, indent=2)

    log.info("Wrote translated tips to %s", TRANSLATED_FILE)


if __name__ == "__main__":
    main()
