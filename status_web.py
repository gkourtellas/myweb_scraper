import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import db

APP_VERSION = "1.2.2"
SERVICE_NAME = "myweb_scraper"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SENT_LOG_FILE = os.path.join(BASE_DIR, "sent_log.json")
RUNTIME = os.environ.get("RUNTIME", "auto").lower()
DOCKER_SCRAPER_CONTAINER = os.environ.get("DOCKER_SCRAPER_CONTAINER", "myweb_scraper")
LOG_DIR = os.path.join(BASE_DIR, "logs")
SCRAPER_LOG_FILE = os.path.join(LOG_DIR, "scraper.log")


def use_docker_runtime():
    if RUNTIME == "docker":
        return True
    if RUNTIME == "systemd":
        return False
    return bool(DOCKER_SCRAPER_CONTAINER) and os.path.exists("/var/run/docker.sock")


def get_docker_client():
    try:
        import docker
        return docker.from_env()
    except Exception:
        return None


def get_docker_scraper_container():
    client = get_docker_client()
    if client is None:
        return None
    try:
        return client.containers.get(DOCKER_SCRAPER_CONTAINER)
    except Exception:
        return None


def get_docker_bot_process_info():
    container = get_docker_scraper_container()
    if container is None:
        return 0, "unknown", None
    if container.status != "running":
        return 0, "stopped", None

    started_raw = container.attrs.get("State", {}).get("StartedAt")
    if not started_raw:
        return 1, "unknown", None

    try:
        started = datetime.fromisoformat(started_raw.replace("Z", "+00:00"))
        elapsed = max(0, int((datetime.now(started.tzinfo) - started).total_seconds()))
    except ValueError:
        return 1, "unknown", None

    bot_uptime = format_duration(elapsed)
    bot_since = started.astimezone().strftime("%d/%m/%Y %H:%M:%S")
    return 1, bot_uptime, bot_since


def get_docker_service_status():
    instances, bot_uptime, bot_since = get_docker_bot_process_info()
    container = get_docker_scraper_container()
    if container is None:
        return {
            "available": True,
            "message": f"Container '{DOCKER_SCRAPER_CONTAINER}' not found",
            "active": False,
            "sub": "missing",
            "loaded": "docker",
            "bot_uptime": bot_uptime,
            "bot_since": bot_since,
            "status_output": f"docker container {DOCKER_SCRAPER_CONTAINER} not found",
            "instances": instances,
        }

    active = container.status == "running"
    return {
        "available": True,
        "message": "",
        "active": active,
        "sub": container.status,
        "loaded": "docker",
        "bot_uptime": bot_uptime,
        "bot_since": bot_since,
        "status_output": f"container={DOCKER_SCRAPER_CONTAINER}\nstatus={container.status}",
        "instances": instances,
        "service_since": container.attrs.get("State", {}).get("StartedAt"),
    }


def perform_docker_action(action):
    if action not in {"start", "stop", "restart"}:
        return False, f"Invalid action: {action}"

    container = get_docker_scraper_container()
    if container is None:
        return False, f"Container '{DOCKER_SCRAPER_CONTAINER}' not found"

    try:
        if action == "start":
            container.start()
        elif action == "stop":
            container.stop()
        else:
            container.restart()
    except Exception as exc:
        return False, str(exc)

    return True, f"{action} sent to container {DOCKER_SCRAPER_CONTAINER}"


def read_docker_scraper_logs(tail=200):
    container = get_docker_scraper_container()
    if container is None:
        return ""
    try:
        raw = container.logs(tail=tail)
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_site_name(url):
    if 'foxbet.gr/316026/to-dunato-simeio' in url:
        return 'foxbet-to_dynato'
    elif 'foxbet.gr/316014/to-stantar' in url:
        return 'foxbet-to_stantar'
    elif 'nostrabet.com/en/bet-of-the-day' in url:
        return 'nostra_bet_of_the_day'
    elif 'nostrabet.com/en/banker-of-the-day' in url:
        return 'notra_banker_of_the_day'
    elif 'kingbet.com.cy/to-dynato-simeio-imeras' in url:
        return 'kingbet-to_dynato'
    elif 'kingbet.com.cy/favori-imeras' in url:
        return 'kingbet-to_favori'
    elif 'kingbet.com.cy/to-stantar-tis-imeras' in url:
        return 'kingbet-to_stantar'

    parsed = urlparse(url)
    netloc = parsed.netloc
    if netloc.startswith('www.'):
        netloc = netloc[4:]
    site_name = netloc.split('.')[0]
    return site_name if site_name else 'unknown'


def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"Command not found: {command[0]}"


def get_service_status():
    if use_docker_runtime():
        return get_docker_service_status()

    instances, bot_uptime, bot_since = get_bot_process_info()
    if shutil_which("systemctl") is None:
        return {
            "available": False,
            "message": "systemctl not found",
            "active": instances > 0,
            "sub": instances > 0 and "running" or "stopped",
            "loaded": "process-only",
            "bot_uptime": bot_uptime,
            "bot_since": bot_since,
            "status_output": "Systemctl unavailable. Using process information instead.",
            "instances": instances,
        }

    code, stdout, stderr = run_command(["systemctl", "show", SERVICE_NAME, "--no-page", "-p", "ActiveState", "-p", "SubState", "-p", "LoadState", "-p", "ActiveEnterTimestamp", "-p", "ExecMainPID"])
    if code != 0:
        return {
            "available": True,
            "message": f"systemctl show failed ({code})",
            "active": False,
            "sub": "unknown",
            "loaded": "unknown",
            "bot_uptime": bot_uptime,
            "bot_since": bot_since,
            "status_output": stderr or stdout or "Systemctl service not found. Using process information instead.",
            "instances": instances,
        }

    status = {line.split("=", 1)[0]: line.split("=", 1)[1] for line in stdout.splitlines() if "=" in line}
    active = status.get("ActiveState", "unknown") == "active"
    service_since = status.get("ActiveEnterTimestamp")

    return {
        "available": True,
        "message": "",
        "active": active,
        "sub": status.get("SubState", "unknown"),
        "loaded": status.get("LoadState", "unknown"),
        "bot_uptime": bot_uptime,
        "bot_since": bot_since,
        "status_output": stdout,
        "instances": instances,
        "service_since": service_since,
    }


def format_site_alias(name):
    if not name:
        return name
    pretty = name.replace("_", " ").replace("-", " ")
    pretty = " ".join(pretty.split())
    return pretty


def get_sent_tips():
    if not os.path.exists(SENT_LOG_FILE):
        return {}

    try:
        with open(SENT_LOG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        return {}

    tips_by_site = {}

    for key, val in data.items():
        url = key.split("|", 1)[0]
        site = format_site_alias(extract_site_name(url))

        if isinstance(val, dict):
            tip_text = val.get("text", "")
        else:
            tip_text = val

        tips_by_site.setdefault(site, []).append({
            "tip": tip_text,
            "tip_key": key,
        })

    return tips_by_site


def format_duration(seconds):
    if seconds is None or seconds == "unknown":
        return "unknown"
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f"{days}d {hours:02}:{minutes:02}:{seconds:02}"
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_bot_process_info():
    code, stdout, stderr = run_command(["ps", "-eo", "etimes,cmd"])
    if code != 0 or not stdout:
        return 0, "unknown", None

    processes = []
    for line in stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2:
            continue
        etimes, cmd = parts
        if "main.py" in cmd and "status_web.py" not in cmd:
            try:
                elapsed = int(etimes)
            except ValueError:
                continue
            processes.append((elapsed, cmd))

    if not processes:
        return 0, "unknown", None

    instances = len(processes)
    longest = max(processes, key=lambda item: item[0])
    bot_uptime = format_duration(longest[0])
    bot_since = (datetime.now() - timedelta(seconds=longest[0])).strftime("%d/%m/%Y %H:%M:%S")
    return instances, bot_uptime, bot_since


def shutdown_server():
    raise KeyboardInterrupt


def perform_run_now():
    if use_docker_runtime():
        container = get_docker_scraper_container()
        if container is None:
            return False, f"Container '{DOCKER_SCRAPER_CONTAINER}' not found"
        try:
            container.exec_run(["python", "main.py"], detach=True)
        except Exception as exc:
            return False, str(exc)
        return True, "Triggered one-off scrape inside scraper container"

    try:
        subprocess.Popen(
            [sys.executable, "main.py"],
            cwd=BASE_DIR,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as exc:
        return False, str(exc)
    return True, "Triggered one-off scrape run"


def perform_action(action):
    if action == "restart_console":
        return True, "Console reload handled by UI"

    if action == "run_now":
        return perform_run_now()

    if use_docker_runtime():
        return perform_docker_action(action)

    if shutil_which("systemctl") is None:
        return False, "systemctl not available on this machine"

    if action not in {"start", "stop", "restart"}:
        return False, f"Invalid action: {action}"

    code, stdout, stderr = run_command(["sudo", "systemctl", action, SERVICE_NAME, "--no-pager"])
    success = code == 0
    result_text = stdout if stdout else stderr
    if not result_text:
        result_text = f"command exited with code {code}"
    return success, result_text


def shutil_which(name):
    from shutil import which
    return which(name)


class StatusHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type="text/html", extra_headers=None):
        self.send_response(status)
        self.send_header("Content-type", content_type)
        if extra_headers:
            for name, value in extra_headers.items():
                self.send_header(name, value)
        self.end_headers()

    def _json(self, payload, status=200):
        self._set_headers(status, "application/json")
        self.wfile.write(json.dumps(payload).encode("utf-8"))

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._serve_index()
        if parsed.path == "/manifest.json":
            return self._serve_manifest()
        if parsed.path == "/sw.js":
            return self._serve_sw()
        if parsed.path == "/api/status":
            return self._serve_status()
        if parsed.path == "/api/today":
            return self._serve_today()
        if parsed.path == "/api/favorites":
            return self._serve_favorites_get(parsed)
        if parsed.path == "/logs":
            return self._serve_logs()
        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/action":
            length = int(self.headers.get("Content-Length", 0))
            post_data = self.rfile.read(length).decode("utf-8")
            params = parse_qs(post_data)
            action = params.get("action", [""])[0]
            success, output = perform_action(action)
            self._json({"success": success, "action": action, "output": output})
            return
        if parsed.path == "/api/favorites":
            return self._serve_favorites_post()
        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    def do_DELETE(self):
        parsed = urlparse(self.path)
        if parsed.path == "/api/favorites":
            return self._serve_favorites_delete(parsed)
        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

    # ---- favorites/users ----

    def _serve_favorites_get(self, parsed):
        qs = parse_qs(parsed.query)
        user_name = (qs.get("user", [""])[0] or "").strip()
        if not user_name:
            return self._json({"error": "missing 'user' query param"}, 400)
        user = db.get_or_create_user(user_name)
        favorites = db.list_favorites(user["id"])
        self._json({"user": user, "favorites": favorites})

    def _read_json_body(self):
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length).decode("utf-8") if length else ""
        content_type = self.headers.get("Content-Type", "")
        if "application/json" in content_type:
            try:
                return json.loads(raw) if raw else {}
            except Exception:
                return {}
        # fallback: form-encoded
        parsed = parse_qs(raw)
        return {k: v[0] for k, v in parsed.items()}

    def _serve_favorites_post(self):
        body = self._read_json_body()
        user_name = (body.get("user") or "").strip()
        tip_key = (body.get("tip_key") or "").strip()
        if not user_name or not tip_key:
            return self._json({"error": "missing 'user' or 'tip_key'"}, 400)
        user = db.get_or_create_user(user_name)
        db.add_favorite(user["id"], tip_key, body.get("tip_text"), body.get("site"))
        self._json({"success": True, "user": user, "favorites": db.list_favorites(user["id"])})

    def _serve_favorites_delete(self, parsed):
        qs = parse_qs(parsed.query)
        user_name = (qs.get("user", [""])[0] or "").strip()
        tip_key = (qs.get("tip_key", [""])[0] or "").strip()
        if not user_name or not tip_key:
            return self._json({"error": "missing 'user' or 'tip_key'"}, 400)
        user = db.get_or_create_user(user_name)
        db.remove_favorite(user["id"], tip_key)
        self._json({"success": True, "user": user, "favorites": db.list_favorites(user["id"])})

    # ---- existing routes ----

    def _serve_status(self):
        status = get_service_status()
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(status).encode("utf-8"))

    def _serve_today(self):
        data = get_sent_tips()
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps({"tips_by_site": data}).encode("utf-8"))

    def _serve_logs(self):
        if os.path.exists(SCRAPER_LOG_FILE):
            with open(SCRAPER_LOG_FILE, "rb") as f:
                raw = f.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            if content.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
                return

        if use_docker_runtime():
            docker_logs = read_docker_scraper_logs()
            if docker_logs.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(docker_logs.encode("utf-8"))
                return

        log_path = os.path.join(BASE_DIR, "output.log")
        backup_path = os.path.join(BASE_DIR, "nohup.out")
        if os.path.exists(log_path):
            with open(log_path, "rb") as f:
                raw = f.read()
            content = None
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            if content.strip() and content.strip() != "nohup: ignoring input":
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
                return
        if os.path.exists(backup_path):
            with open(backup_path, "rb") as f:
                raw = f.read()
            try:
                content = raw.decode("utf-8")
            except UnicodeDecodeError:
                content = raw.decode("latin-1", errors="replace")
            if content.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(content.encode("utf-8"))
                return
        if shutil_which("journalctl"):
            code, stdout, stderr = run_command(["journalctl", "-u", SERVICE_NAME, "--no-pager", "-n", "200"])
            if code == 0 and stdout.strip():
                self._set_headers(200, "text/plain; charset=utf-8")
                self.wfile.write(stdout.encode("utf-8"))
                return
        self._set_headers(404, "text/plain; charset=utf-8")
        self.wfile.write(b"No usable log output found. Check output.log, nohup.out, or journalctl.")

    def _serve_manifest(self):
        manifest = {
            "name": "Tips Console",
            "short_name": "Tips",
            "start_url": "/",
            "display": "standalone",
            "background_color": "#0c0d16",
            "theme_color": "#0c0d16",
            "icons": [
                {
                    "src": "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='22' fill='%23dd4814'/%3E%3Ctext x='50' y='68' font-size='58' text-anchor='middle' fill='white'%3E%E2%9A%BD%3C/text%3E%3C/svg%3E",
                    "sizes": "192x192",
                    "type": "image/svg+xml",
                }
            ],
        }
        self._set_headers(200, "application/json")
        self.wfile.write(json.dumps(manifest).encode("utf-8"))

    def _serve_sw(self):
        sw_js = """
self.addEventListener('install', e => self.skipWaiting());
self.addEventListener('activate', e => self.clients.claim());
self.addEventListener('fetch', e => {
  e.respondWith(fetch(e.request).catch(() => new Response('Offline', { status: 503 })));
});
"""
        self._set_headers(200, "application/javascript")
        self.wfile.write(sw_js.encode("utf-8"))

    def _serve_index(self):
        self._set_headers(200, "text/html", {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })
        self.wfile.write(INDEX_HTML.replace("APP_VERSION_PLACEHOLDER", APP_VERSION).encode("utf-8"))

    def log_message(self, format, *args):
        return


INDEX_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate" />
  <meta http-equiv="Pragma" content="no-cache" />
  <meta http-equiv="Expires" content="0" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <link rel="manifest" href="/manifest.json">
  <meta name="theme-color" content="#0c0d16">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <title>Tips Console</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0c0d16;
      --panel: #131424;
      --panel2: #16161e;
      --card: #1c1c27;
      --border: #272a47;
      --border2: #252533;
      --text: #f3f2ee;
      --muted: #a8a29e;
      --muted2: #7a8699;
      --accent: #f59e0b;
      --accent2: #dd4814;
      --win: #34d399;
      --loss: #fb7185;
      --info: #38bdf8;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; min-height: 100vh; background: var(--bg); color: var(--text);
      font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }
    .wrap { max-width: 1100px; margin: 0 auto; padding: 28px 20px 60px; }
    header {
      display: flex; align-items: center; justify-content: space-between; gap: 12px;
      margin-bottom: 22px; flex-wrap: wrap;
    }
    .brand { display: flex; align-items: center; gap: 12px; }
    .logo {
      width: 40px; height: 40px; border-radius: 12px;
      background: linear-gradient(135deg, #fbbf24, #dd4814);
      display: flex; align-items: center; justify-content: center;
      font-weight: 800; color: #1a1300; font-size: 18px;
    }
    .brand h1 { margin: 0; font-size: 1.15rem; font-weight: 800; letter-spacing: -0.02em; }
    .brand p { margin: 0; font-size: 0.72rem; color: var(--muted2); display: flex; align-items: center; gap: 6px; }
    .dot { width: 7px; height: 7px; border-radius: 50%; background: var(--win); display: inline-block; }
    .dot.off { background: var(--loss); }
    .btn {
      border: none; border-radius: 10px; padding: 9px 14px; font-weight: 700; font-size: 0.78rem;
      cursor: pointer; transition: all .15s ease; font-family: inherit;
    }
    .btn-accent { background: linear-gradient(135deg, #f59e0b, #dd4814); color: #1a1300; }
    .btn-secondary { background: var(--card); color: var(--text); border: 1px solid var(--border2); }
    .btn:hover { opacity: 0.85; transform: translateY(-1px); }
    .btn-row { display: flex; gap: 8px; flex-wrap: wrap; }

    .card {
      background: var(--panel); border: 1px solid var(--border); border-radius: 20px;
      padding: 20px; margin-bottom: 18px;
    }
    .card h2 {
      margin: 0 0 14px; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.05em;
      color: var(--muted2); font-weight: 700;
    }

    .stat-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: 12px; }
    .stat { background: var(--card); border: 1px solid var(--border2); border-radius: 14px; padding: 14px; }
    .stat-label { font-size: 0.68rem; text-transform: uppercase; color: var(--muted2); letter-spacing: 0.04em; margin-bottom: 6px; }
    .stat-value { font-family: 'JetBrains Mono', monospace; font-size: 1.15rem; font-weight: 700; }
    .stat-value.on { color: var(--win); }
    .stat-value.off { color: var(--loss); }

    .action-result { margin-top: 12px; font-size: 0.75rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; }

    .toolbar { display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 14px; align-items: center; justify-content: space-between; }
    .search-box { position: relative; flex: 1; min-width: 200px; }
    .search-box input {
      width: 100%; padding: 9px 12px 9px 34px; border-radius: 10px; background: #0a0b14;
      border: 1px solid var(--border); color: var(--text); font-size: 0.8rem; font-family: inherit;
    }
    .search-box input:focus { outline: none; border-color: var(--accent); }
    .search-box::before {
      content: "⌕"; position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
      color: var(--muted2); font-size: 0.9rem;
    }
    .chips { display: flex; gap: 6px; flex-wrap: wrap; }
    .chip {
      padding: 6px 12px; border-radius: 10px; font-size: 0.72rem; font-weight: 700;
      background: var(--card); color: var(--muted); border: 1px solid var(--border2); cursor: pointer;
    }
    .chip.active { background: var(--accent); color: #1a1300; border-color: var(--accent); }

    .tip-row {
      display: flex; align-items: flex-start; gap: 12px; padding: 14px; border-radius: 14px;
      background: var(--card); border: 1px solid var(--border2); margin-bottom: 10px;
    }
    .tip-badge {
      flex-shrink: 0; padding: 4px 10px; border-radius: 8px; font-size: 0.68rem; font-weight: 800;
      text-transform: uppercase; letter-spacing: 0.03em; white-space: nowrap;
    }
    .tip-body { flex: 1; min-width: 0; }
    .tip-text { font-family: 'JetBrains Mono', monospace; font-size: 0.8rem; white-space: pre-wrap; color: var(--text); line-height: 1.5; }
    .tip-fav {
      flex-shrink: 0; background: none; border: 1px solid var(--border2); border-radius: 10px;
      width: 34px; height: 34px; font-size: 1rem; cursor: pointer; color: var(--muted2);
      display: flex; align-items: center; justify-content: center;
    }
    .tip-fav.active { color: var(--accent); border-color: var(--accent); background: rgba(245,158,11,0.1); }
    .empty { color: var(--muted2); font-size: 0.8rem; text-align: center; padding: 30px 0; }

    pre.raw {
      background: #090a10; color: #d6e4ff; padding: 14px; border-radius: 12px; overflow: auto;
      font-family: 'JetBrains Mono', monospace; font-size: 0.72rem; border: 1px solid var(--border2);
      max-height: 240px;
    }

    .modal-overlay {
      display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.7);
      z-index: 50; align-items: center; justify-content: center; padding: 20px;
    }
    .modal-overlay.open { display: flex; }
    .modal-box {
      background: var(--panel); border: 1px solid var(--border); border-radius: 18px;
      width: 100%; max-width: 800px; max-height: 80vh; display: flex; flex-direction: column; overflow: hidden;
    }
    .modal-head {
      display: flex; align-items: center; justify-content: space-between; padding: 14px 18px;
      border-bottom: 1px solid var(--border2);
    }
    .modal-head h3 { margin: 0; font-size: 0.9rem; font-weight: 700; }
    .modal-close { background: none; border: none; color: var(--muted); font-size: 1.1rem; cursor: pointer; }
    .modal-body { padding: 14px 18px; overflow: auto; }
    .modal-body pre { margin: 0; max-height: none; }
    .modal-overlay { padding: 0; }
    .modal-box { max-width: 100%; max-height: 100vh; height: 100vh; border-radius: 0; }
    .modal-body { flex: 1; }
    .version-tag { font-size: 0.62rem; color: var(--muted2); font-family: 'JetBrains Mono', monospace; margin-left: 8px; }

    @media (max-width: 640px) {
      .modal-overlay { padding: 0; }
      .modal-box { max-width: 100%; max-height: 100vh; height: 100vh; border-radius: 0; }
      .modal-body { flex: 1; }
    }
  </style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="brand">
        <div class="logo">⚽</div>
        <div>
          <h1>Tips Console <span class="version-tag">vAPP_VERSION_PLACEHOLDER</span></h1>
          <p><span class="dot" id="brand-dot"></span> <span id="brand-status">connecting...</span></p>
        </div>
      </div>
      <div class="btn-row">
        <button class="btn btn-accent" id="run-now-btn" onclick="sendAction('run_now')">▶ Run Scrape Now</button>
        <button class="btn btn-secondary" onclick="openLogs()">☰ Logs</button>
      </div>
    </header>

    <div class="card">
      <h2>Today's Tips <span id="tip-count" style="color:var(--accent);"></span></h2>
      <div class="toolbar">
        <div class="search-box"><input id="search-input" placeholder="Search event or tipster..." oninput="renderTips()"/></div>
        <div class="chips" id="site-chips"></div>
      </div>
      <div id="tips-list"></div>
    </div>

    <div class="card">
      <h2>Diagnostic Output</h2>
      <pre class="raw" id="raw-output">loading...</pre>
    </div>

    <div class="card">
      <h2>Service Status</h2>
      <div class="stat-grid">
        <div class="stat"><div class="stat-label">Active</div><div class="stat-value" id="active-state">-</div></div>
        <div class="stat"><div class="stat-label">Sub-state</div><div class="stat-value" id="sub-state">-</div></div>
        <div class="stat"><div class="stat-label">Uptime</div><div class="stat-value" id="uptime">-</div></div>
        <div class="stat"><div class="stat-label">Instances</div><div class="stat-value" id="instances">-</div></div>
      </div>
      <div class="btn-row" style="margin-top:16px;">
        <button class="btn btn-secondary" onclick="sendAction('start')">Start</button>
        <button class="btn btn-secondary" onclick="sendAction('stop')">Stop</button>
        <button class="btn btn-secondary" onclick="sendAction('restart')">Restart</button>
      </div>
      <div class="action-result" id="action-result">Ready.</div>
    </div>
  </div>

  <div class="modal-overlay" id="logs-modal">
    <div class="modal-box">
      <div class="modal-head">
        <h3>Scraper Logs</h3>
        <button class="modal-close" onclick="closeLogs()">✕</button>
      </div>
      <div class="modal-body"><pre id="logs-content">loading...</pre></div>
    </div>
  </div>

  <script>
    const FAV_USER = 'default';
    let favoriteKeys = new Set();
    let tipsBySite = {};
    let activeSite = 'all';

    const SITE_COLORS = ['#f59e0b', '#38bdf8', '#34d399', '#a78bfa', '#fb7185', '#818cf8'];
    function colorFor(site) {
      let hash = 0;
      for (let i = 0; i < site.length; i++) hash = site.charCodeAt(i) + ((hash << 5) - hash);
      return SITE_COLORS[Math.abs(hash) % SITE_COLORS.length];
    }

    async function fetchStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('active-state').textContent = data.active ? 'active' : 'inactive';
      document.getElementById('active-state').className = 'stat-value ' + (data.active ? 'on' : 'off');
      document.getElementById('sub-state').textContent = data.sub || 'unknown';
      document.getElementById('uptime').textContent = data.bot_uptime || 'unknown';
      document.getElementById('instances').textContent = data.instances || 0;
      document.getElementById('raw-output').textContent = data.status_output || 'no output';
      document.getElementById('brand-dot').className = 'dot' + (data.active ? '' : ' off');
      document.getElementById('brand-status').textContent = data.active ? 'Bot running' : 'Bot stopped';
    }

    async function fetchFavorites() {
      try {
        const res = await fetch('/api/favorites?user=' + encodeURIComponent(FAV_USER));
        const data = await res.json();
        favoriteKeys = new Set((data.favorites || []).map(f => f.tip_key));
      } catch (err) {
        favoriteKeys = new Set();
      }
    }

    async function toggleFavorite(tipKey, tipText, site) {
      if (favoriteKeys.has(tipKey)) {
        await fetch('/api/favorites?user=' + encodeURIComponent(FAV_USER) + '&tip_key=' + encodeURIComponent(tipKey), { method: 'DELETE' });
      } else {
        await fetch('/api/favorites', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user: FAV_USER, tip_key: tipKey, tip_text: tipText, site: site })
        });
      }
      await fetchFavorites();
      renderTips();
    }

    async function fetchTips() {
      const res = await fetch('/api/today');
      const data = await res.json();
      tipsBySite = data.tips_by_site || {};
      renderChips();
      renderTips();
    }

    function renderChips() {
      const container = document.getElementById('site-chips');
      const sites = Object.keys(tipsBySite);
      let html = `<div class="chip ${activeSite === 'all' ? 'active' : ''}" onclick="setSite('all')">All</div>`;
      sites.forEach(site => {
        html += `<div class="chip ${activeSite === site ? 'active' : ''}" onclick="setSite('${site.replace(/'/g, "\\'")}')">${site}</div>`;
      });
      container.innerHTML = html;
    }

    function setSite(site) {
      activeSite = site;
      renderChips();
      renderTips();
    }

    function renderTips() {
      const search = (document.getElementById('search-input').value || '').toLowerCase();
      const list = document.getElementById('tips-list');
      let rows = [];
      for (const [site, items] of Object.entries(tipsBySite)) {
        if (activeSite !== 'all' && site !== activeSite) continue;
        items.forEach(item => {
          const tipText = (item && typeof item === 'object') ? (item.tip || '') : (item || '');
          const tipKey = (item && typeof item === 'object') ? (item.tip_key || '') : '';
          if (search && !tipText.toLowerCase().includes(search) && !site.toLowerCase().includes(search)) return;
          rows.push({ site, tipText, tipKey });
        });
      }
      document.getElementById('tip-count').textContent = rows.length ? `(${rows.length})` : '';
      if (!rows.length) {
        list.innerHTML = '<div class="empty">No tips match right now.</div>';
        return;
      }
      list.innerHTML = rows.map(row => {
        const isFav = favoriteKeys.has(row.tipKey);
        const color = colorFor(row.site);
        const label = row.site.replace(/[_-]/g, ' ');
        return `
          <div class="tip-row">
            <span class="tip-badge" style="background:${color}22; color:${color}; border:1px solid ${color}55;">${label}</span>
            <div class="tip-body"><div class="tip-text">${row.tipText.replace(/</g, '&lt;')}</div></div>
            <button class="tip-fav ${isFav ? 'active' : ''}" data-key="${row.tipKey}" data-site="${row.site}">${isFav ? '★' : '☆'}</button>
          </div>
        `;
      }).join('');
      list.querySelectorAll('.tip-fav').forEach((btn, idx) => {
        const row = rows[idx];
        btn.onclick = () => toggleFavorite(row.tipKey, row.tipText, row.site);
      });
    }

    async function openLogs() {
      const modal = document.getElementById('logs-modal');
      const content = document.getElementById('logs-content');
      modal.classList.add('open');
      content.textContent = 'loading...';
      try {
        const res = await fetch('/logs?ts=' + Date.now());
        content.textContent = await res.text();
      } catch (err) {
        content.textContent = 'Failed to load logs: ' + err;
      }
    }

    function closeLogs() {
      document.getElementById('logs-modal').classList.remove('open');
    }

    async function sendAction(action) {
      document.getElementById('action-result').textContent = 'Sending ' + action + '...';
      const res = await fetch('/api/action', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `action=${action}`
      });
      const data = await res.json();
      document.getElementById('action-result').textContent = `${data.success ? 'OK' : 'ERROR'}: ${data.output}`;
      await fetchStatus();
    }

    async function refreshAll() {
      await fetchStatus();
      await fetchFavorites();
      await fetchTips();
    }

    refreshAll();
    setInterval(refreshAll, 6000);

    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.register('/sw.js').catch(() => {});
    }
  </script>
</body>
</html>
"""


def run(port=8000):
    server_address = ("0.0.0.0", port)
    try:
        httpd = ThreadingHTTPServer(server_address, StatusHandler)
    except OSError as exc:
        if exc.errno == 98:
            print(f"ERROR: port {port} is already in use. Start with a different port, e.g. python3 status_web.py 8001")
            return
        raise
    print(f"Serving bot status on http://0.0.0.0:{port}")
    httpd.should_restart = False
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down server")
    finally:
        httpd.server_close()

    if getattr(httpd, "should_restart", False):
        print("Restarting status web console...")
        os.execv(sys.executable, [sys.executable, __file__, str(port)])


if __name__ == "__main__":
    port = 8001
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run(port)
