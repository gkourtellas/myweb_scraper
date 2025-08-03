# Web Scraper with Playwright

A Python web scraper that checks a list of URLs for new content or tips using Playwright, and sends notifications when updates are found.

## Features

- Reads URLs, selectors, and options from `urls.txt`
- Uses Playwright for headless browser automation
- Detects new content or daily tips (supports date-based checks)
- Sends notifications via a custom `notify.py` module
- Maintains a daily log to avoid duplicate notifications

## Requirements

- Python 3.8+
- Playwright (`pip install playwright`)
- See `requirements.txt` for all dependencies

## Setup

1. Clone this repository.
2. Create and activate a virtual environment:

   ```bash
   python -m venv venv
   # On Linux/macOS:
   source venv/bin/activate
   # On Windows:
   venv\Scripts\activate

   Install dependencies:


pip install -r requirements.txt
playwright install
Edit urls.txt with your target URLs and selectors.


Configure notify.py to send notifications as needed.


Usage
Run the scraper manually:
python main.py

The script will check all sites and repeat every 100 minutes.


Running as a Service
To run automatically on startup, create a systemd service file pointing to your virtual environment's Python and main.py.
Check Status
sudo systemctl status mywebscraper

File Overview
main.py — Main scraping script
urls.txt — List of URLs, selectors, and options
sent_log.json — Log of sent notifications (auto-managed)
notify.py — Notification logic
License
MIT License


