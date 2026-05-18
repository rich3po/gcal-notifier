# Meetings menubar app

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
- Click the menubar item → **Refresh** to update immediately, or **Quit** to exit.
- Updates automatically every 60 seconds.

## Manual verification

1. `pip install -r requirements.txt` completes without errors.
2. `python3 -m py_compile app.py calendar_client.py` succeeds.
3. With `credentials.json` in place, first run opens the browser and creates `token.json`.
4. Menubar shows your next primary-calendar event (or `No meetings` if none).
5. Second run uses `token.json` without opening the browser.

## Requirements

- macOS (menu bar app via [rumps](https://github.com/jaredks/rumps))
- Python 3.10+
