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
# Clears old entries from previous days from the log file, keeping all of today's entries
def clear_log_daily(log_file):
    if os.path.exists(log_file):
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
        
        today_str = datetime.today().strftime("%Y-%m-%d")
        updated_data = {}
        
        # Only keep log entries that were stored today
        for key, val in data.items():
            if isinstance(val, dict) and val.get("date") == today_str:
                updated_data[key] = val
                
        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(updated_data, f, ensure_ascii=False, indent=2)

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
#FAILURE_COOLDOWN_SECONDS = 6 * 3600
FAILURE_COOLDOWN_SECONDS = 1 * 3600

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

    def wait_for_kingbet_selection(slide_selector, before_match_text):
        try:
            # Dismiss cookie banner first (it blocks all clicks)
            for cookie_sel in ['button:has-text("ΣΥΜΦΩΝΩ")', 'button:has-text("Συμφωνώ")', '[aria-label*="Agree"]']:
                try:
                    btn = page.query_selector(cookie_sel)
                    if btn:
                        btn.click()
                        page.wait_for_timeout(1000)
                        break
                except:
                    pass
            
            # Click today's slide directly
            today_iso = datetime.today().date().isoformat()
            slide = page.query_selector(f'[data-date="{today_iso}"]')
            if slide:
                slide.click()
                page.wait_for_timeout(1500)
            
            # Wait for the actual match name to change
            page.wait_for_function(
                """
                before => {
                    const matchName = document.querySelector('.betting-feature__match-name');
                    return Boolean(matchName && matchName.innerText.trim() && matchName.innerText.trim() !== before);
                }
                """,
                arg=before_match_text,
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

    # matchbot_root = os.environ.get("MATCHBOT_OUTPUT_DIR", "/home/gk/matchbot")
    # output_path = os.path.join(matchbot_root, "autobet", "tips", file_name)
    # os.makedirs(os.path.dirname(output_path), exist_ok=True)
    # with open(output_path, "w", encoding="utf-8") as f:
    #     json.dump({
    #         "date": datetime.today().strftime("%Y-%m-%d"),
    #         "tip": normalized_tip
    #     }, f, ensure_ascii=False, indent=2)


def write_sendragoal_json(tip_text):
    """Write the latest SendraGoal tip to /home/gk/matchbot/sendragoal.json."""
    # write_matchbot_json(tip_text, "sendragoal.json")


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

                # if any(domain in full_url.lower() for domain in ['sendragoal', 'sentragoal']):
                #     write_sendragoal_json(compare_text)
                # if 'kingbet.com.cy/to-dynato-simeio-imeras' in full_url.lower():
                #     write_matchbot_json(compare_text, 'kingbet_to_dynato.json')
                # if 'kingbet.com.cy/favori-imeras' in full_url.lower():
                #     write_matchbot_json(compare_text, 'kingbet_to_favori.json')

                should_send = False
                # Backward-compatible: older runs stored full content; trim it before comparing
                last_content_raw = last_sent.get(unique_key, "")
                if isinstance(last_content_raw, dict):
                    last_content_text = last_content_raw.get("text", "")
                else:
                    last_content_text = last_content_raw
                last_content = get_compare_text(last_content_text, lines_to_trim) if last_content_text else ""

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
                        today_str = datetime.today().strftime("%Y-%m-%d")
                        saved_entry = {"text": compare_text, "date": today_str}
                        last_sent[unique_key] = saved_entry
                        sent_log[unique_key] = saved_entry
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