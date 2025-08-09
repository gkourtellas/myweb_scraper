# Web Scraper with Playwright

A Python web scraper that checks a list of URLs for new content or tips using Playwright, and sends notifications when updates are found.

## Features

- Reads URLs, selectors, and options from `urls.txt`
- Uses Playwright for headless browser automation
- Detects new content or daily tips (supports date-based checks)
- Sends notifications via a custom `notify.py` module
- Maintains a daily log to avoid duplicate notifications
- **Creates a new `.xlsx` log file for each month, named `tips_log_YYYY_MM.xlsx`**
- **Log files are kept locally for now**

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
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   playwright install
   ```

4. Edit `urls.txt` with your target URLs and selectors.

5. Configure `notify.py` to send notifications as needed.

## Usage

Run the scraper manually:

```bash
python main.py
```

The script will check all sites and repeat every 100 minutes.

Each month, a new log file is created and stored locally.

## Log File Management

Log files (`tips_log_YYYY_MM.xlsx`) are kept locally.

If you want to upload a log file to your private GitHub repository manually:

```bash
# Copy the file into your repo directory.
git add tips_log_YYYY_MM.xlsx
git commit -m "Add monthly tips log"
git push origin master
```

Automation for uploading log files can be added later if needed.

## Running as a Service

To run automatically on startup, create a systemd service file pointing to your virtual environment's Python and `main.py`.

## File Overview

- `main.py` — Main scraping script  
- `urls.txt` — List of URLs, selectors, and options  
- `sent_log.json` — Log of sent notifications (auto-managed)  
- `notify.py` — Notification logic  

## Deployment Notes

Copy files to server:

```bash
scp *.py gk@monitor:/home/gk/myweb_scraper
```

After copy, stop the service (it will restart automatically):

```bash
# Find the process ID
ps aux | grep main.py

# Kill it
kill <PID>
```
| Command                | Description                                      |
|------------------------|--------------------------------------------------|
| tmux                   | Start a new tmux session                         |
| python main.py         | Run your Python script inside tmux                |
| Ctrl+b d               | Detach from the session (keep script running)     |
| tmux attach            | Reattach to the session to view output            |
| exit                   | Exit the tmux session and stop the script         |
| tmux ls                | List all tmux sessions                            |
| tmux kill-session -t <name> | Kill a specific session by name             |
## License

MIT License
