# clear_sent_log.py
import json

log_file = 'sent_log.json'

with open(log_file, 'w') as f:
    json.dump({}, f, indent=2)

print(f"{log_file} has been cleared.")