"""Loopback preview with an optional real AWS open-source demo API."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import argparse
import json
import sys
import os
import socket
from threading import Lock
from urllib.parse import urlsplit, parse_qsl

ROOT = Path(__file__).resolve().parent
if (ROOT / '.env').is_file():
    for line in (ROOT / '.env').read_text(encoding='utf-8').splitlines():
        if line.strip() and not line.lstrip().startswith('#') and '=' in line:
            name, value = line.split('=', 1)
            if name.strip() in {'OPENAQ_API_KEY', 'WAQI_API_KEY', 'OPENWEATHER_API_KEY', 'ALERT_DELIVERY_MODE', 'VAPID_PUBLIC_KEY', 'VAPID_PRIVATE_KEY', 'VAPID_SUBJECT', 'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN', 'TWILIO_FROM'}:
                os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))
sys.path.insert(0, str(ROOT / 'backend' / 'vendor'))
try:
    from backend.functions.community_api import handler as api_handler
except ModuleNotFoundError as error:
    if error.name != 'aws_lambda_powertools':
        raise
    api_handler = None
API_LOCK = Lock()

class PreviewServer(ThreadingHTTPServer):
    allow_reuse_address = False
    def server_bind(self):
        if hasattr(socket, 'SO_EXCLUSIVEADDRUSE'):
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()

class PreviewHandler(SimpleHTTPRequestHandler):
    def do_HEAD(self):
        # Reuse the frontend allowlist; never expose private filesystem metadata.
        self.do_GET()

    def do_GET(self):
        if self.path.split('?', 1)[0].startswith('/api/'):
            if self.command == 'HEAD':
                self.send_error(405);return
            self.handle_api()
            return
        # Only serve frontend files, never backend sources, Git or local secrets.
        path = self.path.split('?', 1)[0]
        if path not in {'/brand-refresh.css', '/cloud-theme.js', '/assets/guardian-emblem.png', '/brand-entry.js', '/brand-entry.css', '/', '/index.html', '/landing.js', '/shared_plan.js', '/kids_experience.js', '/experience.css', '/feedback.css', '/assets/school-day.svg', '/assets/kids-air-day.svg', '/assets/kids-reading-v2.webp', '/app.js', '/guardian.js', '/pwa.js', '/i18n.js', '/sw.js', '/manifest.webmanifest', '/guardian_services.js', '/workspace.js', '/workspace_extras.js', '/assets/vendor/leaflet/leaflet.js', '/assets/vendor/leaflet/leaflet.css', '/guardian.css', '/ui.js', '/kids.js', '/campus.js', '/data.js', '/services.js', '/styles.css', '/redesign.css', '/refinement.css', '/assets/logo.svg', '/assets/logo-still.svg', '/assets/campus-air.svg', '/assets/indoor-day.svg', '/assets/campus-landscape.webp', '/favicon.ico'}:
            self.send_error(404)
            return
        if path == '/favicon.ico':
            self.send_response(204)
            self.end_headers()
            return
        if self.command == "HEAD":
            super().do_HEAD()
        else:
            super().do_GET()

    def do_POST(self):
        self.handle_api()

    def do_DELETE(self):
        self.handle_api()

    def handle_api(self):
        local_origin = f'http://127.0.0.1:{self.server.server_port}'
        if self.headers.get('Host') != f'127.0.0.1:{self.server.server_port}':
            self.send_error(403)
            return
        if self.command != 'GET' and self.headers.get('Origin') != local_origin:
            self.send_error(403)
            return
        if api_handler is None:
            self.send_error(503, 'Install backend/functions/requirements.txt for the local API')
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError:
            self.send_error(400)
            return
        if length < 0 or length > 4096:
            self.send_error(413)
            return
        if self.command == 'POST' and self.headers.get_content_type() != 'application/json':
            self.send_error(415)
            return
        try:
            body = self.rfile.read(length).decode('utf-8') if length else None
        except UnicodeDecodeError:
            self.send_error(400)
            return
        parsed = urlsplit(self.path)
        event = {'httpMethod': self.command, 'path': parsed.path,
                 'headers': dict(self.headers.items()), 'body': body,
                 'queryStringParameters': dict(parse_qsl(parsed.query)),
                 'requestContext': {'stage': 'local', 'requestId': 'local-demo'},
                 'isBase64Encoded': False}
        try:
            # API Gateway calls a Lambda instance serially. Preserve that model
            # when adapting Powertools' current_event to ThreadingHTTPServer.
            with API_LOCK:
                result = api_handler(event, None)
        except Exception:
            self.send_error(503, 'The local plan store is unavailable')
            return
        self.send_response(result['statusCode'])
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        for name, values in result.get('multiValueHeaders', {}).items():
            if name.lower() == 'set-cookie':
                for value in values:
                    self.send_header(name, value)
        self.end_headers()
        self.wfile.write(result.get('body', '{}').encode('utf-8'))

    def end_headers(self):
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Cache-Control', 'no-store' if self.path.startswith('/api/') else 'no-cache')
        super().end_headers()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=5173)
    args = parser.parse_args()
    server = PreviewServer(('127.0.0.1', args.port), partial(PreviewHandler, directory=str(ROOT)))
    print(f'Air Guardian preview: http://127.0.0.1:{args.port}', flush=True)
    print(f'AWS open-source demo API: {"Powertools + local SQLite" if api_handler else "unavailable; install requirements"}', flush=True)
    if api_handler:
        from threading import Thread, Event
        from backend.functions.alert_engine import monitor_tick
        def monitor():
            while True:
                try:
                    with API_LOCK:
                        monitor_tick()
                except Exception:
                    pass
                Event().wait(60)
        Thread(target=monitor,daemon=True).start()
    server.serve_forever()
