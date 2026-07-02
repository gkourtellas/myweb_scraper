import os

# The exact list of files to look for
files_to_collect = [
    "docker-compose.yml",
    "Dockerfile",
    "requirements.txt",
    "urls.txt",
    "docker/entrypoint.sh",
    "docker/run-scraper.sh",
    "main.py",
    "notify.py",
    "status_web.py",
    "home_page.py"
]

output_md = "files.md"

with open(output_md, "w", encoding="utf-8") as outfile:
    for filepath in files_to_collect:
        if os.path.exists(filepath):
            outfile.write(f"--- {filepath} ---\n")
            with open(filepath, "r", encoding="utf-8", errors="ignore") as infile:
                outfile.write(infile.read())
            outfile.write("\n\n")
        else:
            print(f"Skipping: {filepath} (Not found)")

print(f"Successfully created {output_md}")