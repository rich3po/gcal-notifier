# macOS menu bar app showing the next Google Calendar meeting
import subprocess
import urllib.parse
import webbrowser
from datetime import datetime, timezone

import rumps

from calendar_client import CalendarSetupError, get_credentials, get_next_event

MAX_TITLE_LEN = 20


def format_countdown(start: datetime) -> str:
    """Return a bracketed countdown string to the given start datetime."""
    now = datetime.now(timezone.utc)
    if start.tzinfo is None:
        start = start.replace(tzinfo=timezone.utc)
    delta_minutes = int((start - now).total_seconds() // 60)
    if delta_minutes <= 0:
        return "[now]"
    hours, minutes = divmod(delta_minutes, 60)
    if hours == 0:
        return f"[{minutes}m]"
    return f"[{hours}h {minutes:02d}m]"


def format_next_event(event: dict) -> str:
    """Format an event for the menubar (truncated title + time)."""
    title = event["summary"]
    if len(title) > MAX_TITLE_LEN:
        title = title[: MAX_TITLE_LEN - 1] + "…"

    if event["all_day"]:
        return f"{title} · All day"

    start = event["start"]
    if start.tzinfo is None:
        local_start = start
    else:
        local_start = start.astimezone()
    time_str = local_start.strftime("%-I:%M %p")
    return f"{title} · {time_str} {format_countdown(start)}"


def _to_zoom_app_url(https_url: str) -> str:
    """Convert a Zoom HTTPS join URL to a zoommtg:// URL to open the desktop app."""
    parsed = urllib.parse.urlparse(https_url)
    meeting_id = parsed.path.lstrip("/j/").split("/")[0]
    params = urllib.parse.parse_qs(parsed.query)
    query = f"action=join&confno={meeting_id}"
    if "pwd" in params:
        query += f"&pwd={params['pwd'][0]}"
    return f"zoommtg://{parsed.netloc}/join?{query}"


def _to_teams_app_url(https_url: str) -> str:
    """Convert a Teams HTTPS join URL to a msteams:// URL to open the desktop app."""
    return https_url.replace("https://", "msteams://", 1)



class MeetingsApp(rumps.App):
    """Menubar app showing the next upcoming Google Calendar meeting."""

    def __init__(self):
        super().__init__("Meetings", title="Loading…")
        if "Quit" in self.menu:
            del self.menu["Quit"]
        self._zoom_link = None
        self._teams_link = None
        self._html_link = None

        try:
            get_credentials()
        except CalendarSetupError:
            self.title = "Set up calendar"
            return

        self.refresh_meeting()

    def join_zoom_clicked(self, _):
        if self._zoom_link:
            subprocess.run(["open", _to_zoom_app_url(self._zoom_link)])

    def join_teams_clicked(self, _):
        if self._teams_link:
            webbrowser.open(_to_teams_app_url(self._teams_link))

    def view_in_calendar_clicked(self, _):
        if self._html_link:
            webbrowser.open(self._html_link)

    @rumps.timer(60)  # refresh every 60 seconds
    def refresh_timer(self, _):
        self.refresh_meeting()

    def _update_meeting_menu_items(self, zoom_link: str | None, teams_link: str | None, html_link: str | None = None):
        """Rebuild the menu from scratch on every refresh."""
        self._zoom_link = zoom_link
        self._teams_link = teams_link
        self._html_link = html_link

        self.menu.clear()

        if zoom_link:
            self.menu.add(rumps.MenuItem("Join Zoom", callback=self.join_zoom_clicked))
        if teams_link:
            self.menu.add(rumps.MenuItem("Join Teams", callback=self.join_teams_clicked))
        if html_link:
            self.menu.add(rumps.MenuItem("View in calendar", callback=self.view_in_calendar_clicked))
        self.menu.add(rumps.MenuItem("Quit", callback=rumps.quit_application))

    def refresh_meeting(self):
        try:
            event = get_next_event()
        except CalendarSetupError:
            self.title = "Set up calendar"
            self._update_meeting_menu_items(None, None, None)
        except Exception:
            self.title = "Calendar error"
            self._update_meeting_menu_items(None, None, None)
        else:
            if event is None:
                self.title = "(No meetings)"
                self._update_meeting_menu_items(None, None, None)
            else:
                self.title = format_next_event(event)
                self._update_meeting_menu_items(event["zoom_link"], event["teams_link"], event["html_link"])


# Start the app when run as a script
if __name__ == "__main__":
    import AppKit
    AppKit.NSApplication.sharedApplication().setActivationPolicy_(
        AppKit.NSApplicationActivationPolicyAccessory
    )
    MeetingsApp().run()
