import json
import os
import shutil
import subprocess
import sys
from datetime import timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HOME_HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>George's Server</title>
  <style>
    :root {
      --bg: #0f0f10;
      --panel: #1f1f22;
      --surface: #1f1f22;
      --text: #f3f2ee;
      --muted: #a8a29e;
      --accent: #dd4814;
      --accent-soft: rgba(221,72,20,0.18);
      --border: rgba(255,255,255,0.08);
    }
    * { box-sizing: border-box; }
    body { margin: 0; min-height: 100vh; background: radial-gradient(circle at 20% 20%, rgba(221,72,20,0.16), transparent 32%), #0c0c0f; color: var(--text); font-family: Inter, system-ui, sans-serif; }
    .container { max-width: 1160px; margin: 0 auto; padding: 40px 30px; display: grid; gap: 28px; }
    .hero { padding: 48px 42px; border-radius: 34px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); display: grid; gap: 24px; justify-items: center; text-align: center; }
    .hero .logo { width: 92px; height: 92px; display: grid; place-items: center; border-radius: 26px; background: linear-gradient(135deg, #ff8c42, #dd4814); box-shadow: 0 24px 50px rgba(221,72,20,0.2); }
    .hero h1 { margin: 0; font-size: clamp(3.2rem, 5.6vw, 4.8rem); letter-spacing: -0.05em; line-height: 0.92; }
    .hero p { margin: 0; max-width: 760px; color: var(--muted); font-size: 1.05rem; }
    .panel-grid { display: grid; gap: 22px; grid-template-columns: 2fr 1fr; }
    .panel { border-radius: 28px; border: 1px solid var(--border); background: rgba(255,255,255,0.04); padding: 28px; }
    .panel h2 { margin-top: 0; font-size: 1.2rem; }
    .panel p { margin: 0; color: var(--muted); line-height: 1.75; }
    .button-row { display: grid; gap: 14px; margin-top: 20px; }
    .button { border: none; border-radius: 16px; padding: 14px 16px; font-weight: 700; cursor: pointer; background: var(--accent); color: #fff; transition: transform .16s ease; }
    .button:hover { transform: translateY(-2px); background: #b23a11; }
    .button.secondary { background: rgba(255,255,255,0.08); color: var(--text); }
    .bookmarks { display: grid; gap: 12px; margin-top: 18px; }
    .bookmark { display: flex; align-items: center; justify-content: space-between; padding: 16px 18px; border-radius: 18px; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); color: var(--text); text-decoration: none; }
    .bookmark span { color: var(--muted); }
    .bookmark-buttons { display: flex; gap: 10px; }
    .bookmark-button { border: none; background: rgba(255,255,255,0.08); color: var(--text); padding: 8px 12px; border-radius: 12px; cursor: pointer; transition: transform .16s ease; }
    .bookmark-button:hover { transform: translateY(-1px); background: rgba(255,255,255,0.12); }
    .stats { display: grid; gap: 14px; margin-top: 18px; }
    .stat { padding: 18px; border-radius: 22px; background: rgba(255,255,255,0.04); border: 1px solid var(--border); }
    .stat strong { display: block; font-size: 1.05rem; margin-bottom: 5px; }
    .stat small { color: var(--muted); }
    .status-line { margin-top: 12px; color: var(--muted); font-size: 0.95rem; }
  </style>
</head>
<body>
  <div class="container">
    <section class="hero">
      <div class="logo" aria-hidden="true">
        <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" fill="#fff"><circle cx="50" cy="50" r="50" opacity="0.16"/><path d="M54.4 34.5a7.8 7.8 0 1 1-10.8 0 7.8 7.8 0 0 1 10.8 0Zm18.7 3.1a5.2 5.2 0 1 0-7.4 7.3 5.2 5.2 0 0 0 7.4-7.3ZM30 40.8a5.2 5.2 0 1 0 7.4 7.3 5.2 5.2 0 0 0-7.4-7.3Zm47.9 29.4a5.2 5.2 0 1 0-7.4 7.3 5.2 5.2 0 0 0 7.4-7.3Zm-34.1 9.5a5.2 5.2 0 1 0-7.4 7.3 5.2 5.2 0 0 0 7.4-7.3Z"/></svg>
      </div>
      <h1>George's Server</h1>
      <p>Refined server homepage concept with console bookmarks, a clear action panel, and lightweight live status cards.</p>
    </section>

    <div class="panel-grid">
      <section class="panel">
        <h2>Navigation</h2>
        <div class="bookmarks" id="bookmark-list">
          <div class="bookmark" style="justify-content: center; color: var(--muted);">No bookmarks added yet.</div>
        </div>
        <div class="button-row" style="margin-top: 18px;">
          <button class="button secondary" onclick="addBookmark()">Add Bookmark</button>
        </div>
      </section>

      <section class="panel">
        <h2>Controls</h2>
        <div class="button-row">
          <button class="button" onclick="rebootServer()">Reboot Server</button>
          <button class="button secondary" onclick="refreshPage()">Refresh Page</button>
          <button class="button" onclick="restartHomepage()">Restart Homepage</button>
        </div>
        <p class="small">Reboot sends a reboot command to the server. Restart homepage reloads the app process.</p>
        <div class="status-line" id="action-status">Ready</div>
      </section>
    </div>

    <section class="panel">
      <h2>Live stats</h2>
      <div class="stats">
        <div class="stat"><strong>Uptime</strong><small id="stat-uptime">Loading…</small></div>
        <div class="stat"><strong>Load average</strong><small id="stat-load">Loading…</small></div>
        <div class="stat"><strong>Memory</strong><small id="stat-memory">Loading…</small></div>
        <div class="stat"><strong>Disk</strong><small id="stat-disk">Loading…</small></div>
      </div>
      <div class="status-line" id="stats-status">Fetching stats…</div>
    </section>
  </div>
  <script>
    const BOOKMARK_KEY = 'george_server_bookmarks';
    let bookmarks = [];

    function renderBookmarks() {
      const list = document.getElementById('bookmark-list');
      list.innerHTML = '';
      if (!bookmarks.length) {
        const placeholder = document.createElement('div');
        placeholder.className = 'bookmark';
        placeholder.style.justifyContent = 'center';
        placeholder.style.color = 'var(--muted)';
        placeholder.textContent = 'No bookmarks added yet.';
        list.appendChild(placeholder);
        return;
      }
      bookmarks.forEach((bookmark, index) => {
        const item = document.createElement('div');
        item.className = 'bookmark';
        const link = document.createElement('a');
        link.href = bookmark.url;
        link.target = '_blank';
        link.rel = 'noopener';
        link.style.color = 'inherit';
        link.style.textDecoration = 'none';
        link.innerHTML = `<span>${bookmark.title}</span>`;
        const controls = document.createElement('div');
        controls.className = 'bookmark-buttons';
        const edit = document.createElement('button');
        edit.className = 'bookmark-button';
        edit.textContent = 'Edit';
        edit.onclick = () => editBookmark(index);
        const remove = document.createElement('button');
        remove.className = 'bookmark-button';
        remove.textContent = 'Remove';
        remove.onclick = () => removeBookmark(index);
        controls.appendChild(edit);
        controls.appendChild(remove);
        item.appendChild(link);
        item.appendChild(controls);
        list.appendChild(item);
      });
    }

    function loadBookmarks() {
      try {
        const raw = localStorage.getItem(BOOKMARK_KEY);
        bookmarks = raw ? JSON.parse(raw) : [];
      } catch (err) {
        bookmarks = [];
      }
      renderBookmarks();
    }

    function saveBookmarks() {
      localStorage.setItem(BOOKMARK_KEY, JSON.stringify(bookmarks));
    }

    function addBookmark() {
      const url = window.prompt('Bookmark URL', 'http://');
      if (!url || !url.trim()) return;
      const title = window.prompt('Bookmark title', 'New bookmark');
      if (!title || !title.trim()) return;
      bookmarks.push({ title: title.trim(), url: url.trim() });
      saveBookmarks();
      renderBookmarks();
    }

    function editBookmark(index) {
      const bookmark = bookmarks[index];
      const title = window.prompt('Bookmark title', bookmark.title);
      if (!title || !title.trim()) return;
      const url = window.prompt('Bookmark URL', bookmark.url);
      if (!url || !url.trim()) return;
      bookmarks[index] = { title: title.trim(), url: url.trim() };
      saveBookmarks();
      renderBookmarks();
    }

    function removeBookmark(index) {
      if (!confirm('Remove this bookmark?')) return;
      bookmarks.splice(index, 1);
      saveBookmarks();
      renderBookmarks();
    }

    async function fetchStats() {
      const statusLine = document.getElementById('stats-status');
      try {
        const res = await fetch('/api/stats');
        const data = await res.json();
        document.getElementById('stat-uptime').textContent = data.uptime;
        document.getElementById('stat-load').textContent = data.load;
        document.getElementById('stat-memory').textContent = data.memory;
        document.getElementById('stat-disk').textContent = data.disk;
        statusLine.textContent = 'Stats live';
      } catch (err) {
        statusLine.textContent = 'Failed to fetch stats';
      }
    }

    async function sendAction(action) {
      const status = document.getElementById('action-status');
      status.textContent = 'Sending ' + action + '...';
      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
          body: `action=${encodeURIComponent(action)}`
        });
        const data = await res.json();
        status.textContent = data.success ? `OK: ${data.message}` : `ERROR: ${data.message}`;
      } catch (err) {
        status.textContent = 'Action failed';
      }
    }

    function refreshPage() { location.reload(); }
    function rebootServer() { if (confirm('Reboot the server now?')) sendAction('reboot_server'); }
    function restartHomepage() { if (confirm('Restart homepage application?')) sendAction('restart_homepage'); }

    loadBookmarks();
    fetchStats();
    setInterval(fetchStats, 10000);
  </script>
</body>
</html>
"""

SERVICE_NAME = 'home_page'


def run_command(command):
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except FileNotFoundError:
        return 127, '', f'Command not found: {command[0]}'


def shutil_which(name):
    return shutil.which(name)


def format_duration(seconds):
    seconds = int(seconds)
    days, seconds = divmod(seconds, 86400)
    hours, seconds = divmod(seconds, 3600)
    minutes, seconds = divmod(seconds, 60)
    if days:
        return f'{days}d {hours:02}:{minutes:02}:{seconds:02}'
    return f'{hours:02}:{minutes:02}:{seconds:02}'


def get_system_stats():
    uptime = 'unknown'
    load = 'unknown'
    memory = 'unknown'
    disk = 'unknown'

    if os.path.exists('/proc/uptime'):
        try:
            with open('/proc/uptime', 'r', encoding='utf-8') as f:
                uptime_seconds = float(f.read().split()[0])
            uptime = format_duration(int(uptime_seconds))
        except Exception:
            pass

    try:
        load1, load5, load15 = os.getloadavg()
        load = f'{load1:.2f}, {load5:.2f}, {load15:.2f}'
    except Exception:
        pass

    if os.path.exists('/proc/meminfo'):
        try:
            meminfo = {}
            with open('/proc/meminfo', 'r', encoding='utf-8') as f:
                for line in f:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        meminfo[key.strip()] = int(value.strip().split()[0])
            total = meminfo.get('MemTotal')
            free = meminfo.get('MemAvailable', meminfo.get('MemFree'))
            if total and free:
                used = total - free
                memory = f'{used // 1024}MB / {total // 1024}MB'
        except Exception:
            pass

    try:
        usage = shutil.disk_usage('/')
        disk = f'{usage.used // (1024**3)}GB / {usage.total // (1024**3)}GB'
    except Exception:
        pass

    return {
        'uptime': uptime,
        'load': load,
        'memory': memory,
        'disk': disk,
    }


def perform_action(action, server=None):
    if action == 'restart_homepage':
        if server is not None:
            server.should_restart = True
            server.shutdown()
            return True, 'Homepage restart initiated'
        return False, 'Server handle unavailable'

    if action == 'reboot_server':
        if shutil_which('systemctl'):
            code, out, err = run_command(['sudo', 'systemctl', 'reboot'])
        else:
            code, out, err = run_command(['sudo', 'reboot'])
        if code == 0:
            return True, 'Reboot command sent'
        return False, err or out or f'reboot failed ({code})'

    return False, f'Unknown action: {action}'


class HomeHandler(BaseHTTPRequestHandler):
    def _set_headers(self, status=200, content_type='text/html'):
        self.send_response(status)
        self.send_header('Content-type', content_type)
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == '/':
            self._set_headers(200)
            self.wfile.write(HOME_HTML.encode('utf-8'))
            return
        if parsed.path == '/api/stats':
            stats = get_system_stats()
            self._set_headers(200, 'application/json')
            self.wfile.write(json.dumps(stats).encode('utf-8'))
            return
        self._set_headers(404, 'application/json')
        self.wfile.write(json.dumps({'error': 'not found'}).encode('utf-8'))

    def do_POST(self):
        parsed = urlparse(self.path)
        if parsed.path != '/api/action':
            self._set_headers(404, 'application/json')
            self.wfile.write(json.dumps({'error': 'not found'}).encode('utf-8'))
            return
        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        params = parse_qs(body)
        action = params.get('action', [''])[0]
        success, message = perform_action(action, server=self.server)
        self._set_headers(200, 'application/json')
        self.wfile.write(json.dumps({'success': success, 'message': message}).encode('utf-8'))

    def log_message(self, format, *args):
        return


def run(port=6969):
    server_address = ('0.0.0.0', port)
    httpd = ThreadingHTTPServer(server_address, HomeHandler)
    httpd.should_restart = False
    print(f'Serving homepage on http://0.0.0.0:{port}')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down homepage server')
    finally:
        httpd.server_close()

    if getattr(httpd, 'should_restart', False):
        print('Restarting homepage...')
        os.execv(sys.executable, [sys.executable, __file__, str(port)])


if __name__ == '__main__':
    port = 6969
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run(port)
