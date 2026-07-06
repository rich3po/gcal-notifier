#!/usr/bin/env bash
#
# Install (or reinstall) the gcal-notifier macOS LaunchAgent so the menu-bar app
# starts at login. Paths are derived from this script's own location, so it works
# regardless of where the repo lives.
#
#   ./install-launchagent.sh            # install and start
#   ./install-launchagent.sh --uninstall # stop and remove
#
set -euo pipefail

LABEL="com.richjones.gcal-notifier"
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="$PROJECT_DIR/.venv/bin/python"
APP="$PROJECT_DIR/app.py"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ "${1:-}" == "--uninstall" ]]; then
    if [[ -f "$PLIST" ]]; then
        launchctl unload -w "$PLIST" 2>/dev/null || true
        rm -f "$PLIST"
        echo "Uninstalled $LABEL (removed $PLIST)."
    else
        echo "Nothing to uninstall: $PLIST does not exist."
    fi
    exit 0
fi

# Preflight: the LaunchAgent points at the venv interpreter, so it must exist.
if [[ ! -x "$PYTHON" ]]; then
    echo "Error: $PYTHON not found or not executable." >&2
    echo "Create the venv and install deps first:" >&2
    echo "  python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt" >&2
    exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents"

# Generate the plist with absolute paths resolved at install time.
cat > "$PLIST" <<PLIST_EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>$LABEL</string>

    <key>ProgramArguments</key>
    <array>
        <string>$PYTHON</string>
        <string>$APP</string>
    </array>

    <!-- app.py reads credentials.json / token.json by relative path -->
    <key>WorkingDirectory</key>
    <string>$PROJECT_DIR</string>

    <!-- start at login -->
    <key>RunAtLoad</key>
    <true/>

    <!-- do NOT relaunch after the user quits from the menu -->
    <key>KeepAlive</key>
    <false/>

    <key>StandardOutPath</key>
    <string>$PROJECT_DIR/output.log</string>
    <key>StandardErrorPath</key>
    <string>$PROJECT_DIR/error.log</string>
</dict>
</plist>
PLIST_EOF

plutil -lint "$PLIST"

# Reload to pick up any changes (load alone is a no-op if already loaded).
launchctl unload -w "$PLIST" 2>/dev/null || true
launchctl load -w "$PLIST"

echo "Installed and started $LABEL."
echo "Plist: $PLIST"
echo "Check status with: launchctl list | grep gcal-notifier"
