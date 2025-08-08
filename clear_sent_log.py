import json

log_files = ['sent_log.json', 'last_sent.json']

for log_file in log_files:
    with open(log_file, 'w') as f:
        json.dump({}, f, indent=2)
    print(f"{log_file} has been cleared.")

with open('urls.txt', 'r', encoding='utf-8') as f:
    for line in f:
        parts = line.strip().split('|')
        if len(parts) > 4 and parts[4].strip().isdigit():
            lines_to_trim = int(parts[4].strip())
        elif len(parts) > 3 and parts[3].strip().isdigit():
            lines_to_trim = int(parts[3].strip())
        else:
            lines_to_trim = 1
        print(lines_to_trim)