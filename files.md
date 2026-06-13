--- docker-compose.yml ---
services:
  scraper:
    build: .
    image: myweb-scraper:latest
    container_name: myweb_scraper
    restart: unless-stopped
    env_file:
      - .env
    environment:
      PYTHONUNBUFFERED: "1"
      MATCHBOT_OUTPUT_DIR: ${MATCHBOT_OUTPUT_DIR:-/matchbot}
      SCRAPE_INTERVAL_SECONDS: ${SCRAPE_INTERVAL_SECONDS:-3600}
      TGINFO_PATH: ${TGINFO_PATH:-/app/tginfo.txt}
    volumes:
      - ./:/app
      - ${MATCHBOT_HOST_DIR:-/home/gk/matchbot}:/matchbot
    command: ["scraper"]

  status:
    build: .
    image: myweb-scraper:latest
    container_name: myweb_scraper_status
    restart: unless-stopped
    depends_on:
      - scraper
    ports:
      - "${STATUS_PORT:-8001}:8001"
    environment:
      PYTHONUNBUFFERED: "1"
      RUNTIME: docker
      DOCKER_SCRAPER_CONTAINER: myweb_scraper
      STATUS_PORT: "8001"
    volumes:
      - ./:/app
      - /var/run/docker.sock:/var/run/docker.sock
    command: ["status"]

  homepage:
    build: .
    image: myweb-scraper:latest
    container_name: myweb_scraper_homepage
    restart: unless-stopped
    ports:
      - "${HOMEPAGE_PORT:-6969}:6969"
    environment:
      PYTHONUNBUFFERED: "1"
      HOMEPAGE_PORT: "6969"
    volumes:
      - ./:/app
      - ./bookmarks.json:/app/bookmarks.json
    command: ["homepage"]


--- Dockerfile ---
FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py notify.py status_web.py home_page.py urls.txt bookmarks.json ./
COPY docker/ docker/

RUN chmod +x docker/run-scraper.sh docker/entrypoint.sh \
    && mkdir -p /app/logs

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["scraper"]


--- requirements.txt ---
playwright==1.54.0
requests>=2.31.0
docker>=7.0.0


--- urls.txt ---
#https://footballpredictions.com/betting-tips/bet-of-the-day/|static|body > div.boxed-wrap.clearfix > div.boxed-content-wrapper.clearfix > div.inner > div.main_container > div.main-col > div.newsitem-wrapper > div.newsitem-content > div.botd-background|4
https://sportbet.gr/prognostika-to-dynato-simeio-imeras/|static|#featured_archive > div.featured-item.active > table > tbody > tr:nth-child(1) > td.names.hidden-sm-down,#featured_archive > div.featured-item.active > table > tbody > tr:nth-child(3) > td:nth-child(3),#featured_archive > div.featured-item.active > table > tbody > tr:nth-child(3) > td:nth-child(4)|20
https://www.foxbet.gr/316026/to-dunato-simeio-tis-imeras|static|table.prediction_bet_1_3cols tbody tr:first-child td:nth-child(1),table.prediction_bet_1_3cols tbody tr:first-child td:nth-child(2)|4
https://www.foxbet.gr/316014/to-stantar-tis-imeras|static|table.prediction_bet_1_3cols tbody tr:first-child td:nth-child(1),table.prediction_bet_1_3cols tbody tr:first-child td:nth-child(3)|4
https://www.bethome.gr/prognostika-to-simeio-tis-imeras/|static|#main > div.betting-tips.mb-5 > div.betting-tips-listing.betting-tips-listing--rounded.betting-tips-listing--is-active-tip.betting-tips-listing--open > div.betting-tips-listing__table > div:nth-child(2)|4
#https://www.bet-on-arme.com/to-dinato-simeio-tis-imeras/|static|div.position-relative.mt-3 > table > tbody > tr:nth-child(2) > td:nth-child(1),div.position-relative.mt-3 > table > tbody > tr:nth-child(2) > td:nth-child(2),div.position-relative.mt-3 > table > tbody > tr:nth-child(2) > td:nth-child(3),div.position-relative.mt-3 > table > tbody > tr:nth-child(2) > td:nth-child(4),div.position-relative.mt-3 > table > tbody > tr:nth-child(2) > td:nth-child(5)|6
https://www.kingbet.com.cy/to-dynato-simeio-imeras/|static|div.betting-features__listing div.betting-feature.block:first-child .betting-feature__match-name,div.betting-features__listing div.betting-feature.block:first-child .betting-feature__prediction|5
https://www.kingbet.com.cy/favori-imeras/|static|div.betting-features__listing div.betting-feature.block:first-child .betting-feature__match-name,div.betting-features__listing div.betting-feature.block:first-child .betting-feature__prediction|5
#https://www.kingbet.com.cy/to-stantar-tis-imeras/|static|body > main > div > div > div > div.column.column--has-slider.column--has-sidebar > div:nth-child(2) > div.block.betting-features__wrapper.nx-offer-loaded > div.betting-features__listing.block > div.betting-feature.block|5
https://www.sentragoal.gr/dunato-simeio-imeras/|static|div[id^='predictions_'][id$='_page_container'] > table > tbody > tr:nth-child(2) > td.predictions_table__date.text-center.font-0-8.text-nowrap.text-gray-500,div[id^='predictions_'][id$='_page_container'] > table > tbody > tr:nth-child(2) > td.predictions_table__fixture.text-start.font-0-9,div[id^='predictions_'][id$='_page_container'] > table > tbody > tr:nth-child(2) > td.predictions_table__market.text-start.fw-medium.font-0-9,div[id^='predictions_'][id$='_page_container'] > table > tbody > tr:nth-child(2) > td.predictions_table__betting-odd.text-center.text-nowrap|8
#https://www.betarades.gr/to-dynato-simeio-tis-imeras-sto-stoixima-prognostiko-apo-betarades/|static|body > div.wall_ad_container > div > div > main > article > div > table:nth-child(14)|4
#https://www.betmarket.gr/prognostika-imeras/to-dynato-simeio-tis-imeras/|static|#main > div > div > div:nth-child(1) > div > div.single-match-tip-container > div.single-match-tip-match-container.single-match-tip--football|5


--- docker/entrypoint.sh ---
#!/usr/bin/env bash
set -euo pipefail

cd /app

case "${1:-scraper}" in
  scraper)
    exec /app/docker/run-scraper.sh
    ;;
  status)
    exec python status_web.py "${STATUS_PORT:-8001}"
    ;;
  homepage)
    exec python home_page.py "${HOMEPAGE_PORT:-6969}"
    ;;
  once)
    exec python main.py
    ;;
  *)
    exec "$@"
    ;;
esac


--- docker/run-scraper.sh ---
#!/usr/bin/env bash
set -euo pipefail

cd /app
mkdir -p logs

INTERVAL="${SCRAPE_INTERVAL_SECONDS:-3600}"

echo "Scraper loop started (interval=${INTERVAL}s)" | tee -a logs/scraper.log

while true; do
  echo "===== $(date -Is) run start =====" | tee -a logs/scraper.log
  python main.py 2>&1 | tee -a logs/scraper.log
  echo "===== $(date -Is) run end, sleeping ${INTERVAL}s =====" | tee -a logs/scraper.log
  sleep "${INTERVAL}"
done


--- main.py ---
import json
import os
import re
import time
import difflib
from datetime import datetime
from playwright.sync_api import sync_playwright

from notify import send_message

#print("Script started", flush=True)
#print("Script Started")
# Clears the log file if it's a new day
def clear_log_daily(log_file):
    if os.path.exists(log_file):
        last_modified = datetime.fromtimestamp(os.path.getmtime(log_file))
        today = datetime.today().date()
        if last_modified.date() != today:
            with open(log_file, "w") as f:
                json.dump({}, f)

# Load or initialize the last sent log (persistent)
def load_last_sent(file_name):
    if os.path.exists(file_name):
        with open(file_name, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_last_sent(file_name, data):
    tmp_file = f"{file_name}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, file_name)


def save_scrape_state(log_file, last_sent_file, sent_log, last_sent):
    tmp_log_file = f"{log_file}.tmp"
    with open(tmp_log_file, "w", encoding="utf-8") as f:
        json.dump(sent_log, f, ensure_ascii=False, indent=2)
    os.replace(tmp_log_file, log_file)
    save_last_sent(last_sent_file, last_sent)


FAILURE_STATE_FILE = "url_failures.json"
FAILURE_THRESHOLD = 2
FAILURE_COOLDOWN_SECONDS = 6 * 3600


def load_failure_state(file_name):
    if os.path.exists(file_name):
        try:
            with open(file_name, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except Exception:
            return {}
    return {}


def save_failure_state(file_name, data):
    tmp_file = f"{file_name}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, file_name)


def get_failure_entry(failure_state, unique_key):
    entry = failure_state.get(unique_key, {})
    if not isinstance(entry, dict):
        entry = {}
    return entry


def is_in_failure_cooldown(failure_state, unique_key):
    entry = get_failure_entry(failure_state, unique_key)
    cooldown_until = float(entry.get("cooldown_until", 0) or 0)
    now = time.time()
    if cooldown_until and now < cooldown_until:
        return True, int(cooldown_until - now)
    return False, 0


def record_failure(failure_state, unique_key, message):
    entry = get_failure_entry(failure_state, unique_key)
    entry["count"] = int(entry.get("count", 0) or 0) + 1
    entry["last_error"] = message
    entry["last_failure_ts"] = time.time()
    if entry["count"] >= FAILURE_THRESHOLD:
        entry["cooldown_until"] = time.time() + FAILURE_COOLDOWN_SECONDS
        entry["count"] = 0
    failure_state[unique_key] = entry


def clear_failure(failure_state, unique_key):
    if unique_key in failure_state:
        del failure_state[unique_key]

def is_mostly_same(a, b, threshold=0.9):
    """Return True if a and b are mostly the same (similarity > threshold)."""
    return difflib.SequenceMatcher(None, a, b).ratio() > threshold

def get_compare_text(text, lines_to_trim):
    """Normalize and trim text to the part we actually send (top N lines, strip blanks)."""
    trimmed = "\n".join(text.splitlines()[:lines_to_trim])
    normalized = "\n".join([line.strip() for line in trimmed.splitlines() if line.strip()])
    return normalized

def format_content(url, contents):
    """Format scraped content based on site-specific requirements"""
    if not contents:
        return ""

    # bet-on-arme: join with spaces (single line)
    if 'bet-on-arme.com' in url:
        return " ".join(contents)

    # bethome: join with spaces but remove last item (stake amount)
    elif 'bethome.gr' in url:
        text_parts = " ".join(contents).split()
        return " ".join(text_parts[:-1]) if text_parts else ""

    # Default: join with newlines
    else:
        return "\n".join(contents)


KINGBET_DATE_LABEL_RE = re.compile(r"^(\d{1,2})\.(\d{2})\.(\d{2})$")


def parse_kingbet_date_label(text):
    label = (text or "").strip()
    match = KINGBET_DATE_LABEL_RE.match(label)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
    year += 2000 if year < 100 else 0
    try:
        return datetime(year, month, day).date()
    except ValueError:
        return None


def select_kingbet_today_tab(page, url):
    """Open kingbet page and select today's date tab if it exists."""
    try:
        page.goto(url, timeout=60000, wait_until="domcontentloaded")
        page.wait_for_load_state("domcontentloaded")
    except Exception as exc:
        print(f"Kingbet page load failed for {url}: {exc}", flush=True)
        return False, True

    def js_click(locator):
        locator.evaluate(
            """
            el => el.dispatchEvent(new MouseEvent('click', {
                bubbles: true,
                cancelable: true,
                view: window,
            }))
            """
        )

    def wait_for_kingbet_selection(slide_selector, before_text):
        try:
            page.wait_for_function(
                """
                selector => {
                    const slide = document.querySelector(selector);
                    return Boolean(slide && slide.classList.contains('current'));
                }
                """,
                arg=slide_selector,
                timeout=10000,
            )
            page.wait_for_function(
                """
                before => {
                    const listing = document.querySelector('.betting-features__listing');
                    return Boolean(listing && listing.innerText.trim() && listing.innerText.trim() !== before);
                }
                """,
                arg=before_text,
                timeout=10000,
            )
            return True, False
        except Exception as exc:
            print(f"Kingbet tab selection timed out on {url}: {exc}", flush=True)
            return False, True

    today = datetime.today().date()
    today_iso = today.isoformat()
    labels_to_try = {
        today.strftime("%d.%m.%y"),
        f"{today.day}.{today.month:02d}.{today.strftime('%y')}",
        f"{today.day}.{today.month}.{today.strftime('%y')}",
    }

    iso_slide = page.locator(f".betting-features__calendar__slide[data-date='{today_iso}']")
    if iso_slide.count() > 0:
        before_text = page.locator('.betting-features__listing').inner_text().strip()
        js_click(iso_slide.first)
        selected, retryable_failure = wait_for_kingbet_selection(f".betting-features__calendar__slide[data-date='{today_iso}']", before_text)
        if not selected:
            return False, retryable_failure
        page.wait_for_timeout(500)
        print(f"Selected kingbet date tab: {today_iso} on {url}", flush=True)
        return True, False

    for label in labels_to_try:
        button = page.locator("button", has_text=label)
        if button.count() > 0:
            before_text = page.locator('.betting-features__listing').inner_text().strip()
            js_click(button.first)
            selected, retryable_failure = wait_for_kingbet_selection(".betting-features__calendar__slide.current", before_text)
            if not selected:
                return False, retryable_failure
            page.wait_for_timeout(500)
            print(f"Selected kingbet date tab: {label} on {url}", flush=True)
            return True, False

    for candidate in ("button", "a", "[role='tab']"):
        for element in page.locator(candidate).all():
            label = element.inner_text().strip()
            if parse_kingbet_date_label(label) == today:
                before_text = page.locator('.betting-features__listing').inner_text().strip()
                js_click(element)
                selected, retryable_failure = wait_for_kingbet_selection(".betting-features__calendar__slide.current", before_text)
                if not selected:
                    return False, retryable_failure
                page.wait_for_timeout(500)
                print(f"Selected kingbet date tab: {label} on {url}", flush=True)
                return True, False

    # Fallback: some Kingbet pages render the date tabs as div/span slides
    # (e.g. .betting-features__calendar__slide / .betting-features__calendar__date).
    for slide in page.locator(".betting-features__calendar__slide").all():
        label = slide.inner_text().strip()
        if parse_kingbet_date_label(label) == today:
            before_text = page.locator('.betting-features__listing').inner_text().strip()
            try:
                js_click(slide)
            except Exception:
                # try clicking the inner date element if slide itself isn't clickable
                date_elem = slide.locator(".betting-features__calendar__date")
                if date_elem.count() > 0:
                    js_click(date_elem.first)
            selected, retryable_failure = wait_for_kingbet_selection(f".betting-features__calendar__slide[data-date='{today_iso}']", before_text)
            if not selected:
                return False, retryable_failure
            page.wait_for_timeout(500)
            print(f"Selected kingbet date tab: {label} on {url}", flush=True)
            return True, False

    print(
        f"No kingbet date tab for today ({today.strftime('%d.%m.%y')}) on {url} — "
        "skipping to avoid stale tips",
        flush=True,
    )
    return False, False


def normalize_matchbot_tip(tip_text, max_lines=6):
    lines = [line.strip() for line in tip_text.splitlines() if line.strip()]
    if len(lines) >= max_lines:
        lines = lines[:max_lines]
    return "\n".join(lines)


def write_matchbot_json(tip_text, file_name, max_lines=6):
    if not tip_text or not tip_text.strip():
        return

    normalized_tip = normalize_matchbot_tip(tip_text, max_lines)
    if not normalized_tip:
        return

    matchbot_root = os.environ.get("MATCHBOT_OUTPUT_DIR", "/home/gk/matchbot")
    output_path = os.path.join(matchbot_root, "autobet", "tips", file_name)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({
            "date": datetime.today().strftime("%Y-%m-%d"),
            "tip": normalized_tip
        }, f, ensure_ascii=False, indent=2)


def write_sendragoal_json(tip_text):
    """Write the latest SendraGoal tip to /home/gk/matchbot/sendragoal.json."""
    write_matchbot_json(tip_text, "sendragoal.json")

# def extract_percentage(text):
#     """Extract percentage from text like '(72%)'"""
#     match = re.search(r'\((\d+)%\)', text)
#     return int(match.group(1)) if match else 0

# def scrape_betclever(page, url, last_sent, sent_log, unique_key, selector):
#     """Special handler for betclever - scrapes all tips, sorts by %, sends only >75%"""
#     print(f"\n[BETCLEVER] Betclever special handler activated for: {url} (selector: {selector})", flush=True)
#
#     try:
#         page.goto(url, timeout=60000)
#         page.wait_for_selector(selector, timeout=30000)
#
#         # Get the specific container first, then items within it
#         container = page.query_selector(selector)
#         if not container:
#             print("[BETCLEVER] Container not found", flush=True)
#             return
#
#         items = container.query_selector_all('.singles__item')
#         print(f"[BETCLEVER] Found {len(items)} tips in betclever container", flush=True)
#
#         tips = []
#         for item in items:
#             try:
#                 # Extract team names
#                 names = item.query_selector_all('.singles__item-left-name')
#                 team1 = names[0].inner_text().strip() if len(names) > 0 else "?"
#                 team2 = names[1].inner_text().strip() if len(names) > 1 else "?"
#
#                 # Extract time and league
#                 time_elem = item.query_selector('.singles__item-right-time')
#                 time_text = time_elem.inner_text().strip() if time_elem else "?"
#
#                 league_elem = item.query_selector('.singles__item-right-liga')
#                 league = league_elem.inner_text().strip() if league_elem else "?"
#
#                 # Extract tip and percentage
#                 tip_elem = item.query_selector('.singles__item-right-winner b')
#                 tip_text = tip_elem.inner_text().strip() if tip_elem else "?"
#
#                 # Extract odds
#                 odds_elem = item.query_selector('.singles__item-right-odd button')
#                 odds = odds_elem.inner_text().strip() if odds_elem else "?"
#
#                 # Get percentage
#                 percentage = extract_percentage(tip_text)
#
#                 tips.append({
#                     'team1': team1,
#                     'team2': team2,
#                     'time': time_text,
#                     'league': league,
#                     'tip': tip_text,
#                     'odds': odds,
#                     'percentage': percentage
#                 })
#             except Exception as e:
#                 print(f"Error parsing betclever item: {e}")
#
#         # Sort by percentage (highest first)
#         tips.sort(key=lambda x: x['percentage'], reverse=True)
#
#         # Filter for >75%
#         high_confidence = [t for t in tips if t['percentage'] > 75]
#
#         print(f"High confidence tips (>75%): {len(high_confidence)}")
#
#         if high_confidence:
#             # Format all tips into a single message
#             message_parts = [f"🎯 BETCLEVER HIGH CONFIDENCE TIPS ({len(high_confidence)} tips >75%)\n"]
#
#             for tip in high_confidence:
#                 tip_msg = (
#                     f"⚽ {tip['team1']} vs {tip['team2']}\n"
#                     f"⏰ {tip['time']} | {tip['league']}\n"
#                     f"💡 {tip['tip']}\n"
#                     f"📊 Odds: {tip['odds']}\n"
#                 )
#                 message_parts.append(tip_msg)
#
#             combined_message = "\n".join(message_parts)
#
#             # Check if we already sent this exact set of tips (use unique_key for deduplication)
#             last_content = last_sent.get(unique_key, "")
#
#             if not is_mostly_same(combined_message, last_content):
#                 print("✅ Sending betclever high confidence tips:")
#                 print(combined_message)
#                 send_message(combined_message, url=url, lines_to_trim=100)
#                 last_sent[unique_key] = combined_message
#                 sent_log[unique_key] = combined_message
#             else:
#                 print("ℹ️ Betclever tips already sent (content is mostly the same).")
#         else:
#             print("❌ No betclever tips above 75% confidence found.")
#
#     except Exception as e:
#         print(f"Error scraping betclever: {e}")


def check_sites():
    today_url = datetime.today().strftime("%d-%m-%y")
    today_display_ddmm = datetime.today().strftime("%d/%m")
    today_display_ddmmyy = datetime.today().strftime("%d/%m/%y")
    today_display_mmdd = datetime.today().strftime("%m/%d")

    date_formats = {
        "dd/mm": today_display_ddmm,
        "dd/mm/yy": today_display_ddmmyy,
        "mm/dd": today_display_mmdd
    }

    log_file = "sent_log.json"
    last_sent_file = "last_sent.json"
    clear_log_daily(log_file)

    # Load logs
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            sent_log = json.load(f)
    else:
        sent_log = {}

    last_sent = load_last_sent(last_sent_file)
    failure_state = load_failure_state(FAILURE_STATE_FILE)

    sites = []
    with open("urls.txt", "r") as f:
        lines = f.read().splitlines()
        for line_num, line in enumerate(lines):
            if line.startswith("#") or not line.strip():  # Skip commented or empty lines
                continue
            parts = line.split("|")
            if len(parts) >= 3:
                url = parts[0].strip()
                url_type = parts[1].strip().lower()
                selector = parts[2].strip()
                date_format = parts[3].strip().lower() if len(parts) > 3 else ""
                lines_to_trim = (
                    int(parts[4].strip()) if len(parts) > 4 and parts[4].strip().isdigit()
                    else int(parts[3].strip()) if len(parts) > 3 and parts[3].strip().isdigit()
                    else 1
                )
                # Create unique key combining URL and selector to handle duplicate URLs with different configs
                unique_key = f"{url}|{selector}"
                sites.append((url, url_type, selector, date_format, lines_to_trim, unique_key))

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        for url, url_type, selector, date_format, lines_to_trim, unique_key in sites:
            is_kingbet = "kingbet.com.cy" in url
            is_cooldown, seconds_left = is_in_failure_cooldown(failure_state, unique_key)
            if is_cooldown:
                full_url_preview = f"{url}{today_url}/" if url_type == "date" else url
                print(f"Skipping {full_url_preview} for {seconds_left}s due to recent failures.", flush=True)
                continue

            if is_kingbet:
                try:
                    selected, retryable_failure = select_kingbet_today_tab(page, url)
                    if not selected:
                        if retryable_failure:
                            record_failure(failure_state, unique_key, "Kingbet selection failed")
                            save_failure_state(FAILURE_STATE_FILE, failure_state)
                        continue
                except Exception as exc:
                    print(f"Error selecting Kingbet date tab for {url}: {exc}", flush=True)
                    record_failure(failure_state, unique_key, str(exc))
                    save_failure_state(FAILURE_STATE_FILE, failure_state)
                    continue

            full_url = f"{url}{today_url}/" if url_type == "date" else url
            print(f"\nChecking: {full_url}", flush=True)

            # # Special handling for betclever only when using the main tips container
            # if 'betclever.com' in full_url and 'singles__wrap' in selector:
            #     scrape_betclever(page, full_url, last_sent, sent_log, unique_key, selector)
            #     continue

            try:
                if not is_kingbet:
                    page.goto(full_url, timeout=60000)
                selectors = [s.strip() for s in selector.split(",")]
                contents = []
                for sel in selectors:
                    try:
                        wait_state = "attached" if is_kingbet else "visible"
                        page.wait_for_selector(sel, state=wait_state, timeout=30000)
                        element = page.query_selector(sel)
                        if element:
                            if sel.endswith("table"):
                                rows = element.query_selector_all("tr")
                                if rows:
                                    contents.append(rows[-1].inner_text().strip())
                            else:
                                contents.append(element.inner_text().strip())
                        else:
                                print("No element found with selector:", sel, flush=True)
                    except Exception as e:
                                print(f"Selector error for {sel}: {e}", flush=True)

                # Filter out empty strings from contents
                contents = [c for c in contents if c.strip()]

                # Format content based on site requirements
                combined_content = format_content(full_url, contents)
                print("🔍 Raw content:", combined_content, flush=True)

                # Use only the trimmed, normalized message for dedupe
                if 'bet-on-arme.com' in full_url:
                    # For bet-on-arme, don't add newlines back - keep as single line
                    compare_text = combined_content
                else:
                    compare_text = get_compare_text(combined_content, lines_to_trim)

                if any(domain in full_url.lower() for domain in ['sendragoal', 'sentragoal']):
                    write_sendragoal_json(compare_text)
                if 'kingbet.com.cy/to-dynato-simeio-imeras' in full_url.lower():
                    write_matchbot_json(compare_text, 'kingbet_to_dynato.json')
                if 'kingbet.com.cy/favori-imeras' in full_url.lower():
                    write_matchbot_json(compare_text, 'kingbet_to_favori.json')

                should_send = False
                # Backward-compatible: older runs stored full content; trim it before comparing
                last_content_raw = last_sent.get(unique_key, "")
                last_content = get_compare_text(last_content_raw, lines_to_trim) if last_content_raw else ""

                if date_format:
                    expected_date = date_formats.get(date_format, "")
                    if expected_date in combined_content:
                        # Only send if content is significantly different (based on trimmed text)
                        should_send = not last_content or not is_mostly_same(compare_text, last_content)
                        if should_send:
                            print("✅ Tip found for today:", flush=True)
                            print(compare_text, flush=True)
                        else:
                            print("ℹ️ Tip already sent (content is mostly the same).", flush=True)
                    else:
                        print("❌ No Tip Today", flush=True)
                else:
                    # Only send if content is significantly different (based on trimmed text)
                    should_send = not last_content or not is_mostly_same(compare_text, last_content)
                    if should_send:
                        print("✅ Content found:", flush=True)
                        print(compare_text, flush=True)
                    else:
                        print("ℹ️ Content already sent (content is mostly the same).", flush=True)

                if should_send:
                    # Send full combined content (notify trims again for chat), but store trimmed for dedupe
                    sent_ok = send_message(combined_content, url=full_url, lines_to_trim=lines_to_trim)
                    if sent_ok:
                        last_sent[unique_key] = compare_text
                        sent_log[unique_key] = compare_text
                        save_scrape_state(log_file, last_sent_file, sent_log, last_sent)
                    else:
                        print(f"Telegram send failed for {full_url}; not updating dedupe state.", flush=True)

            except Exception as e:
                print(f"Error accessing {full_url}: {e}", flush=True)
                record_failure(failure_state, unique_key, str(e))
                save_failure_state(FAILURE_STATE_FILE, failure_state)
            else:
                clear_failure(failure_state, unique_key)
                save_failure_state(FAILURE_STATE_FILE, failure_state)

        browser.close()

    save_scrape_state(log_file, last_sent_file, sent_log, last_sent)

def main():
    # Entry point for the script
    print("Starting bot...", flush=True)
    check_sites()

if __name__ == "__main__":
    main()



--- notify.py ---
import os
from urllib.parse import urlparse
import requests
# from openpyxl import Workbook, load_workbook

# Reads Telegram bot token and chat ID from a file
def read_telegram_info(tginfo_path='tginfo.txt'):
    """Read Telegram bot token and chat ID from a text file."""
    with open(tginfo_path, 'r') as f:
        lines = f.read().splitlines()
        token = lines[0].strip()
        chat_id = lines[1].strip()
    return token, chat_id

# Extracts the site name from a given URL for labeling messages
def extract_site_name(url):
    """Extract the site name from a URL for labeling."""
    # Custom handling for specific foxbet URLs
    if 'foxbet.gr/316026/to-dunato-simeio' in url:
        return 'foxbet-to_dynato'
    elif 'foxbet.gr/316014/to-stantar' in url:
        return 'foxbet-to_stantar'
    # Custom handling for nostrabet URLs
    elif 'nostrabet.com/en/bet-of-the-day' in url:
        return 'nostra_bet_of_the_day'
    elif 'nostrabet.com/en/banker-of-the-day' in url:
        return 'notra_banker_of_the_day'
    # Custom handling for kingbet URLs
    elif 'kingbet.com.cy/to-dynato-simeio-imeras' in url:
        return 'kingbet-to_dynato'
    elif 'kingbet.com.cy/favori-imeras' in url:
        return 'kingbet-to_favori'
    elif 'kingbet.com.cy/to-stantar-tis-imeras' in url:
        return 'kingbet-to_stantar'

    # Default behavior for other URLs
    netloc = urlparse(url).netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    site_name = netloc.split('.')[0]
    return site_name if site_name else 'unknown'

# # Returns the monthly log file name for tips
# def get_monthly_log_file(base_name="tips_log"):
#     """Generate the monthly log file name for tips."""
#     month_str = datetime.today().strftime("%Y_%m")
#     return f"{base_name}_{month_str}.xlsx"
#
# # Logs a tip to the monthly Excel file, adding headers if new
# def log_tip_to_xlsx(xlsx_file, url, tip):
#     """Log a tip to the monthly Excel file, adding headers if the file is new."""
#     now = datetime.now()
#     date_str = now.strftime("%d/%m/%Y")
#     time_str = now.strftime("%H:%M")
#     tipster = extract_site_name(url)
#     if not os.path.exists(xlsx_file):
#         wb = Workbook()
#         ws = wb.active
#         ws.append(["Date", "Time", "Tipster", "Tip"])
#         wb.save(xlsx_file)
#     wb = load_workbook(xlsx_file)
#     ws = wb.active
#     ws.append([date_str, time_str, tipster, tip])
#     wb.save(xlsx_file)

# Normalize message text for Telegram: trim each line and drop empty lines.
def normalize_message_text(message, lines_to_trim):
    cleaned_lines = [line.strip() for line in message.splitlines() if line.strip()]
    return "\n".join(cleaned_lines[:lines_to_trim])

def default_tginfo_path():
    return os.environ.get("TGINFO_PATH", "tginfo.txt")


# Sends a message to a Telegram chat using the bot API
def send_message(message, url=None, tginfo_path=None, lines_to_trim=10):
    if tginfo_path is None:
        tginfo_path = default_tginfo_path()
    """Send a message to Telegram."""
    trimmed_message = normalize_message_text(message, lines_to_trim)
    # Only send if the tip content is not empty (excluding site name)
    if not trimmed_message.strip():
        print("⚠️ Empty message, not sending to Telegram.")
        return False
    token, chat_id = read_telegram_info(tginfo_path)
    if url:
        site_name = extract_site_name(url)
        # If the trimmed_message is empty after stripping, do not send even with site name
        if not trimmed_message.strip():
            print(f"⚠️ Empty tip for [{site_name}], not sending to Telegram.")
            return False
        trimmed_message = f"[{site_name}] {trimmed_message}"
    url_api = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': trimmed_message}
    response = requests.post(url_api, data=payload)
    print("Telegram response:", response.text)
    # if url:
    #     log_tip_to_xlsx(get_monthly_log_file(), url, trimmed_message)
    return response.ok

def main():
    # Entry point for notification handling
    pass

if __name__ == "__main__":
    main()

--- status_web.py ---
import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

SERVICE_NAME = "myweb_scraper"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_LOG_FILE = os.path.join(BASE_DIR, "sent_log.json")
RUNTIME = os.environ.get("RUNTIME", "auto").lower()
DOCKER_SCRAPER_CONTAINER = os.environ.get("DOCKER_SCRAPER_CONTAINER", "myweb_scraper")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SCRAPER_LOG_FILE = os.path.join(LOG_DIR, "scraper.log")


def use_docker_runtime():
    if RUNTIME == "docker":
        return True
    if RUNTIME == "systemd":
        return False
    return bool(DOCKER_SCRAPER_CONTAINER) and os.path.exists("/var/run/docker.sock")


def get_docker_client():
    try:
        import docker
        return docker.from_env()
    except Exception:
        return None


def get_docker_scraper_container():
    client = get_docker_client()
    if client is None:
        return None
    try:
        return client.containers.get(DOCKER_SCRAPER_CONTAINER)
    except Exception:
        return None


def get_docker_bot_process_info():
    container = get_docker_scraper_container()
    if container is None:
        return 0, "unknown", None
    if container.status != "running":
        return 0, "stopped", None

    started_raw = container.attrs.get("State", {}).get("StartedAt")
    if not started_raw:
        return 1, "unknown", None

    try:
        started = datetime.fromisoformat(started_raw.replace("Z", "+00:00"))
        elapsed = max(0, int((datetime.now(started.tzinfo) - started).total_seconds()))
    except ValueError:
        return 1, "unknown", None

    bot_uptime = format_duration(elapsed)
    bot_since = started.astimezone().strftime("%d/%m/%Y %H:%M:%S")
    return 1, bot_uptime, bot_since


def get_docker_service_status():
    instances, bot_uptime, bot_since = get_docker_bot_process_info()
    container = get_docker_scraper_container()
    if container is None:
        return {
            "available": True,
            "message": f"Container '{DOCKER_SCRAPER_CONTAINER}' not found",
            "active": False,
            "sub": "missing",
            "loaded": "docker",
            "bot_uptime": bot_uptime,
            "bot_since": bot_since,
            "status_output": f"docker container {DOCKER_SCRAPER_CONTAINER} not found",
            "instances": instances,
        }

    active = container.status == "running"
    return {
        "available": True,
        "message": "",
        "active": active,
        "sub": container.status,
        "loaded": "docker",
        "bot_uptime": bot_uptime,
        "bot_since": bot_since,
        "status_output": f"container={DOCKER_SCRAPER_CONTAINER}\nstatus={container.status}",
        "instances": instances,
        "service_since": container.attrs.get("State", {}).get("StartedAt"),
    }


def perform_docker_action(action):
    if action not in {"start", "stop", "restart"}:
        return False, f"Invalid action: {action}"

    container = get_docker_scraper_container()
    if container is None:
        return False, f"Container '{DOCKER_SCRAPER_CONTAINER}' not found"

    try:
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop()
        else:
            container.restart()
    except Exception as exc:
        return False, str(exc)

    return True, f"{action} sent to container {DOCKER_SCRAPER_CONTAINER}"


def read_docker_scraper_logs(tail=200):
    container = get_docker_scraper_container()
    if container is None:
        return ""
    try:
        raw = container.logs(tail=tail)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_site_name(url):
    if 'foxbet.gr/316026/to-dunato-simeio' in url:
        return 'foxbet-to_dynato'
    elif 'foxbet.gr/316014/to-stantar' in url:
        return 'foxbet-to_stantar'
    elif 'nostrabet.com/en/bet-of-the-day' in url:
        return 'nostra_bet_of_the_day'
    elif 'nostrabet.com/en/banker-of-the-day' in url:
        return 'notra_banker_of_the_day'
    elif 'kingbet.com.cy/to-dynato-simeio-imeras' in url:
        return 'kingbet-to_dynato'
    elif 'kingbet.com.cy/favori-imeras' in url:
        return 'kingbet-to_favori'
    elif 'kingbet.com.cy/to-stantar-tis-imeras' in url:
        return 'kingbet-to_stantar'

    parsed = urlparse(url)
    netloc = parsed.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    site_name = netloc.split('.')[0]
    return site_name if site_name else 'unknown'


def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {command[0]}"


def get_service_status():
    if use_docker_runtime():
        return get_docker_service_status()

    instances, bot_uptime, bot_since = get_bot_process_info()
    if shutil_which("systemctl") is None:
        return {
            "available": False,
            "message": "systemctl not found",
            "active": instances > 0,
            "sub": instances > 0 and "running" or "stopped",
            "loaded": "process-only",
            "bot_uptime": bot_uptime,
            "bot_since": bot_since,
            "status_output": "Systemctl unavailable. Using process information instead.",
            "instances": instances,
        }

    code, stdout, stderr = run_command(["systemctl", "show", SERVICE_NAME, "--no-page", "-p", "ActiveState", "-p", "SubState", "-p", "LoadState", "-p", "ActiveEnterTimestamp", "-p", "ExecMainPID"])
    if code != 0:
        return {
            "available": True,
            "message": f"systemctl show failed ({code})",
            "active": False,
            "sub": "unknown",
            "loaded": "unknown",
            "bot_uptime": bot_uptime,
            "bot_since": bot_since,
            "status_output": stderr or stdout or "Systemctl service not found. Using process information instead.",
            "instances": instances,
        }

    status = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in stdout.splitlines() if "=" in line}
    active = status.get("ActiveState", "unknown") == "active"
    service_since = status.get("ActiveEnterTimestamp")

    return {
        "available": True,
        "message": "",
        "active": active,
        "sub": status.get("SubState", "unknown"),
        "loaded": status.get("LoadState", "unknown"),
        "bot_uptime": bot_uptime,
        "bot_since": bot_since,
        "status_output": stdout,
        "instances": instances,
        "service_since": service_since,
    }


def format_site_alias(name):
    if not name:
        return name
    pretty = name.replace("_", " ").replace("-", " ")
    pretty = " ".join(pretty.split())
    return pretty


def get_sent_tips():
    if not os.path.exists(SENT_LOG_FILE):
        return {}

    try:
        with open(SENT_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    tips_by_site = {}

    for key, tip_text in data.items():
        url = key.split("|", 1)[0]
        site = format_site_alias(extract_site_name(url))
        tips_by_site.setdefault(site, []).append({
            "tip": tip_text,
        })

    return tips_by_site


def format_duration(seconds):
    if seconds is None or seconds == "unknown":
        return "unknown"
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_bot_process_info():
    code, stdout, stderr = run_command(["ps", "-eo", "etimes,cmd"])
    if code != 0 or not stdout:
        return 0, "unknown", None

    processes = []
    for line in stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        etimes, cmd = parts
        if "main.py" in cmd and "status_web.py" not in cmd:
            try:
                elapsed = int(etimes)
            except ValueError:
                continue
            processes.append((elapsed, cmd))

    if not processes:
        return 0, "unknown", None

    instances = len(processes)
    longest = max(processes, key=lambda item: item[0])
    bot_uptime = format_duration(longest[0])
    bot_since = (datetime.now() - timedelta(seconds=longest[0])).strftime("%d/%m/%Y %H:%M:%S")
    return instances, bot_uptime, bot_since


def shutdown_server():
    raise KeyboardInterrupt


def perform_action(action):
    if action == "restart_console":
        return True, "Console reload handled by UI"

    if use_docker_runtime():
        return perform_docker_action(action)

    if shutil_which("systemctl") is None:
        return False, "systemctl not available on this machine"

    if action not in {"start", "stop", "restart"}:
        return False, f"Invalid action: {action}"

    code, stdout, stderr = run_command(["sudo", "systemctl", action, SERVICE_NAME, "--no-pager"])
    success = code == 0
    result_text = stdout if stdout else stderr
    if not result_text:
        result_text = f"command exited with code {code}"
    return success, result_text


def shutil_which(name):
    from shutil import which
    return which(name)


class StatusHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="text/html", extra_headers=None):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._serve_index()
        if parsed.path == "/api/status":
            return self._serve_status()
        if parsed.path == "/api/today":
            return self._serve_today()
        if parsed.path == "/logs":
            return self._serve_logs()
        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/action":
            length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(length).decode("utf-8")
            params = parse_qs(post_data)
            action = params.get("action", [""])[0]
            success, output = perform_action(action)
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"success": success, "action": action, "output": output}).encode("utf-8"))
            return
        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def _serve_status(self):
        status = get_service_status()
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(status).encode("utf-8"))

    def _serve_today(self):
        data = get_sent_tips()
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps({"tips_by_site": data}).encode("utf-8"))

    def _serve_logs(self):
        if os.path.exists(SCRAPER_LOG_FILE):
            with open(SCRAPER_LOG_FILE, "rb") as f:
                raw = f.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            if content.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
                return

        if use_docker_runtime():
            docker_logs = read_docker_scraper_logs()
            if docker_logs.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(docker_logs.encode("utf-8"))
                return

        log_path = os.path.join(BASE_DIR, "output.log")
        backup_path = os.path.join(BASE_DIR, "nohup.out")
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                raw = f.read()
            content = None
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            if content.strip() and content.strip() != "nohup: ignoring input":
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
                return
        if os.path.exists(backup_path):
            with open(backup_path, "rb") as f:
                raw = f.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            if content.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
                return
        if shutil_which("journalctl"):
            code, stdout, stderr = run_command(["journalctl", "-u", SERVICE_NAME, "--no-pager", "-n", "200"])
            if code == 0 and stdout.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(stdout.encode("utf-8"))
                return
        self._set_headers(404, "text/plain; charset=utf-8")
        self.wfile.write(b"No usable log output found. Check output.log, nohup.out, or journalctl.")

    def _serve_index(self):
        self._set_headers(200, "text/html", {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })
        self.wfile.write(INDEX_HTML.encode("utf-8"))

    def log_message(self, format, *args):
        return


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Bot Status</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background:#f7f8fb; color:#222; }
    h1 { margin-bottom: 8px; }
    .card { background: #fff; border: 1px solid #d9dee7; border-radius: 10px; padding: 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
    button { margin-right: 10px; padding: 10px 14px; border:none; border-radius: 6px; cursor:pointer; font-weight: 600; }
    .btn-start { background:#2f9d27; color:#fff; }
    .btn-stop { background:#d6392e; color:#fff; }
    .btn-restart { background:#1677ff; color:#fff; }
    .status { font-size: 1rem; margin-top: 10px; }
    .site { margin-bottom: 14px; }
    pre { background:#0f172a; color:#d6e4ff; padding:12px; border-radius:8px; overflow:auto; }
  </style>
</head>
<body>
  <h1>Bot Status Dashboard</h1>
  <div class="card">
    <div><strong>Service:</strong> <span id="service-name">myweb_scraper</span></div>
    <div class="status"><strong>Active:</strong> <span id="active-state">loading...</span></div>
    <div class="status"><strong>Sub-state:</strong> <span id="sub-state">loading...</span></div>
    <div class="status"><strong>Loaded:</strong> <span id="loaded-state">loading...</span></div>
    <div class="status"><strong>Bot uptime:</strong> <span id="uptime">loading...</span></div>
    <div class="status"><strong>Started at:</strong> <span id="since">loading...</span></div>
    <div class="status"><strong>Systemctl available:</strong> <span id="systemctl-available">loading...</span></div>
    <div class="status"><strong>Instances:</strong> <span id="instances">loading...</span></div>
    <div style="margin-top:16px;">
      <button class="btn-start" onclick="sendAction('start')">Start</button>
      <button class="btn-stop" onclick="sendAction('stop')">Stop</button>
      <button class="btn-restart" onclick="sendAction('restart')">Restart</button>
      <button class="btn-restart" onclick="sendAction('restart_console')">Restart Console</button>
      <button class="btn-restart" onclick="openLogs()">Open Logs</button>
    </div>
    <div class="status">Controls the <strong>myweb_scraper</strong> service/process, not the status page itself.</div>
    <div class="status"><strong>Last action:</strong> <span id="action-result">none</span></div>
  </div>

  <div class="card">
    <h2>Today's Sent Tips</h2>
    <div><strong>Date:</strong> <span id="today-date">loading...</span></div>
    <table id="tips-table" style="width:100%; border-collapse: collapse; margin-top: 12px;">
      <thead>
        <tr>
          <th style="text-align:left; padding: 8px; border-bottom: 1px solid #d9dee7;">Tipster</th>
          <th style="text-align:left; padding: 8px; border-bottom: 1px solid #d9dee7;">Tip</th>
        </tr>
      </thead>
      <tbody id="tips-body"></tbody>
    </table>
    <div id="no-tips" style="margin-top:12px; color:#555;"></div>
  </div>

  <div class="card">
    <h2>Service Details</h2>
    <div class="status">Raw diagnostic output from the myweb_scraper service/process.</div>
    <pre id="raw-output">loading...</pre>
  </div>

  <script>
    async function fetchStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('active-state').textContent = data.active ? 'active' : 'inactive';
      document.getElementById('sub-state').textContent = data.sub || 'unknown';
      document.getElementById('loaded-state').textContent = data.loaded || 'unknown';
      document.getElementById('uptime').textContent = data.bot_uptime || 'unknown';
      document.getElementById('since').textContent = data.bot_since || 'unknown';
      document.getElementById('systemctl-available').textContent = data.available ? 'yes' : 'no';
      document.getElementById('raw-output').textContent = data.status_output || 'no output';
      document.getElementById('instances').textContent = data.instances || 0;
    }

    async function fetchTips() {
      const res = await fetch('/api/today');
      const data = await res.json();
      const body = document.getElementById('tips-body');
      const noTips = document.getElementById('no-tips');
      body.innerHTML = '';
      const tips = data.tips_by_site || {};
      const date = new Date();
      document.getElementById('today-date').textContent = `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
      const rows = [];
      for (const [site, items] of Object.entries(tips)) {
        items.forEach(item => {
          rows.push({ site: site.replace(/[_-]/g, ' ').replace(/\s+/g, ' ').trim(), tip: item.tip });
        });
      }
      if (!rows.length) {
        noTips.textContent = 'No tips have been stored for today yet.';
        return;
      }
      noTips.textContent = '';
      rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="padding: 8px; border-bottom: 1px solid #f0f2f7;">${row.site}</td>
          <td style="padding: 8px; border-bottom: 1px solid #f0f2f7;">${row.tip}</td>
        `;
        body.appendChild(tr);
      });
    }

    function openLogs() {
      window.open('/logs?ts=' + Date.now(), '_blank');
    }

    async function sendAction(action) {
      if (action === 'restart_console') {
        document.getElementById('action-result').textContent = 'Reloading console...';
        window.location.reload();
        return;
      }
      document.getElementById('action-result').textContent = 'waiting...';
      const res = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `action=${action}`
      });
      const data = await res.json();
      document.getElementById('action-result').textContent = `${data.success ? 'OK' : 'ERROR'}: ${data.output}`;
      await fetchStatus();
    }

    async function refreshAll() {
      await fetchStatus();
      await fetchTips();
    }

    refreshAll();
    setInterval(refreshAll, 5000);
  </script>
</body>
</html>
"""


def run(port=8000):
    server_address = ("0.0.0.0", port)
    try:
        httpd = ThreadingHTTPServer(server_address, StatusHandler)
    except OSError as exc:
        if exc.errno == 98:
            print(f"ERROR: port {port} is already in use. Start with a different port, e.g. python3 status_web.py 8001")
            return
        raise
    print(f"Serving bot status on http://0.0.0.0:{port}")
    httpd.should_restart = False
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server")
    finally:
        httpd.server_close()

    if getattr(httpd, "should_restart", False):
        print("Restarting status web console...")
        os.execv(sys.executable, [sys.executable, __file__, str(port)])


if __name__ == "__main__":
    port = 8001
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run(port)


--- home_page.py ---
import json
import os
import shutil
import subprocess
import sys
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
BOOKMARKS_FILE = os.path.join(BASE_DIR, 'bookmarks.json')

HOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>George's Server</title>
  <style>
    :root {
      --bg: #0f0f10;
      --panel: #1f1f22;
      --surface: #1f1f22;
      --text: #f3f2ee;
      --muted: #a8a29e;
      --accent: #dd4814;
      --accent-soft: rgba(221,72,20,0.18);
      --border: rgba(255,255,255,0.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: radial-gradient(circle at 20% 20%, rgba(221,72,20,0.16), transparent 32%), #0c0c0f; color: var(--text); font-family: Inter, system-ui, sans-serif; }
    .container { max-width: 1160px; margin: 0 auto; padding: 40px 30px; display: grid; gap: 28px; }
    .hero { padding: 48px 42px; border-radius: 34px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); display: grid; gap: 24px; justify-items: center; text-align: center; }
    .hero .logo { width: 92px; height: 92px; display: grid; place-items: center; border-radius: 26px; background: linear-gradient(135deg, #ff8c42, #dd4814); box-shadow: 0 24px 50px rgba(221,72,20,0.2); }
    .hero h1 { margin: 0; font-size: clamp(3.2rem, 5.6vw, 4.8rem); letter-spacing: -0.05em; line-height: 0.92; }
    .hero p { margin: 0; max-width: 760px; color: var(--muted); font-size: 1.05rem; }
    .panel-grid { display: grid; gap: 22px; grid-template-columns: 2fr 1fr; }
    .panel { border-radius: 28px; border: 1px solid var(--border); background: rgba(255,255,255,0.04); padding: 28px; }
    .panel h2 { margin-top: 0; font-size: 1.2rem; }
    .panel p { margin: 0; color: var(--muted); line-height: 1.75; }
    .button-row { display: grid; gap: 14px; margin-top: 20px; }
    .button { border: none; border-radius: 16px; padding: 14px 16px; font-weight: 700; cursor: pointer; background: var(--accent); color: #fff; transition: transform .16s ease; }
    .button:hover { transform: translateY(-2px); background: #b23a11; }
    .button.secondary { background: rgba(255,255,255,0.08); color: var(--text); }
    .bookmarks { display: grid; gap: 12px; margin-top: 18px; }
    .bookmark { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-radius: 18px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); color: var(--text); text-decoration: none; }
    .bookmark span { color: var(--muted); }
    .bookmark-buttons { display: flex; gap: 10px; }
    .bookmark-button { border: none; background: rgba(255,255,255,0.08); color: var(--text); padding: 8px 12px; border-radius: 12px; cursor: pointer; transition: transform .16s ease; }
    .bookmark-button:hover { transform: translateY(-1px); background: rgba(255,255,255,0.12); }
    .stats { display: grid; gap: 14px; margin-top: 18px; }
    .stat { padding: 18px; border-radius: 22px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); }
    .stat strong { display: block; font-size: 1.05rem; margin-bottom: 5px; }
    .stat small { color: var(--muted); }
    .status-line { margin-top: 12px; color: var(--muted); font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <div class="logo" aria-hidden="true">
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="#fff"><circle cx="50" cy="50" r="50" opacity="0.16"/><path d="M54.4 34.5a7.8 7.8 0 1 1-10.8 0 7.8 7.8 0 0 1 10.8 0Zm18.7 3.1a5.2 5.2 0 1 0-7.4 7.3 5.2 5.2 0 0 0 7.4-7.3ZM30 40.8a5.2 5.2 0 1 0 7.4 7.3 5.2 5.2 0 0 0-7.4-7.3Zm47.9 29.4a5.2 5.2 0 1 0-7.4 7.3 5.2 5.2 0 0 0 7.4-7.3Zm-34.1 9.5a5.2 5.2 0 1 0-7.4 7.3 5.2 5.2 0 0 0 7.4-7.3Z"/></svg>
      </div>
      <h1>George's Server</h1>
      <p>Refined server homepage concept with console bookmarks, a clear action panel, and lightweight live status cards.</p>
    </section>

    <div class="panel-grid">
      <section class="panel">
        <h2>Navigation</h2>
        <div class="bookmarks" id="bookmark-list">
          <div class="bookmark" style="justify-content: center; color: var(--muted);">No bookmarks added yet.</div>
        </div>
        <div class="button-row" style="margin-top: 18px;">
          <button class="button secondary" onclick="addBookmark()">Add Bookmark</button>
        </div>
      </section>

      <section class="panel">
        <h2>Controls</h2>
        <div class="button-row">
          <button class="button" onclick="rebootServer()">Reboot Server</button>
          <button class="button secondary" onclick="refreshPage()">Refresh Page</button>
          <button class="button" onclick="restartHomepage()">Restart Homepage</button>
        </div>
        <p class="small">Reboot sends a reboot command to the server. Restart homepage reloads the app process.</p>
        <div class="status-line" id="action-status">Ready</div>
      </section>
    </div>

    <section class="panel">
      <h2>Live stats</h2>
      <div class="stats">
        <div class="stat"><strong>Uptime</strong><small id="stat-uptime">Loading…</small></div>
        <div class="stat"><strong>Load average</strong><small id="stat-load">Loading…</small></div>
        <div class="stat"><strong>Memory</strong><small id="stat-memory">Loading…</small></div>
        <div class="stat"><strong>Disk</strong><small id="stat-disk">Loading…</small></div>
      </div>
      <div class="status-line" id="stats-status">Fetching stats…</div>
    </section>
  </div>
  <script>
    let bookmarks = [];

    function renderBookmarks() {
      const list = document.getElementById('bookmark-list');
      list.innerHTML = '';
      if (!bookmarks.length) {
        const placeholder = document.createElement('div');
        placeholder.className = 'bookmark';
        placeholder.style.justifyContent = 'center';
        placeholder.style.color = 'var(--muted)';
        placeholder.textContent = 'No bookmarks added yet.';
        list.appendChild(placeholder);
        return;
      }
      bookmarks.forEach((bookmark, index) => {
        const item = document.createElement('div');
        item.className = 'bookmark';
        const link = document.createElement('a');
        link.href = bookmark.url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.style.color = 'inherit';
        link.style.textDecoration = 'none';
        link.innerHTML = `<span>${bookmark.title}</span>`;
        const controls = document.createElement('div');
        controls.className = 'bookmark-buttons';
        const edit = document.createElement('button');
        edit.className = 'bookmark-button';
        edit.textContent = 'Edit';
        edit.onclick = () => editBookmark(index);
        const remove = document.createElement('button');
        remove.className = 'bookmark-button';
        remove.textContent = 'Remove';
        remove.onclick = () => removeBookmark(index);
        controls.appendChild(edit);
        controls.appendChild(remove);
        item.appendChild(link);
        item.appendChild(controls);
        list.appendChild(item);
      });
    }

    async function loadBookmarks() {
      try {
        const res = await fetch('/api/bookmarks');
        if (res.ok) {
          bookmarks = await res.json();
        } else {
          bookmarks = [];
        }
      } catch (err) {
        bookmarks = [];
      }
      renderBookmarks();
    }

    async function saveBookmarks() {
      try {
        await fetch('/api/bookmarks', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ bookmarks }),
        });
      } catch (err) {
        console.warn('Bookmark save failed', err);
      }
    }

    async function addBookmark() {
      const url = window.prompt('Bookmark URL', 'http://');
      if (!url || !url.trim()) return;
      const title = window.prompt('Bookmark title', 'New bookmark');
      if (!title || !title.trim()) return;
      bookmarks.push({ title: title.trim(), url: url.trim() });
      await saveBookmarks();
      renderBookmarks();
    }

    async function editBookmark(index) {
      const bookmark = bookmarks[index];
      const title = window.prompt('Bookmark title', bookmark.title);
      if (!title || !title.trim()) return;
      const url = window.prompt('Bookmark URL', bookmark.url);
      if (!url || !url.trim()) return;
      bookmarks[index] = { title: title.trim(), url: url.trim() };
      await saveBookmarks();
      renderBookmarks();
    }

    async function removeBookmark(index) {
      if (!confirm('Remove this bookmark?')) return;
      bookmarks.splice(index, 1);
      await saveBookmarks();
      renderBookmarks();
    }

    async function fetchStats() {
      const statusLine = document.getElementById('stats-status');
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-uptime').textContent = data.uptime;
        document.getElementById('stat-load').textContent = data.load;
        document.getElementById('stat-memory').textContent = data.memory;
        document.getElementById('stat-disk').textContent = data.disk;
        statusLine.textContent = 'Stats live';
      } catch (err) {
        statusLine.textContent = 'Failed to fetch stats';
      }
    }

    async function sendAction(action) {
      const status = document.getElementById('action-status');
      status.textContent = 'Sending ' + action + '...';
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: `action=${encodeURIComponent(action)}`
        });
        const data = await res.json();
        status.textContent = data.success ? `OK: ${data.message}` : `ERROR: ${data.message}`;
      } catch (err) {
        status.textContent = 'Action failed';
      }
    }

    function refreshPage() { location.reload(); }
    function rebootServer() { if (confirm('Reboot the server now?')) sendAction('reboot_server'); }
    function restartHomepage() { if (confirm('Restart homepage application?')) sendAction('restart_homepage'); }

    loadBookmarks();
    fetchStats();
    setInterval(fetchStats, 10000);
  </script>
</body>
</html>
"""

SERVICE_NAME = 'home_page'


def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, '', f'Command not found: {command[0]}'


def shutil_which(name):
    return shutil.which(name)


def format_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f'{days}d {hours:02}:{minutes:02}:{seconds:02}'
    return f'{hours:02}:{minutes:02}:{seconds:02}'


def get_system_stats():
    uptime = 'unknown'
    load = 'unknown'
    memory = 'unknown'
    disk = 'unknown'

    if os.path.exists('/proc/uptime'):
        try:
            with open('/proc/uptime', 'r', encoding='utf-8') as f:
                uptime_seconds = float(f.read().split()[0])
            uptime = format_duration(int(uptime_seconds))
        except Exception:
            pass

    try:
        load1, load5, load15 = os.getloadavg()
        load = f'{load1:.2f}, {load5:.2f}, {load15:.2f}'
    except Exception:
        pass

    if os.path.exists('/proc/meminfo'):
        try:
            meminfo = {}
            with open('/proc/meminfo', 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        meminfo[key.strip()] = int(value.strip().split()[0])
            total = meminfo.get('MemTotal')
            free = meminfo.get('MemAvailable', meminfo.get('MemFree'))
            if total and free:
                used = total - free
                memory = f'{used // 1024}MB / {total // 1024}MB'
        except Exception:
            pass

    try:
        usage = shutil.disk_usage('/')
        disk = f'{usage.used // (1024**3)}GB / {usage.total // (1024**3)}GB'
    except Exception:
        pass

    return {
        'uptime': uptime,
        'load': load,
        'memory': memory,
        'disk': disk,
    }


def load_bookmarks():
    if not os.path.exists(BOOKMARKS_FILE):
        return []
    try:
        with open(BOOKMARKS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_bookmarks(bookmarks):
    try:
        with open(BOOKMARKS_FILE, 'w', encoding='utf-8') as f:
            json.dump(bookmarks, f, indent=2, ensure_ascii=False)
        return True
    except Exception:
        return False


def perform_action(action, server=None):
    if action == 'restart_homepage':
        if server is not None:
            server.should_restart = True
            server.shutdown()
            return True, 'Homepage restart initiated'
        return False, 'Server handle unavailable'

    if action == 'reboot_server':
        if shutil_which('systemctl'):
            code, out, err = run_command(['sudo', 'systemctl', 'reboot'])
        else:
            code, out, err = run_command(['sudo', 'reboot'])
        if code == 0:
            return True, 'Reboot command sent'
        return False, err or out or f'reboot failed ({code})'

    return False, f'Unknown action: {action}'


class HomeHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='text/html'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self._set_headers(200)
            self.wfile.write(HOME_HTML.encode('utf-8'))
            return
        if parsed.path == '/api/stats':
            stats = get_system_stats()
            self._set_headers(200, 'application/json')
            self.wfile.write(json.dumps(stats).encode('utf-8'))
            return
        if parsed.path == '/api/bookmarks':
            bookmarks = load_bookmarks()
            self._set_headers(200, 'application/json')
            self.wfile.write(json.dumps(bookmarks).encode('utf-8'))
            return
        self._set_headers(404, 'application/json')
        self.wfile.write(json.dumps({'error': 'not found'}).encode('utf-8'))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == '/api/bookmarks':
            length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(length).decode('utf-8')
            try:
                payload = json.loads(body)
                bookmarks = payload.get('bookmarks', [])
                if not isinstance(bookmarks, list):
                    raise ValueError('Invalid bookmarks payload')
                saved = save_bookmarks(bookmarks)
                if not saved:
                    raise ValueError('Failed to write bookmarks')
                self._set_headers(200, 'application/json')
                self.wfile.write(json.dumps({'success': True, 'bookmarks': bookmarks}).encode('utf-8'))
                return
            except Exception as exc:
                self._set_headers(400, 'application/json')
                self.wfile.write(json.dumps({'success': False, 'error': str(exc)}).encode('utf-8'))
                return
        if parsed.path != '/api/action':
            self._set_headers(404, 'application/json')
            self.wfile.write(json.dumps({'error': 'not found'}).encode('utf-8'))
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        params = parse_qs(body)
        action = params.get('action', [''])[0]
        success, message = perform_action(action, server=self.server)
        self._set_headers(200, 'application/json')
        self.wfile.write(json.dumps({'success': success, 'message': message}).encode('utf-8'))

    def log_message(self, format, *args):
        return


def run(port=6969):
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HomeHandler)
    httpd.should_restart = False
    print(f'Serving homepage on http://0.0.0.0:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down homepage server')
    finally:
        httpd.server_close()

    if getattr(httpd, 'should_restart', False):
        print('Restarting homepage...')
        os.execv(sys.executable, [sys.executable, __file__, str(port)])


if __name__ == '__main__':
    port = 6969
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run(port)


