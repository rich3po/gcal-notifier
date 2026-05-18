# macOS menu bar app showing the next Google Calendar meeting
import rumps

from calendar_client import CalendarSetupError, get_credentials, get_next_event

MAX_TITLE_LEN = 20


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
    return f"{title} · {time_str}"


class MeetingsApp(rumps.App):
    """Menubar app showing the next upcoming Google Calendar meeting."""

    def __init__(self):
        super().__init__("Meetings", title="Loading…")
        self.menu = ["Refresh", None, "Quit"]

        try:
            get_credentials()
        except CalendarSetupError:
            self.title = "Set up calendar"
            return

        self.refresh_meeting()

    @rumps.clicked("Refresh")
    def refresh_clicked(self, _):
        self.refresh_meeting()

    @rumps.timer(60)  # refresh every 60 seconds
    def refresh_timer(self, _):
        self.refresh_meeting()

    def refresh_meeting(self):
        try:
            event = get_next_event()
        except CalendarSetupError:
            self.title = "Set up calendar"
        except Exception:
            self.title = "Calendar error"
        else:
            if event is None:
                self.title = "No meetings"
            else:
                self.title = format_next_event(event)


# Start the app when run as a script
if __name__ == "__main__":
    MeetingsApp().run()
