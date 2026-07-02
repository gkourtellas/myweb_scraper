#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.foxbet.gr/316026/to-dunato-simeio-tis-imeras", timeout=60000)
    page.wait_for_selector("table.prediction_bet_1_3cols", timeout=15000)
    
    table = page.query_selector("table.prediction_bet_1_3cols")
    rows = table.query_selector_all("tbody tr")
    print(f"Total rows: {len(rows)}\n")
    
    for i, row in enumerate(rows[:8]):
        text = row.inner_text()[:200]
        print(f"Row {i+1}:")
        print(text)
        print("-" * 50)
    
    browser.close()
