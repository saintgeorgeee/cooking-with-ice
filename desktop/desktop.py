"""Native application window and persistent per-user settings."""
import os
from pathlib import Path
import shutil
import sys
import threading
import webview
from app import AppState, ROOT, create_server


def data_dir():
    if sys.platform == 'win32':
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'Discord Activity Controller'
    return Path.home() / 'Library' / 'Application Support' / 'Discord Activity Controller'


def main():
    folder = data_dir()
    folder.mkdir(parents=True, exist_ok=True)
    config = folder / 'activities.json'
    if not config.exists():
        shutil.copyfile(ROOT / 'activities.json', config)
    state = AppState(config)
    server = create_server(state, 0)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        webview.create_window('Discord Activity Controller', f'http://127.0.0.1:{server.server_address[1]}',
                              width=1120, height=820, min_size=(390, 600), background_color='#101115')
        webview.start()
    finally:
        server.shutdown()
        server.server_close()
        state.rpc.close()


if __name__ == '__main__':
    main()
