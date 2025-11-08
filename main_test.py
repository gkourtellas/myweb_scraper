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

def extract_percentage(text):
    """Extract percentage from text like '(72%)'"""
    match = re.search(r'\((\d+)%\)', text)
    return int(match.group(1)) if match else 0

def scrape_betclever(page, url, last_sent, sent_log):
    """Special handler for betclever - scrapes all tips, sorts by %, sends only >75%"""
    print(f"\n🎯 Betclever special handler activated for: {url}")

    try:
        page.goto(url, timeout=60000)
        page.wait_for_selector('body > div.wrapper > main > section.all-games > div > div.singles > div.singles__wrap', timeout=30000)

        # Get the specific container first, then items within it
        container = page.query_selector('body > div.wrapper > main > section.all-games > div > div.singles > div.singles__wrap')
        if not container:
            print("❌ Container not found")
            return

        items = container.query_selector_all('.singles__item')
        print(f"Found {len(items)} tips in betclever container")

        tips = []
        for item in items:
            try:
                # Extract team names
                names = item.query_selector_all('.singles__item-left-name')
                team1 = names[0].inner_text().strip() if len(names) > 0 else "?"
                team2 = names[1].inner_text().strip() if len(names) > 1 else "?"

                # Extract time and league
                time_elem = item.query_selector('.singles__item-right-time')
                time_text = time_elem.inner_text().strip() if time_elem else "?"

                league_elem = item.query_selector('.singles__item-right-liga')
                league = league_elem.inner_text().strip() if league_elem else "?"

                # Extract tip and percentage
                tip_elem = item.query_selector('.singles__item-right-winner b')
                tip_text = tip_elem.inner_text().strip() if tip_elem else "?"

                # Extract odds
                odds_elem = item.query_selector('.singles__item-right-odd button')
                odds = odds_elem.inner_text().strip() if odds_elem else "?"

                # Get percentage
                percentage = extract_percentage(tip_text)

                tips.append({
                    'team1': team1,
                    'team2': team2,
                    'time': time_text,
                    'league': league,
                    'tip': tip_text,
                    'odds': odds,
                    'percentage': percentage
                })
            except Exception as e:
                print(f"Error parsing betclever item: {e}")

        # Sort by percentage (highest first)
        tips.sort(key=lambda x: x['percentage'], reverse=True)

        # Filter for >75%
        high_confidence = [t for t in tips if t['percentage'] > 75]

        print(f"High confidence tips (>75%): {len(high_confidence)}")

        if high_confidence:
            # Format all tips into a single message
            message_parts = [f"🎯 BETCLEVER HIGH CONFIDENCE TIPS ({len(high_confidence)} tips >75%)\n"]

            for tip in high_confidence:
                tip_msg = (
                    f"⚽ {tip['team1']} vs {tip['team2']}\n"
                    f"⏰ {tip['time']} | {tip['league']}\n"
                    f"💡 {tip['tip']}\n"
                    f"📊 Odds: {tip['odds']}\n"
                )
                message_parts.append(tip_msg)

            combined_message = "\n".join(message_parts)

            # Check if we already sent this exact set of tips
            last_content = last_sent.get(url, "")

            if not is_mostly_same(combined_message, last_content):
                print("✅ Sending betclever high confidence tips:")
                print(combined_message)
                send_message(combined_message, url=url, lines_to_trim=100)
                last_sent[url] = combined_message
                sent_log[url] = combined_message
            else:
                print("ℹ️ Betclever tips already sent (content is mostly the same).")
        else:
            print("❌ No betclever tips above 75% confidence found.")

    except Exception as e:
        print(f"Error scraping betclever: {e}")

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
    with open("urls_test.txt", "r") as f:
        lines = f.read().splitlines()
        for line in lines:
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
                sites.append((url, url_type, selector, date_format, lines_to_trim))

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        page = browser.new_page()

        for url, url_type, selector, date_format, lines_to_trim in sites:
            full_url = f"{url}{today_url}/" if url_type == "date" else url
            print(f"\nChecking: {full_url}")

            # Special handling for betclever
            if 'betclever.com' in full_url:
                scrape_betclever(page, full_url, last_sent, sent_log)
                continue

            try:
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
                            print("No element found with selector:", sel)
                    except Exception as e:
                        print(f"Selector error for {sel}: {e}")

                # Filter out empty strings from contents
                contents = [c for c in contents if c.strip()]
                # Combine the content from all selectors
                combined_content = "\n".join(contents)
                print("🔍 Raw content:", combined_content)

                # Use only the trimmed, normalized message for dedupe
                compare_text = get_compare_text(combined_content, lines_to_trim)

                should_send = False
                # Backward-compatible: older runs stored full content; trim it before comparing
                last_content_raw = last_sent.get(full_url, "")
                last_content = get_compare_text(last_content_raw, lines_to_trim) if last_content_raw else ""

                if date_format:
                    expected_date = date_formats.get(date_format, "")
                    if expected_date in combined_content:
                        # Only send if content is significantly different (based on trimmed text)
                        should_send = not last_content or not is_mostly_same(compare_text, last_content)
                        if should_send:
                            print("✅ Tip found for today:")
                            print(compare_text)
                        else:
                            print("ℹ️ Tip already sent (content is mostly the same).")
                    else:
                        print("❌ No Tip Today")
                else:
                    # Only send if content is significantly different (based on trimmed text)
                    should_send = not last_content or not is_mostly_same(compare_text, last_content)
                    if should_send:
                        print("✅ Content found:")
                        print(compare_text)
                    else:
                        print("ℹ️ Content already sent (content is mostly the same).")

                if should_send:
                    # Send full combined content (notify trims again for chat), but store trimmed for dedupe
                    send_message(combined_content, url=full_url, lines_to_trim=lines_to_trim)
                    last_sent[full_url] = compare_text
                    sent_log[full_url] = compare_text

            except Exception as e:
                print(f"Error accessing {full_url}: {e}")

        browser.close()

    with open(log_file, "w") as f:
        json.dump(sent_log, f, indent=2)
    save_last_sent(last_sent_file, last_sent)

if __name__ == "__main__":
    while True:
        check_sites()
        print("Sleeping for 100 minutes...")
        time.sleep(6000)  # 6000 seconds = 100 minutes