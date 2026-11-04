"""Configuration and single-owner Discord IPC controller. Python 3.9+, no dependencies."""
import copy
import json
import os
from pathlib import Path
import re
import secrets
import socket
import struct
import tempfile
import threading
import time
from urllib.parse import urlsplit

TYPES = {'playing': 0, 'listening': 2, 'watching': 3, 'competing': 5}


class ValidationError(ValueError):
    pass


def https_url(value):
    try:
        url = urlsplit(value)
        return (url.scheme == 'https' and bool(url.hostname) and not url.username
                and not url.password and not any(c.isspace() for c in value)
                and url.port != 0)
    except ValueError:
        return False


def validate_activity(data):
    if not isinstance(data, dict):
        raise ValidationError('Each activity must be a JSON object.')
    allowed = {'label', 'application_id', 'type', 'details', 'state', 'large_image',
               'large_text', 'small_image', 'small_text', 'timer', 'preview', 'icon', 'buttons'}
    if set(data) - allowed:
        raise ValidationError('Unknown fields: ' + ', '.join(sorted(set(data) - allowed)))
    result = {}
    limits = {'label': 64, 'application_id': 20, 'type': 12, 'details': 128,
              'state': 128, 'large_image': 512, 'large_text': 128,
              'small_image': 512, 'small_text': 128, 'preview': 256, 'icon': 12}
    for key, limit in limits.items():
        value = data.get(key)
        if value is not None and not isinstance(value, str):
            raise ValidationError(f'{key}: must be text.')
        value = value.strip() if value else None
        if value and len(value) > limit:
            raise ValidationError(f'{key}: maximum {limit} characters.')
        result[key] = value
    if not result['label']:
        raise ValidationError('Enter a name for the activity.')
    app_id = result['application_id']
    if app_id and (not re.fullmatch(r'[0-9]{17,20}', app_id) or int(app_id) >= 2**64):
        raise ValidationError('Application ID: enter a valid 17–20 digit Discord ID.')
    result['type'] = result['type'] or 'playing'
    if result['type'] not in TYPES:
        raise ValidationError('Invalid activity type.')
    for key in ('large_image', 'small_image'):
        if result[key] and not https_url(result[key]):
            raise ValidationError(f'{key}: enter a valid HTTPS URL.')
    preview = result['preview']
    if preview:
        path = Path(preview)
        if (path.is_absolute() or '..' in path.parts or '\\' in preview
                or not preview.startswith('static/previews/')
                or path.suffix.lower() not in {'.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg'}):
            raise ValidationError('The preview must be an image in static/previews/.')
    if not isinstance(data.get('timer', False), bool):
        raise ValidationError('timer must be true or false.')
    result['timer'] = data.get('timer', False)
    buttons = data.get('buttons') or []
    if not isinstance(buttons, list) or len(buttons) > 2:
        raise ValidationError('You can add up to two buttons.')
    result['buttons'] = []
    for button in buttons:
        if not isinstance(button, dict) or set(button) != {'label', 'url'}:
            raise ValidationError('Each button requires a label and URL.')
        label, url = button['label'], button['url']
        if (not isinstance(label, str) or not 1 <= len(label.strip()) <= 32
                or not isinstance(url, str) or len(url) > 512 or not https_url(url)):
            raise ValidationError('Button: use a 1–32 character label and a valid HTTPS URL.')
        result['buttons'].append({'label': label.strip(), 'url': url})
    return result


class ConfigManager:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict):
                raise ValidationError('Configuration must be a JSON object.')
            self.activities = {}
            for key, value in data.items():
                if not re.fullmatch(r'[a-zA-Z0-9_-]{1,64}', key):
                    raise ValidationError(f'Invalid activity ID: {key}')
                self.activities[key] = validate_activity(value)
        except (OSError, ValueError) as exc:
            raise ValidationError(f'Could not load {self.path.name}: {exc}. The file was not changed.') from exc

    def snapshot(self):
        with self.lock:
            return copy.deepcopy(self.activities)

    def save(self, data):
        # Atomic replace: failed writes leave both the file and memory unchanged.
        with self.lock:
            name = None
            try:
                with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=self.path.parent,
                                                 prefix='.activities-', delete=False) as file:
                    name = file.name
                    json.dump(data, file, ensure_ascii=False, indent=2)
                    file.write('\n')
                    file.flush()
                    os.fsync(file.fileno())
                os.replace(name, self.path)
                self.activities = copy.deepcopy(data)
            finally:
                if name and os.path.exists(name):
                    os.unlink(name)


def activity_payload(config, started_at):
    activity = {'type': TYPES[config['type']]}
    for key in ('details', 'state'):
        if config.get(key):
            activity[key] = config[key]
    assets = {key: config[key] for key in ('large_image', 'large_text', 'small_image', 'small_text')
              if config.get(key)}
    if assets:
        activity['assets'] = assets
    if config.get('timer'):
        activity['timestamps'] = {'start': int(started_at)}
    if config.get('buttons'):
        activity['buttons'] = config['buttons']
    return activity


class RPCError(Exception):
    pass


class DiscordIPC:
    """Bounded synchronous IPC. Only the manager worker may own/use this socket."""
    def __init__(self):
        self.sock = None

    @staticmethod
    def paths():
        roots = list(dict.fromkeys([os.environ.get(k) for k in
                     ('XDG_RUNTIME_DIR', 'TMPDIR', 'TMP', 'TEMP')] + ['/tmp']))
        return [str(Path(root) / f'discord-ipc-{i}') for root in roots if root for i in range(10)]

    @classmethod
    def available(cls):
        return any(Path(path).exists() for path in cls.paths())

    def connect(self, application_id):
        for path in self.paths():
            if not Path(path).exists():
                continue
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.settimeout(3)
            try:
                sock.connect(path)
            except OSError:
                sock.close()
                continue
            self.sock = sock
            try:
                self.send(0, {'v': 1, 'client_id': application_id})
                self.receive_until(lambda op, value: op == 1 and value.get('evt') == 'READY')
                return
            except Exception:
                self.close()
                raise
        raise RPCError('Discord is unavailable. Open the desktop app; reconnecting automatically.')

    def send(self, opcode, value):
        payload = json.dumps(value, separators=(',', ':')).encode()
        self.sock.sendall(struct.pack('<II', opcode, len(payload)) + payload)

    def exact(self, count, deadline):
        data = bytearray()
        while len(data) < count:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Discord did not respond within 3 seconds.')
            self.sock.settimeout(remaining)
            chunk = self.sock.recv(count - len(data))
            if not chunk:
                raise RPCError('Discord disconnected.')
            data.extend(chunk)
        return data

    def receive_until(self, match):
        deadline = time.monotonic() + 3
        while True:
            opcode, length = struct.unpack('<II', self.exact(8, deadline))
            if length > 1024 * 1024:
                raise RPCError('Discord frame is too large.')
            value = json.loads(self.exact(length, deadline))
            if not isinstance(value, dict):
                raise RPCError('Invalid Discord response.')
            if opcode == 2 or value.get('evt') == 'ERROR':
                message = value.get('data') or value
                raise RPCError('Discord: ' + str(message.get('message', 'RPC request rejected.')))
            if opcode == 3:
                self.send(4, value)
            elif match(opcode, value):
                return value

    def update(self, activity):
        nonce = secrets.token_hex(16)
        self.send(1, {'cmd': 'SET_ACTIVITY', 'args': {'pid': os.getpid(), 'activity': activity}, 'nonce': nonce})
        self.receive_until(lambda op, value: op == 1 and value.get('nonce') == nonce)

    def health(self):
        # A ping detects a dead socket even when no new activity is requested.
        nonce = secrets.token_hex(8)
        self.send(3, {'nonce': nonce})
        self.receive_until(lambda op, value: op == 4 and value.get('nonce') == nonce)

    def close(self):
        if self.sock:
            self.sock.close()
            self.sock = None


class DiscordRPCManager:
    def __init__(self, factory=DiscordIPC, interval=5):
        self.factory = factory
        self.interval = interval
        self.lock = threading.RLock()
        self.wake = threading.Event()
        self.stop = threading.Event()
        self.selected = None
        self.config = None
        self.started_at = None
        self.generation = 0
        self.active = None
        self.connected = False
        self.phase = 'off'
        self.error = None
        self.worker = threading.Thread(target=self.run, name='discord-rpc', daemon=True)
        self.worker.start()

    def select(self, key, config):
        with self.lock:
            if self.selected == key and self.config == config:
                return  # Repeated clicks never reset the elapsed timer.
            self.selected = key
            self.config = copy.deepcopy(config)
            self.started_at = time.time() if key else None
            self.generation += 1
            self.phase = 'connecting' if key else 'stopping'
            self.active = None
            self.error = None
            self.wake.set()

    def status(self):
        with self.lock:
            return {'selected_id': self.selected, 'active_id': self.active,
                    'connected': self.connected, 'discord_available': self.factory.available(),
                    'phase': self.phase, 'started_at': self.started_at, 'error': self.error,
                    'generation': self.generation}

    def run(self):
        rpc, applied = None, -1
        try:
            while not self.stop.is_set():
                self.wake.clear()
                with self.lock:
                    generation, key = self.generation, self.selected
                    config, started = copy.deepcopy(self.config), self.started_at
                try:
                    if generation != applied:
                        if rpc:
                            try:
                                rpc.update(None)
                            finally:
                                rpc.close()
                                rpc = None
                        with self.lock:
                            self.connected = False
                        if self.stop.is_set():
                            break
                        if key:
                            rpc = self.factory()
                            rpc.connect(config['application_id'])
                            # A newer click can supersede an in-flight handshake.
                            with self.lock:
                                stale = generation != self.generation
                            if self.stop.is_set():
                                break
                            if stale:
                                rpc.close()
                                rpc = None
                                continue
                            rpc.update(activity_payload(config, started))
                        applied = generation
                        with self.lock:
                            if generation == self.generation:
                                self.active = key
                                self.connected = bool(rpc)
                                self.phase = 'active' if key else 'off'
                                self.error = None
                    elif rpc:
                        rpc.health()
                except (OSError, ValueError, RPCError) as exc:
                    if rpc:
                        rpc.close()
                        rpc = None
                    applied = -1
                    with self.lock:
                        self.connected = False
                        self.active = None
                        if generation == self.generation:
                            self.phase = 'waiting' if key else 'off'
                            self.error = str(exc) if key else None
                with self.lock:
                    changed = generation != self.generation
                if not changed:
                    self.wake.wait(self.interval)
        finally:
            if rpc:
                try:
                    rpc.update(None)
                except (OSError, ValueError, RPCError):
                    pass
                finally:
                    rpc.close()

    def close(self):
        self.stop.set()
        self.wake.set()
        self.worker.join(timeout=8)
