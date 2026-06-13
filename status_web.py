import json
import os
import sys
import subprocess
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

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

    for key, tip_text in data.items():
        url = key.split("|", 1)[0]
        site = format_site_alias(extract_site_name(url))
        tips_by_site.setdefault(site, []).append({
            "tip": tip_text,
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


def perform_action(action):
    if action == "restart_console":
        return True, "Console reload handled by UI"

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

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/":
            return self._serve_index()
        if parsed.path == "/api/status":
            return self._serve_status()
        if parsed.path == "/api/today":
            return self._serve_today()
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
            self._set_headers(200, "application/json")
            self.wfile.write(json.dumps({"success": success, "action": action, "output": output}).encode("utf-8"))
            return
        self._set_headers(404, "application/json")
        self.wfile.write(json.dumps({"error": "not found"}).encode("utf-8"))

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

    def _serve_index(self):
        self._set_headers(200, "text/html", {
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        })
        self.wfile.write(INDEX_HTML.encode("utf-8"))

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
  <title>Bot Status</title>
  <style>
    body { font-family: Arial, sans-serif; margin: 24px; background:#f7f8fb; color:#222; }
    h1 { margin-bottom: 8px; }
    .card { background: #fff; border: 1px solid #d9dee7; border-radius: 10px; padding: 18px; margin-bottom: 18px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
    button { margin-right: 10px; padding: 10px 14px; border:none; border-radius: 6px; cursor:pointer; font-weight: 600; }
    .btn-start { background:#2f9d27; color:#fff; }
    .btn-stop { background:#d6392e; color:#fff; }
    .btn-restart { background:#1677ff; color:#fff; }
    .status { font-size: 1rem; margin-top: 10px; }
    .site { margin-bottom: 14px; }
    pre { background:#0f172a; color:#d6e4ff; padding:12px; border-radius:8px; overflow:auto; }
  </style>
</head>
<body>
  <h1>Bot Status Dashboard</h1>
  <div class="card">
    <div><strong>Service:</strong> <span id="service-name">myweb_scraper</span></div>
    <div class="status"><strong>Active:</strong> <span id="active-state">loading...</span></div>
    <div class="status"><strong>Sub-state:</strong> <span id="sub-state">loading...</span></div>
    <div class="status"><strong>Loaded:</strong> <span id="loaded-state">loading...</span></div>
    <div class="status"><strong>Bot uptime:</strong> <span id="uptime">loading...</span></div>
    <div class="status"><strong>Started at:</strong> <span id="since">loading...</span></div>
    <div class="status"><strong>Systemctl available:</strong> <span id="systemctl-available">loading...</span></div>
    <div class="status"><strong>Instances:</strong> <span id="instances">loading...</span></div>
    <div style="margin-top:16px;">
      <button class="btn-start" onclick="sendAction('start')">Start</button>
      <button class="btn-stop" onclick="sendAction('stop')">Stop</button>
      <button class="btn-restart" onclick="sendAction('restart')">Restart</button>
      <button class="btn-restart" onclick="sendAction('restart_console')">Restart Console</button>
      <button class="btn-restart" onclick="openLogs()">Open Logs</button>
    </div>
    <div class="status">Controls the <strong>myweb_scraper</strong> service/process, not the status page itself.</div>
    <div class="status"><strong>Last action:</strong> <span id="action-result">none</span></div>
  </div>

  <div class="card">
    <h2>Today's Sent Tips</h2>
    <div><strong>Date:</strong> <span id="today-date">loading...</span></div>
    <table id="tips-table" style="width:100%; border-collapse: collapse; margin-top: 12px;">
      <thead>
        <tr>
          <th style="text-align:left; padding: 8px; border-bottom: 1px solid #d9dee7;">Tipster</th>
          <th style="text-align:left; padding: 8px; border-bottom: 1px solid #d9dee7;">Tip</th>
        </tr>
      </thead>
      <tbody id="tips-body"></tbody>
    </table>
    <div id="no-tips" style="margin-top:12px; color:#555;"></div>
  </div>

  <div class="card">
    <h2>Service Details</h2>
    <div class="status">Raw diagnostic output from the myweb_scraper service/process.</div>
    <pre id="raw-output">loading...</pre>
  </div>

  <script>
    async function fetchStatus() {
      const res = await fetch('/api/status');
      const data = await res.json();
      document.getElementById('active-state').textContent = data.active ? 'active' : 'inactive';
      document.getElementById('sub-state').textContent = data.sub || 'unknown';
      document.getElementById('loaded-state').textContent = data.loaded || 'unknown';
      document.getElementById('uptime').textContent = data.bot_uptime || 'unknown';
      document.getElementById('since').textContent = data.bot_since || 'unknown';
      document.getElementById('systemctl-available').textContent = data.available ? 'yes' : 'no';
      document.getElementById('raw-output').textContent = data.status_output || 'no output';
      document.getElementById('instances').textContent = data.instances || 0;
    }

    async function fetchTips() {
      const res = await fetch('/api/today');
      const data = await res.json();
      const body = document.getElementById('tips-body');
      const noTips = document.getElementById('no-tips');
      body.innerHTML = '';
      const tips = data.tips_by_site || {};
      const date = new Date();
      document.getElementById('today-date').textContent = `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(2, '0')}/${date.getFullYear()}`;
      const rows = [];
      for (const [site, items] of Object.entries(tips)) {
        items.forEach(item => {
          rows.push({ site: site.replace(/[_-]/g, ' ').replace(/\s+/g, ' ').trim(), tip: item.tip });
        });
      }
      if (!rows.length) {
        noTips.textContent = 'No tips have been stored for today yet.';
        return;
      }
      noTips.textContent = '';
      rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
          <td style="padding: 8px; border-bottom: 1px solid #f0f2f7;">${row.site}</td>
          <td style="padding: 8px; border-bottom: 1px solid #f0f2f7;">${row.tip}</td>
        `;
        body.appendChild(tr);
      });
    }

    function openLogs() {
      window.open('/logs?ts=' + Date.now(), '_blank');
    }

    async function sendAction(action) {
      if (action === 'restart_console') {
        document.getElementById('action-result').textContent = 'Reloading console...';
        window.location.reload();
        return;
      }
      document.getElementById('action-result').textContent = 'waiting...';
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
      await fetchTips();
    }

    refreshAll();
    setInterval(refreshAll, 5000);
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
