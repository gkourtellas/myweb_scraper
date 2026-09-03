#!/usr/bin/env python3
from playwright.sync_api import sync_playwright

SELECTOR = "#main-content > div.content-wrap.has-side > div > div > div.sb-fc-heroWrap"

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    page = browser.new_page()
    page.goto("https://sportbet.gr/prognostika-to-dynato-simeio-imeras/", timeout=60000)
    page.wait_for_selector(SELECTOR, timeout=15000)
    element = page.query_selector(SELECTOR)
    if element:
        print("FOUND. Raw text:\n")
        print(element.inner_text())
    else:
        print("NOT FOUND — selector matched nothing.")
    browser.close()
