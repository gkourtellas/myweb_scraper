#python
import json
import os
from datetime import datetime
from playwright.sync_api import sync_playwright
from notify import send_message

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
            sites.append((url, url_type, selector, date_format))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()

    for url, url_type, selector, date_format in sites:
        full_url = f"{url}{today_url}/" if url_type == "date" else url
        print(f"\nChecking: {full_url}")
        try:
            page.goto(full_url, timeout=60000)
            page.wait_for_selector(selector, timeout=30000)
            element = page.query_selector(selector)

            content = ""
            if element:
                if selector.endswith("table"):
                    rows = element.query_selector_all("tr")
                    if rows:
                        content = rows[-1].inner_text().strip()
                else:
                    content = element.inner_text().strip()

                print("🔍 Raw content:", content)

                if date_format:
                    expected_date = date_formats.get(date_format, "")
                    if expected_date in content:
                        if sent_log.get(full_url) != content:
                            print("✅ Tip found for today:")
                            print(content)
                            send_message(content, url=full_url)
                            sent_log[full_url] = content
                        else:
                            print("ℹ️ Tip already sent.")
                    else:
                        print("❌ No Tip Today")
                else:
                    if sent_log.get(full_url) != content:
                        print("✅ Content found:")
                        print(content)
                        send_message(content, url=full_url)
                        sent_log[full_url] = content
                    else:
                        print("ℹ️ Content already sent.")
            else:
                print("No element found with selector:", selector)
        except Exception as e:
            print(f"Error accessing {full_url}: {e}")

    browser.close()

with open(log_file, "w") as f:
    json.dump(sent_log, f, indent=2)