#!/usr/bin/env python3
"""Run with python3 app.py. Local macOS Discord Rich Presence dashboard."""
import argparse
from functools import partial
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
from pathlib import Path
import secrets
import signal
import sys
import threading
from urllib.parse import unquote, urlsplit
import webbrowser

from controller import ConfigManager, DiscordRPCManager, ValidationError, validate_activity

ROOT = Path(__file__).resolve().parent


class AppState:
    def __init__(self, config_path, manager=None):
        self.config = ConfigManager(config_path)
        if manager is None and sys.platform == 'win32':
            from windows_rpc import WindowsIPC
            manager = DiscordRPCManager(factory=WindowsIPC)
        self.rpc = manager or DiscordRPCManager()
        self.token = secrets.token_urlsafe(32)
        self.lock = threading.RLock()


class Handler(BaseHTTPRequestHandler):
    server_version = 'ActivityController/1.0'

    def __init__(self, *args, state, **kwargs):
        self.state = state
        super().__init__(*args, **kwargs)

    def reply(self, status, body, content_type='application/json; charset=utf-8'):
        if not isinstance(body, bytes):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; img-src 'self' https:; style-src 'self'; script-src 'self'; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
        self.end_headers()
        self.wfile.write(body)

    def dispatch(self):
        port = self.server.server_address[1]
        hosts = {f'127.0.0.1:{port}', f'localhost:{port}'}
        if self.headers.get('Host') not in hosts:
            return self.reply(403, {'error': 'Host not allowed.'})
        path = unquote(urlsplit(self.path).path)
        mutation = self.command in {'POST', 'PUT', 'DELETE'}
        if mutation:
            origin = self.headers.get('Origin')
            if (origin and origin not in {f'http://{host}' for host in hosts}) or not secrets.compare_digest(self.headers.get('X-Controller-Token', ''), self.state.token):
                return self.reply(403, {'error': 'Unauthorized request. Reload the app.'})
        if self.command == 'GET':
            if path == '/api/status':
                return self.reply(200, self.state.rpc.status())
            if path == '/api/activities':
                return self.reply(200, self.state.config.snapshot())
            if path == '/':
                body = (ROOT / 'static/index.html').read_text().replace('__TOKEN__', self.state.token)
                return self.reply(200, body.encode(), 'text/html; charset=utf-8')
            if path.startswith('/static/'):
                file = (ROOT / path.lstrip('/')).resolve()
                static = (ROOT / 'static').resolve()
                if static in file.parents and file.is_file():
                    return self.reply(200, file.read_bytes(), mimetypes.guess_type(str(file))[0] or 'application/octet-stream')
            return self.reply(404, {'error': 'Resource not found.'})
        if not mutation:
            return self.reply(405, {'error': 'Method not allowed.'})
        with self.state.lock:
            activities = self.state.config.snapshot()
            if path == '/api/deactivate' and self.command == 'POST':
                self.state.rpc.select(None, None)
                return self.reply(202, self.state.rpc.status())
            parts = path.strip('/').split('/')
            if (len(parts) == 4 and parts[:2] == ['api', 'activity']
                    and parts[3] == 'activate' and self.command == 'POST'):
                key = parts[2]
                if key not in activities:
                    return self.reply(404, {'error': 'Activity not found.'})
                if not activities[key]['application_id']:
                    raise ValidationError('Add an Application ID before activating this activity.')
                self.state.rpc.select(key, activities[key])
                return self.reply(202, self.state.rpc.status())
            if path == '/api/activities' and self.command == 'POST':
                config = validate_activity(self.read_json())
                key = 'activity_' + secrets.token_hex(6)
                activities[key] = config
                self.state.config.save(activities)
                return self.reply(201, {'id': key, 'activity': config})
            if len(parts) == 3 and parts[:2] == ['api', 'activities']:
                key = parts[2]
                if key not in activities:
                    return self.reply(404, {'error': 'Activity not found.'})
                if self.command == 'PUT':
                    config = validate_activity(self.read_json())
                    if self.state.rpc.status()['selected_id'] == key and not config['application_id']:
                        raise ValidationError('Turn off the activity before removing its Application ID.')
                    activities[key] = config
                    self.state.config.save(activities)
                    if self.state.rpc.status()['selected_id'] == key:
                        self.state.rpc.select(key, config)
                    return self.reply(200, {'id': key, 'activity': config})
                if self.command == 'DELETE':
                    del activities[key]
                    self.state.config.save(activities)
                    if self.state.rpc.status()['selected_id'] == key:
                        self.state.rpc.select(None, None)
                    return self.reply(200, {'deleted': key})
            return self.reply(404, {'error': 'Endpoint not found.'})

    def read_json(self):
        if self.headers.get_content_type() != 'application/json':
            raise ValidationError('Send an application/json object.')
        try:
            length = int(self.headers.get('Content-Length', '0'))
        except ValueError as exc:
            raise ValidationError('Invalid request length.') from exc
        if not 0 < length <= 32768:
            raise ValidationError('Request must be at most 32 KB.')
        return json.loads(self.rfile.read(length))

    def handle_request(self):
        self.connection.settimeout(5)
        try:
            self.dispatch()
        except (ValidationError, ValueError, UnicodeError) as exc:
            self.reply(400, {'error': str(exc)})
        except (BrokenPipeError, ConnectionResetError):
            pass
        except OSError:
            self.reply(500, {'error': 'Could not read or save the local file. Check permissions.'})

    do_GET = do_POST = do_PUT = do_DELETE = do_OPTIONS = handle_request

    def log_message(self, fmt, *args):
        if len(args) > 1 and str(args[1]) not in {'200', '202'}:
            super().log_message(fmt, *args)


def create_server(state, port=8765):
    server = ThreadingHTTPServer(('127.0.0.1', port), partial(Handler, state=state))
    server.daemon_threads = True
    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-browser', action='store_true', help='Do not open the browser')
    parser.add_argument('--port', type=int, default=8765, help='Local port (default: 8765)')
    parser.add_argument('--config', type=Path, default=ROOT / 'activities.json', help='Configuration file')
    args = parser.parse_args()
    state = None
    try:
        state = AppState(args.config)
        server = create_server(state, args.port)
    except (ValidationError, OSError, OverflowError) as exc:
        if state:
            state.rpc.close()
        print(f'Could not start: {exc}', file=sys.stderr)
        return 1
    url = f'http://127.0.0.1:{server.server_address[1]}'
    print(f'Discord Activity Controller → {url}\nPress Ctrl+C to clear your presence and exit.', flush=True)
    def shutdown(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, shutdown)
    if not args.no_browser:
        threading.Timer(0.4, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever(poll_interval=0.3)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
        state.rpc.close()
        print('\nPresence cleared.')
    return 0


if __name__ == '__main__':
    sys.exit(main())
