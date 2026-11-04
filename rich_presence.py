#!/usr/bin/env python3
"""Animated Discord Rich Presence from your terminal (macOS / Windows)."""
import argparse
from contextlib import suppress
import re
import sys
import time
from urllib.parse import urlsplit

BASE_URL = 'https://raw.githubusercontent.com/saintgeorgeee/custom-discord-activities/refs/heads/main/'
ACTIVITIES = {
    'cooking': {
        'label': 'Cooking with ice',
        'application_id': '1566577658631028847',
        'image': BASE_URL + 'minecraft_ice_cycle_512_5fps_exact_timing.webp',
    },
    'framewisp': {
        'label': 'Framewisp',
        'application_id': None,
        'image': BASE_URL + 'Wispy_making_pancakes.webp',
    },
}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--activity', choices=ACTIVITIES, default='cooking',
                        help='Activity preset (default: cooking)')
    parser.add_argument('--client-id', help='Override the Discord Application ID')
    parser.add_argument('--image', help='Override the public HTTPS image URL')
    args = parser.parse_args(argv)
    preset = ACTIVITIES[args.activity]
    client_id = args.client_id or preset['application_id']
    image = args.image or preset['image']
    if client_id is None:
        parser.error('Framewisp needs an Application ID. Create an application named Framewisp '
                     'at https://discord.com/developers/applications and pass --client-id YOUR_APPLICATION_ID.')
    if not re.fullmatch(r'[0-9]{17,20}', client_id) or int(client_id) >= 2**64:
        parser.error('--client-id must be a Discord Application ID (17–20 digits).')
    try:
        url = urlsplit(image)
        valid_url = (url.scheme == 'https' and url.hostname and not url.username
                     and not url.password and not any(ord(c) < 33 for c in image))
        _ = url.port
    except ValueError:
        valid_url = False
    if not valid_url:
        parser.error('--image must be a valid public HTTPS image URL.')
    try:
        from pypresence import Presence
    except ImportError:
        print('Missing dependency. Run this with your virtual environment Python:\n'
              'python -m pip install -r requirements.txt', file=sys.stderr)
        return 1

    rpc = None
    connected = False
    try:
        rpc = Presence(client_id, connection_timeout=5, response_timeout=5)
        rpc.connect()
        connected = True
        rpc.update(large_image=image)
        print(f'{preset["label"]} preset is active. Discord uses the name registered to Application ID {client_id}.', flush=True)
        print('Keep Discord and this terminal open. Press Ctrl+C to stop.', flush=True)
        while True:
            time.sleep(15)
    except KeyboardInterrupt:
        print('\nStopping Rich Presence...')
    except Exception as exc:
        print(f'Could not set Rich Presence: {exc}\n'
              'Open the Discord desktop app and check your Application ID. '
              'If Discord restarted, run this command again.', file=sys.stderr)
        return 1
    finally:
        if rpc is not None:
            if connected:
                with suppress(Exception):
                    rpc.clear()
            with suppress(Exception):
                rpc.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())
