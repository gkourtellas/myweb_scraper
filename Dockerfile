FROM mcr.microsoft.com/playwright/python:v1.54.0-jammy

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY main.py notify.py status_web.py home_page.py urls.txt bookmarks.json ./
COPY docker/ docker/
#COPY autobet/ autobet/

#RUN pip install -r autobet/requirements.txt && chmod +x autobet/run_autobet.sh

RUN chmod +x docker/run-scraper.sh docker/entrypoint.sh \
    && mkdir -p /app/logs

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["scraper"]
