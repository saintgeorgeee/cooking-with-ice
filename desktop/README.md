# Desktop app

The desktop version uses pywebview for a native window, a localhost-only server bound to a random port, and one Discord Rich Presence connection. User changes are saved under `~/Library/Application Support/Discord Activity Controller` on macOS or `%APPDATA%/Discord Activity Controller` on Windows. The bundled presets are copied there the first time the app runs.

Figma with Framewisp and Cracking ice each use their configured Discord Application ID. Discord displays the registered application's name; to display a different name, create or rename the appropriate application in the Discord Developer Portal and use its ID. The in-app guide explains how to add activities and public image URLs.

For development, install `requirements.txt` and run `python desktop/desktop.py` from the repository root. The release workflow builds both systems. Builds are not signed or notarized and may trigger operating-system warnings.
