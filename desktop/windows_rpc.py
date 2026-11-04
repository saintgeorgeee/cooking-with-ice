"""Discord named-pipe adapter used exclusively on Windows."""
import asyncio
import os
import secrets
from contextlib import suppress
from pypresence import Presence
from controller import RPCError


class WindowsIPC:
    def __init__(self):
        self.rpc = None
        self.loop = None

    @staticmethod
    def available():
        return False  # Existence is not proof that a Discord pipe accepts requests.

    def connect(self, application_id):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.rpc = Presence(application_id, loop=self.loop, connection_timeout=5, response_timeout=5)
            self.rpc.connect()
        except Exception as exc:
            self.close()
            raise RPCError(f'Discord is unavailable: {exc}') from exc

    def update(self, activity):
        try:
            if activity is None:
                self.rpc.clear()
            else:
                payload = {'cmd': 'SET_ACTIVITY', 'args': {'pid': os.getpid(), 'activity': activity},
                           'nonce': secrets.token_hex(16)}
                self.rpc.update(payload_override=payload)
        except Exception as exc:
            raise RPCError(f'Discord: {exc}') from exc

    def health(self):
        try:
            self.loop.run_until_complete(asyncio.sleep(0))
            if self.rpc.sock_reader.at_eof() or self.rpc.sock_writer.is_closing():
                raise RPCError('Discord disconnected.')
        except RPCError:
            raise
        except Exception as exc:
            raise RPCError(f'Discord: {exc}') from exc

    def close(self):
        if self.rpc:
            with suppress(Exception):
                self.rpc.close()
            self.rpc = None
        if self.loop and not self.loop.is_closed():
            self.loop.close()
        self.loop = None
