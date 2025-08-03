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
    # Prepare today's date in various formats
    today_url = datetime.today().strftime("%d-%m-%y")
    today_display_ddmm = datetime.today().strftime("%d/%m")
    today_display_ddmmyy = datetime.today().strftime("%d/%m/%y")
    today_display_mmdd = datetime.today().strftime("%m/%d")

    # Map for date format options
    date_formats = {
        "dd/mm": today_display_ddmm,
        "dd/mm/yy": today_display_ddmmyy,
        "mm/dd": today_display_mmdd
    }

    log_file = "sent_log.json"
    clear_log_daily(log_file)  # Reset log if needed

    # Load sent log to avoid duplicate notifications
    if os.path.exists(log_file):
        with open(log_file, "r") as f:
            sent_log = json.load(f)
    else:
        sent_log = {}

    sites = []
    # Read and parse urls.txt for site configs
    with open("urls.txt", "r") as f:
        lines = f.read().splitlines()
        for line in lines:
            parts = line.split("|")
            if len(parts) >= 3:
                url = parts[0].strip()
                url_type = parts[1].strip().lower()
                selector = parts[2].strip()
                # Optional date format and lines_to_trim
                date_format = parts[3].strip().lower() if len(parts) > 3 else ""
                lines_to_trim = (
                    int(parts[4].strip()) if len(parts) > 4 and parts[4].strip().isdigit()
                    else int(parts[3].strip()) if len(parts) > 3 and parts[3].strip().isdigit()
                    else 1
                )
                sites.append((url, url_type, selector, date_format, lines_to_trim))

    # Start Playwright browser session
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Iterate through all sites
        for url, url_type, selector, date_format, lines_to_trim in sites:
            # Append date to URL if needed
            full_url = f"{url}{today_url}/" if url_type == "date" else url
            print(f"\nChecking: {full_url}")
            try:
                page.goto(full_url, timeout=60000)
                page.wait_for_selector(selector, timeout=30000)
                element = page.query_selector(selector)

                content = ""
                if element:
                    # Special handling for tables: get last row
                    if selector.endswith("table"):
                        rows = element.query_selector_all("tr")
                        if rows:
                            content = rows[-1].inner_text().strip()
                    else:
                        content = element.inner_text().strip()

                    print("🔍 Raw content:", content)

                    # If a date format is specified, check for today's date in content
                    if date_format:
                        expected_date = date_formats.get(date_format, "")
                        if expected_date in content:
                            if sent_log.get(full_url) != content:
                                print("✅ Tip found for today:")
                                print(content)
                                send_message(content, url=full_url, lines_to_trim=lines_to_trim)
                                sent_log[full_url] = content
                            else:
                                print("ℹ️ Tip already sent.")
                        else:
                            print("❌ No Tip Today")
                    else:
                        # No date format: just check for new content
                        if sent_log.get(full_url) != content:
                            print("✅ Content found:")
                            print(content)
                            send_message(content, url=full_url, lines_to_trim=lines_to_trim)
                            sent_log[full_url] = content
                        else:
                            print("ℹ️ Content already sent.")
                else:
                    print("No element found with selector:", selector)
            except Exception as e:
                print(f"Error accessing {full_url}: {e}")

        browser.close()

    # Save updated sent log
    with open(log_file, "w") as f:
        json.dump(sent_log, f, indent=2)

# Main loop: run check_sites every 100 minutes
if __name__ == "__main__":
    while True:
        check_sites()
        print("Sleeping for 100 minutes...")
        time.sleep(600)  # 6000 seconds = 100 minutes