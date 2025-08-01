# python
from urllib.parse import urlparse
import requests

def read_telegram_info(tginfo_path='tginfo.txt'):
    with open(tginfo_path, 'r') as f:
        lines = f.read().splitlines()
        token = lines[0].strip()
        chat_id = lines[1].strip()
    return token, chat_id

def extract_site_name(url):
    netloc = urlparse(url).netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    site_name = netloc.split('.')[0]
    return site_name if site_name else 'unknown'

def send_message(message, url=None, tginfo_path='tginfo.txt', lines_to_trim=3):
    trimmed_message = "\n".join(message.splitlines()[:lines_to_trim])
    token, chat_id = read_telegram_info(tginfo_path)
    if url:
        site_name = extract_site_name(url)
        trimmed_message = f"[{site_name}] {trimmed_message}"
    url_api = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': trimmed_message}
    response = requests.post(url_api, data=payload)
    print("Telegram response:", response.text)  # Debug output
    return response.ok