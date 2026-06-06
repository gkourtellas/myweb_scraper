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
    with open(file_name, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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
    page.goto(url, timeout=60000)
    page.wait_for_load_state("domcontentloaded")

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
        wait_for_kingbet_selection(f".betting-features__calendar__slide[data-date='{today_iso}']", before_text)
        page.wait_for_timeout(500)
        print(f"Selected kingbet date tab: {today_iso} on {url}", flush=True)
        return True

    for label in labels_to_try:
        button = page.locator("button", has_text=label)
        if button.count() > 0:
            before_text = page.locator('.betting-features__listing').inner_text().strip()
            js_click(button.first)
            wait_for_kingbet_selection(".betting-features__calendar__slide.current", before_text)
            page.wait_for_timeout(500)
            print(f"Selected kingbet date tab: {label} on {url}", flush=True)
            return True

    for candidate in ("button", "a", "[role='tab']"):
        for element in page.locator(candidate).all():
            label = element.inner_text().strip()
            if parse_kingbet_date_label(label) == today:
                before_text = page.locator('.betting-features__listing').inner_text().strip()
                js_click(element)
                wait_for_kingbet_selection(".betting-features__calendar__slide.current", before_text)
                page.wait_for_timeout(500)
                print(f"Selected kingbet date tab: {label} on {url}", flush=True)
                return True

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
            wait_for_kingbet_selection(f".betting-features__calendar__slide[data-date='{today_iso}']", before_text)
            page.wait_for_timeout(500)
            print(f"Selected kingbet date tab: {label} on {url}", flush=True)
            return True

    print(
        f"No kingbet date tab for today ({today.strftime('%d.%m.%y')}) on {url} — "
        "skipping to avoid stale tips",
        flush=True,
    )
    return False


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
            if is_kingbet and not select_kingbet_today_tab(page, url):
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
                        page.wait_for_selector(sel, timeout=30000)
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
                    send_message(combined_content, url=full_url, lines_to_trim=lines_to_trim)
                    last_sent[unique_key] = compare_text
                    sent_log[unique_key] = compare_text

            except Exception as e:
                print(f"Error accessing {full_url}: {e}", flush=True)

        browser.close()

    with open(log_file, "w") as f:
        json.dump(sent_log, f, indent=2)
    save_last_sent(last_sent_file, last_sent)

def main():
    # Entry point for the script
    print("Starting bot...", flush=True)
    check_sites()

if __name__ == "__main__":
    main()

