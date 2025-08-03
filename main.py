import json
import os
import time
from datetime import datetime
from playwright.sync_api import sync_playwright
from notify import send_message

# Clears the log file if it's a new day
def clear_log_daily(log_file):
    if os.path.exists(log_file):
        last_modified = datetime.fromtimestamp(os.path.getmtime(log_file))
        today = datetime.today().date()
        if last_modified.date() != today:
            with open(log_file, "w") as f:
                json.dump({}, f)

# Main function to check all sites listed in urls.txt
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
    clear_log_daily(log_file)

    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            sent_log = json.load(f)
    else:
        sent_log = {}

    sites = []
    with open("urls.txt", "r") as f:
        lines = f.read().splitlines()
        for line in lines:
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
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for url, url_type, selector, date_format, lines_to_trim in sites:
            full_url = f"{url}{today_url}/" if url_type == "date" else url
            print(f"\nChecking: {full_url}")
            try:
                page.goto(full_url, timeout=60000)
                # Split selectors by comma and strip whitespace
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

                combined_content = "\n".join(contents)
                print("🔍 Raw content:", combined_content)

                if date_format:
                    expected_date = date_formats.get(date_format, "")
                    if expected_date in combined_content:
                        if sent_log.get(full_url) != combined_content:
                            print("✅ Tip found for today:")
                            print(combined_content)
                            send_message(combined_content, url=full_url, lines_to_trim=lines_to_trim)
                            sent_log[full_url] = combined_content
                        else:
                            print("ℹ️ Tip already sent.")
                    else:
                        print("❌ No Tip Today")
                else:
                    if sent_log.get(full_url) != combined_content:
                        print("✅ Content found:")
                        print(combined_content)
                        send_message(combined_content, url=full_url, lines_to_trim=lines_to_trim)
                        sent_log[full_url] = combined_content
                    else:
                        print("ℹ️ Content already sent.")
            except Exception as e:
                print(f"Error accessing {full_url}: {e}")

        browser.close()

    with open(log_file, "w") as f:
        json.dump(sent_log, f, indent=2)

if __name__ == "__main__":
    while True:
        check_sites()
        print("Sleeping for 100 minutes...")
        time.sleep(6000)  # 6000 seconds = 100 minutes