# Animated Discord Rich Presence

Show **Cooking with ice** or **Framewisp making pancakes** on your Discord profile using a small Python script. Start it from **Terminal on macOS** or **PowerShell on Windows**.

| Cooking with ice | Framewisp |
| :---: | :---: |
| <img src="minecraft_ice_cycle_512_5fps_exact_timing.webp" width="180" alt="Animated Minecraft ice"> | <img src="Wispy_making_pancakes.webp" width="180" alt="Framewisp making pancakes"> |

**No dashboard, bot token, client secret, or Git installation required.** You do need the Discord **desktop** app and Python **3.9 or newer**.

- [Choose your activity name](#1-choose-your-activity-name)
- [macOS — Terminal](#macos--terminal)
- [Windows — PowerShell](#windows--powershell)
- [Quick option: use the shared Cooking with ice application](#quick-option-use-the-shared-cooking-with-ice-application)
- [Troubleshooting](#troubleshooting)

## 1. Choose your activity name

**Recommended: create your own Discord application.** This lets you choose the name displayed on your profile.

1. Open the [Discord Developer Portal](https://discord.com/developers/applications) and sign in.
2. Click **New Application** and give it the name you want people to see, such as `Framewisp` or `Cooking with ice`.
3. Open **General Information** and copy the **Application ID**.
4. Keep that ID ready. Replace `YOUR_APPLICATION_ID` in the commands below with the actual number, without spaces.

The `--activity` option selects the **image preset**. Your Application ID determines the **registered application name** shown by this script. For example, choosing `--activity framewisp` does not rename an application called `My Pancakes`.

To switch between **two different names**, create two applications and use the matching ID for each. To switch only the image, you can reuse the same ID.

You do not need to create a bot, invite anything to a server, or copy any token. An Application ID is public configuration, not a password. If you prefer to use the existing shared Cooking with ice application, see the [quick option](#quick-option-use-the-shared-cooking-with-ice-application).

## macOS — Terminal

### 1. Install Python and open Discord

Install Python from [python.org](https://www.python.org/downloads/macos/) if needed. Open **Terminal** and check:

```bash
python3 --version
```

Open the **Discord desktop app** and log in. Keep it open while using Rich Presence.

### 2. Download and install — first time only

Copy this entire block into Terminal:

```bash
mkdir -p "$HOME/discord-rich-presence"
cd "$HOME/discord-rich-presence"
curl --fail --location "https://raw.githubusercontent.com/saintgeorgeee/cooking-with-ice/refs/heads/main/rich_presence.py" --output rich_presence.py
curl --fail --location "https://raw.githubusercontent.com/saintgeorgeee/cooking-with-ice/refs/heads/main/requirements.txt" --output requirements.txt
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Wait for installation to finish successfully before continuing. You only need to do this setup once in this folder.

### 3. Start an activity

Replace `YOUR_APPLICATION_ID` with the ID copied from the Developer Portal. Choose **one** command:

**Cooking with ice image:**

```bash
.venv/bin/python rich_presence.py --activity cooking --client-id YOUR_APPLICATION_ID
```

**Framewisp image:**

```bash
.venv/bin/python rich_presence.py --activity framewisp --client-id YOUR_APPLICATION_ID
```

Keep the terminal open. Press **Control+C** to clear the activity and stop the script. Stop the current script before starting another activity.

### 4. Open it again later

Open Terminal, enter the folder, then run your chosen start command again:

```bash
cd "$HOME/discord-rich-presence"
.venv/bin/python rich_presence.py --activity framewisp --client-id YOUR_APPLICATION_ID
```

Use `--activity cooking` instead if you want the ice animation. You do **not** need to reinstall the package each time.

## Windows — PowerShell

### 1. Install Python and open Discord

Install Python from [python.org](https://www.python.org/downloads/windows/) if needed. Open **PowerShell** and check:

```powershell
py -3 --version
```

If `py` is not recognized but `python --version` works, replace `py -3` with `python` in the setup command below.

Open the **Discord desktop app** and log in. Keep it open while using Rich Presence.

### 2. Download and install — first time only

Copy this entire block into PowerShell:

```powershell
New-Item -ItemType Directory -Force -Path "$HOME\discord-rich-presence" | Out-Null
Set-Location "$HOME\discord-rich-presence"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/saintgeorgeee/cooking-with-ice/refs/heads/main/rich_presence.py" -OutFile "rich_presence.py"
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/saintgeorgeee/cooking-with-ice/refs/heads/main/requirements.txt" -OutFile "requirements.txt"
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Wait for installation to finish successfully before continuing. You only need to do this setup once in this folder. These commands run the virtual environment's Python directly; no activation script or PowerShell execution-policy change is needed.

### 3. Start an activity

Replace `YOUR_APPLICATION_ID` with the ID copied from the Developer Portal. Choose **one** command:

**Cooking with ice image:**

```powershell
.\.venv\Scripts\python.exe rich_presence.py --activity cooking --client-id YOUR_APPLICATION_ID
```

**Framewisp image:**

```powershell
.\.venv\Scripts\python.exe rich_presence.py --activity framewisp --client-id YOUR_APPLICATION_ID
```

Keep the PowerShell window open. Press **Ctrl+C** to clear the activity and stop the script. Stop the current script before starting another activity.

### 4. Open it again later

Open PowerShell, enter the folder, then run your chosen start command again:

```powershell
Set-Location "$HOME\discord-rich-presence"
.\.venv\Scripts\python.exe rich_presence.py --activity framewisp --client-id YOUR_APPLICATION_ID
```

Use `--activity cooking` instead if you want the ice animation. You do **not** need to reinstall the package each time.

## Quick option: use the shared Cooking with ice application

You can use the public Application ID **`1566577658631028847`** instead of creating an application. The script defaults to that ID when you select Cooking with ice without `--client-id`.

**macOS**, after completing setup:

```bash
cd "$HOME/discord-rich-presence"
.venv/bin/python rich_presence.py --activity cooking
```

**Windows PowerShell**, after completing setup:

```powershell
Set-Location "$HOME\discord-rich-presence"
.\.venv\Scripts\python.exe rich_presence.py --activity cooking
```

The registered name will be **Cooking with ice**. Using this ID does not let you choose your own application name. Create your own application for a custom name.

No shared Framewisp Application ID is included. For that preset, use your own Application ID as shown in the main instructions. The animation URL is already configured; you do not need to upload it again.

## Image URLs

The script includes both public image URLs:

**Cooking with ice**

```text
https://raw.githubusercontent.com/saintgeorgeee/cooking-with-ice/refs/heads/main/minecraft_ice_cycle_512_5fps_exact_timing.webp
```

**Framewisp**

```text
https://raw.githubusercontent.com/saintgeorgeee/cooking-with-ice/refs/heads/main/Wispy_making_pancakes.webp
```

To use your own image, add `--image "YOUR_DIRECT_HTTPS_IMAGE_URL"` to a start command. The URL must return the image itself, not a web page or a local file. For animated WebP, use a public external URL; uploaded Discord Art Assets do not support animation. See [Discord's activity asset documentation](https://github.com/discord/discord-api-docs/blob/main/developers/events/gateway-events.mdx).

## Troubleshooting

- **Discord could not be found:** open the Discord desktop app and log in, then rerun the start command. The browser/mobile client is not enough.
- **Nothing appears on your profile:** check your activity-sharing/privacy settings in Discord. The activity must be allowed to show on your profile.
- **The wrong name appears:** check which Discord application owns the ID you supplied. Changing `--activity` changes the image preset, not that application's name.
- **Missing pypresence:** use the `.venv` Python paths shown above for both installation and startup.
- **File not found:** enter the `discord-rich-presence` folder before running the command.
- **Invalid Application ID:** use the numeric Application ID from General Information, not a token or the whole Developer Portal URL.
- **Discord restarted:** press Ctrl+C, then rerun the start command. This small script does not automatically reconnect.
- **Switching activities:** stop the current script with Ctrl+C before running the other command. Run one copy at a time.

The activity stays running while the script and Discord are open. Ctrl+C clears it and closes the RPC connection. If you force-close the terminal or Discord, the connection ends too; use Ctrl+C for a clean stop.

## How it works

[`rich_presence.py`](rich_presence.py) uses [pypresence](https://qwertyquerty.github.io/pypresence/html/info/quickstart.html) to connect locally to Discord through RPC, publish the image, and keep the process alive. It does not log in to your account or require credentials. Setup uses Python's built-in [virtual environments](https://docs.python.org/3/tutorial/venv.html).
