#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.foxbet.gr/316026/to-dunato-simeio-tis-imeras", timeout=60000)
    page.wait_for_timeout(3000)
    
    # Look for "26" or "Ιαπωνία" (today's match) in the page
    content = page.content()
    
    # Find position of Japan (Ιαπωνία) 
    if "Ιαπωνία" in content:
        idx = content.find("Ιαπωνία")
        print("Found 'Ιαπωνία' at position", idx)
        print("Context (500 chars before and after):")
        print(content[max(0, idx-500):idx+500])
    else:
        print("'Ιαπωνία' not found on page")
        print("\nSearching for '26/06'...")
        if "26/06" in content:
            idx = content.find("26/06")
            print("Found '26/06' at position", idx)
            print(content[max(0, idx-300):idx+300])
    
    browser.close()
