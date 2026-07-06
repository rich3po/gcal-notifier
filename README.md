# Google Calendar notifier app

A macOS menu bar app that shows your **next upcoming Google Calendar meeting** (primary calendar). It refreshes every 60 seconds.

## Configure Google Calendar (read-only)

You need a one-time OAuth setup in Google Cloud. The app only requests **read-only** access to your calendars.

### 1. Create a Google Cloud project

1. Open the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.

### 2. Enable the Google Calendar API

1. Go to **APIs & Services** → **Library**.
2. Search for **Google Calendar API** and click **Enable**.

### 3. Configure the OAuth consent screen

1. Go to **APIs & Services** → **OAuth consent screen**.
2. Choose **External** (or **Internal** if you use Google Workspace and only need access within your org).
3. Fill in the required app information (app name, support email).
4. Under **Scopes**, add:
   - `https://www.googleapis.com/auth/calendar.readonly`  
     (See and download any calendar you can access via your Calendar calendars)
5. If the app is in **Testing** mode, add your Google account under **Test users**.

### 4. Create Desktop OAuth credentials

1. Go to **APIs & Services** → **Credentials**.
2. Click **Create credentials** → **OAuth client ID**.
3. Application type: **Desktop app**.
4. Download the JSON file and save it as `credentials.json` in this project directory (same folder as `app.py`).

### 5. First run (authorize the app)

```bash
cd /path/to/meetings-app
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

On first launch:

1. Your browser opens for Google sign-in.
2. Approve **read-only** calendar access.
3. A `token.json` file is created locally for future runs (no browser needed until the token is revoked or expires).

### 6. Security notes

- **Never commit** `credentials.json` or `token.json` (they are listed in `.gitignore`).
- To revoke access: [Google Account → Third-party access](https://myaccount.google.com/permissions).

## Run

```bash
source .venv/bin/activate
python app.py
```

- The menubar shows the next meeting, e.g. `Standup · 2:30 PM`.
- Click the menubar item → **Join meetings** directly, or **View in calendar**.
- Updates automatically every 60 seconds.

## Run at login (macOS LaunchAgent)

To start the app automatically when you log in, install a
[LaunchAgent](https://developer.apple.com/library/archive/documentation/MacOSX/Conceptual/BPSystemStartup/Chapters/CreatingLaunchdJobs.html).
A LaunchAgent (not a LaunchDaemon) runs in your GUI session, which a menu-bar app
requires.

### Quick install (recommended)

[`install-launchagent.sh`](install-launchagent.sh) generates the plist with paths
derived from the repo's location, validates it, and (re)loads it. Run it from
anywhere after the venv is set up:

```bash
./install-launchagent.sh              # install and start at login
./install-launchagent.sh --uninstall  # stop and remove
```

Re-running it is safe — it reloads in place, so use it again after pulling
updates or moving the repo.

### Manual install

If you'd rather set it up by hand:

1. Create `~/Library/LaunchAgents/com.richjones.gcal-notifier.plist`. **Use
   absolute paths**, and set `WorkingDirectory` to the project root — `app.py`
   reads `credentials.json` / `token.json` by relative path, so it must launch
   from there.

   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
     "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
   <plist version="1.0">
   <dict>
       <key>Label</key>
       <string>com.richjones.gcal-notifier</string>

       <key>ProgramArguments</key>
       <array>
           <string>/Users/rich.jones/Code/gcal-notifier/.venv/bin/python</string>
           <string>/Users/rich.jones/Code/gcal-notifier/app.py</string>
       </array>

       <!-- app.py reads credentials.json / token.json by relative path -->
       <key>WorkingDirectory</key>
       <string>/Users/rich.jones/Code/gcal-notifier</string>

       <!-- start at login -->
       <key>RunAtLoad</key>
       <true/>

       <!-- do NOT relaunch after the user quits from the menu -->
       <key>KeepAlive</key>
       <false/>

       <key>StandardOutPath</key>
       <string>/Users/rich.jones/Code/gcal-notifier/output.log</string>
       <key>StandardErrorPath</key>
       <string>/Users/rich.jones/Code/gcal-notifier/error.log</string>
   </dict>
   </plist>
   ```

2. Validate and load it (loading also starts it immediately, thanks to
   `RunAtLoad`):

   ```bash
   plutil -lint ~/Library/LaunchAgents/com.richjones.gcal-notifier.plist
   launchctl load -w ~/Library/LaunchAgents/com.richjones.gcal-notifier.plist
   ```

`RunAtLoad` starts the app at login; `KeepAlive` is `false` so quitting from the
menu actually quits it until the next login (set it to `true` if you'd rather it
always relaunch).

### Managing the agent

```bash
launchctl start com.richjones.gcal-notifier   # start now (without re-login)
launchctl stop  com.richjones.gcal-notifier   # quit now (same as the menu's Quit)

# disable autostart entirely
launchctl unload -w ~/Library/LaunchAgents/com.richjones.gcal-notifier.plist
# re-enable
launchctl load   -w ~/Library/LaunchAgents/com.richjones.gcal-notifier.plist

launchctl list | grep gcal-notifier           # check status (PID, last exit code)
```

- After editing the plist, `unload` then `load` for changes to take effect.
- Startup logs go to `output.log` / `error.log` in the project root.
- If you move or rename the project folder, update the absolute paths and reload.

## Tests

Unit tests live in [`tests/`](tests/) and run with [pytest](https://docs.pytest.org/).

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt   # one-time: installs runtime deps + pytest
pytest
```

- `requirements-dev.txt` pulls in `requirements.txt` plus the test tooling.
- The suite covers the pure helper functions (countdown/title formatting, Zoom &
  Teams URL conversion, calendar event parsing) and a regression test guarding
  against the duplicate "Quit" menu item at boot.
- Tests run fully offline — no Google credentials or network access required.

## Manual verification

1. `pip install -r requirements.txt` completes without errors.
2. `python3 -m py_compile app.py calendar_client.py` succeeds.
3. With `credentials.json` in place, first run opens the browser and creates `token.json`.
4. Menubar shows your next primary-calendar event (or `No meetings` if none).
5. Second run uses `token.json` without opening the browser.

## Requirements

- macOS (menu bar app via [rumps](https://github.com/jaredks/rumps))
- Python 3.10+
