#!/usr/bin/env python3
"""Check what's actually on foxbet to-dunato page."""

from playwright.sync_api import sync_playwright

URL = "https://www.foxbet.gr/316026/to-dunato-simeio-tis-imeras"

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto(URL, timeout=60000)
    page.wait_for_timeout(2000)

    # Wait for table to load dynamically
    try:
        page.wait_for_selector("table.prediction_bet_1_2cols", timeout=15000)
        print("Table loaded after wait.")
    except Exception as e:
        print(f"Table never appeared: {e}")
        print("Checking page for any tables at all...")
        all_tables = page.query_selector_all("table")
        print(f"Total tables on page: {len(all_tables)}")
        for i, table in enumerate(all_tables[:3]):
            classes = table.get_attribute("class")
            print(f"Table {i}: class='{classes}'")
        browser.close()
        exit(1)

    # Check tables
    tables = page.query_selector_all("table.prediction_bet_1_2cols")
    print(f"Tables found: {len(tables)}")
    
    if tables:
        table = tables[0]
        rows = table.query_selector_all("tbody tr")
        print(f"Rows in first table: {len(rows)}")
        
        if len(rows) > 1:
            print("\nRow 2 HTML:")
            print(rows[1].inner_html()[:800])
        else:
            print("\nNo second row")
            if rows:
                print("Row 1 HTML:")
                print(rows[0].inner_html()[:800])

    browser.close()
