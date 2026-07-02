# For Dummies Guide 🐾

A simple guide to running and managing this web scraper project.

## 1. How to Start Everything
The easiest way is using **Docker**.

1. Open your terminal in the project folder.
2. Run this command:
   ```bash
   docker compose up -d
   ```
   *This starts the scraper, the dashboard, and the homepage all at once in the background.*

## 2. How to Access the Interfaces
Open your web browser and go to:

*   **Homepage (Bookmarks & Stats):** `http://localhost:6969`
*   **Status Dashboard (Control & Tips):** `http://localhost:8001`
    *   *Note: If you are on a server, replace `localhost` with your server's IP address.*

## 3. How to Stop Everything
To stop all services, run:
```bash
docker compose down
```

## 4. How to Check Logs (Troubleshooting)
If something isn't working, check the logs to see what's happening:

*   **Scraper logs:** `docker compose logs -f scraper`
*   **Status logs:** `docker compose logs -f status`
*   **Homepage logs:** `docker compose logs -f homepage`
*   *Press `Ctrl+C` to stop watching the logs.*

## 5. Important Files
*   **`urls.txt`**: This is where you list the websites you want to scrape.
*   **`tginfo.txt`**: This contains your Telegram Bot Token and Chat ID for notifications.
*   **`.env`**: General settings (like how often to scrape).

## 6. Quick Refresh
If you changed `urls.txt` or `main.py` and want the scraper to pick up changes immediately:
```bash
docker compose restart scraper
```
