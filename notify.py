import re
import requests

def extract_site_name(url):
    match = re.search(r'//([^\.]+)\.', url)
    return match.group(1) if match else 'unknown'

def read_telegram_info(file_path='tginfo.txt'):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    token = lines[0].split(': ', 1)[1].strip().replace('https://api.telegram.org/bot', '').replace('/getUpdates', '')
    chat_id = lines[1].split(': ', 1)[1].strip()
    return token, chat_id

def send_message(message, url=None, tginfo_path='tginfo.txt'):
    token, chat_id = read_telegram_info(tginfo_path)
    if url:
        site_name = extract_site_name(url)
        message = f"[{site_name}] {message}"
    url_api = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': message}
    response = requests.post(url_api, data=payload)
    return response.ok