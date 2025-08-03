# Imports for URL parsing and HTTP requests
from urllib.parse import urlparse
import requests

# Reads Telegram bot token and chat ID from a file
def read_telegram_info(tginfo_path='tginfo.txt'):
    with open(tginfo_path, 'r') as f:
        lines = f.read().splitlines()
        token = lines[0].strip()  # First line: bot token
        chat_id = lines[1].strip()  # Second line: chat ID
    return token, chat_id

# Extracts the site name from a given URL for labeling messages
def extract_site_name(url):
    netloc = urlparse(url).netloc  # Get network location part of URL
    if netloc.startswith('www.'):
        netloc = netloc[4:]  # Remove 'www.' prefix if present
    site_name = netloc.split('.')[0]  # Take the first part as site name
    return site_name if site_name else 'unknown'

# Sends a message to a Telegram chat using the bot API
def send_message(message, url=None, tginfo_path='tginfo.txt', lines_to_trim=10):
    trimmed_message = "\n".join(message.splitlines()[:lines_to_trim])  # Limit message lines
    token, chat_id = read_telegram_info(tginfo_path)  # Get credentials
    if url:
        site_name = extract_site_name(url)  # Get site name for context
        trimmed_message = f"[{site_name}] {trimmed_message}"  # Prefix message with site name
    url_api = f'https://api.telegram.org/bot{token}/sendMessage'  # Telegram API endpoint
    payload = {'chat_id': chat_id, 'text': trimmed_message}  # Message payload
    response = requests.post(url_api, data=payload)  # Send POST request
    print("Telegram response:", response.text)  # Print API response for debugging
    return response.ok  # Return True if request was successful