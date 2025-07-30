# myweb_scraper

## Project Overview

This project is a web scraping utility designed to monitor specific websites for daily updates or tips and send notifications via Telegram when new content is detected. It runs on a headless Ubuntu server and uses Playwright for browser automation.

## Features

- Scrapes predefined websites using CSS selectors.
- Supports both static and date-based URLs.
- Detects new content based on date or content changes.
- Sends Telegram notifications when new tips are found.
- Avoids duplicate notifications using a persistent log file.

## File Descriptions

- `main.py`: Main script that loads URLs from `urls.txt`, scrapes content using Playwright, checks for updates, and sends notifications via Telegram.
- `notify.py`: Contains the `send_message()` function to send messages via Telegram (currently a placeholder implementation).
- `urls.txt`: List of URLs to scrape, each line formatted as `<url>|<type>|<css selector>|<optional date format>`.
- `sent_log.json`: Automatically created to store previously sent content and avoid duplicate notifications.
- `tginfo.txt`: Contains Telegram bot token and chat ID (not included here for security).


## urls.txt

This file contains the list of websites to be scraped. Each line specifies the URL, the type of content (static or date-based), the CSS selector to locate the desired content, and optionally the date format to match. The script uses this information to determine what to scrape and how to interpret the results.
