#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    page.goto("https://www.foxbet.gr/316026/to-dunato-simeio-tis-imeras", timeout=60000)
    page.wait_for_timeout(3000)
    
    print("Searching for tip containers...\n")
    
    selectors = [
        ".post_content .table",
        ".post_content > div",
        "[class*='tip']",
        "[class*='prediction']",
        ".entry-content table",
        ".wp-content",
        "article",
        "[class*='betting']",
    ]
    
    for sel in selectors:
        els = page.query_selector_all(sel)
        if els:
            print(f"✓ {sel}: {len(els)} found")
    
    # Also check the immediate structure after post_content
    post = page.query_selector(".post_content")
    if post:
        print("\n.post_content direct children:")
        children = post.query_selector_all(":scope > *")
        for i, child in enumerate(children[:5]):
            tag = child.evaluate("el => el.tagName")
            cls = child.get_attribute("class")
            print(f"  Child {i}: <{tag}> class='{cls}'")
    
    browser.close()
