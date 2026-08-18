"""Unit tests for the pure helper functions in app."""

from datetime import datetime, timedelta, timezone
from unittest import mock

import app as app_module
from app import (
    MAX_TITLE_LEN,
    MeetingsApp,
    _to_teams_app_url,
    _to_zoom_app_url,
    format_countdown,
    format_next_event,
)

UTC = timezone.utc


def _in(**kwargs) -> datetime:
    """A UTC datetime offset from now by the given timedelta kwargs."""
    return datetime.now(UTC) + timedelta(**kwargs)


class TestFormatCountdown:
    def test_past_event_is_now(self):
        assert format_countdown(_in(minutes=-5)) == "[now]"

    def test_minutes_only(self):
        # Implementation rounds up via +1: floor(secs/60)+1. 9m30s -> [10m].
        assert format_countdown(_in(minutes=9, seconds=30)) == "[10m]"

    def test_hours_and_minutes_zero_padded(self):
        # 2h4m30s -> floor=124, +1=125 -> 2h 05m.
        assert format_countdown(_in(hours=2, minutes=4, seconds=30)) == "[2h 05m]"

    def test_naive_datetime_treated_as_utc(self):
        naive = (datetime.now(UTC) + timedelta(minutes=9, seconds=30)).replace(tzinfo=None)
        assert format_countdown(naive) == "[10m]"


class TestFormatNextEvent:
    def test_all_day(self):
        event = {"summary": "Holiday", "all_day": True, "start": None}
        assert format_next_event(event) == "Holiday · All day"

    def test_long_title_truncated(self):
        title = "A" * 50
        event = {"summary": title, "all_day": False, "start": _in(minutes=30)}
        out = format_next_event(event)
        displayed = out.split(" · ")[0]
        assert len(displayed) == MAX_TITLE_LEN
        assert displayed.endswith("…")

    def test_short_title_not_truncated(self):
        event = {"summary": "Standup", "all_day": False, "start": _in(minutes=30)}
        assert format_next_event(event).startswith("Standup · ")

    def test_includes_time_and_countdown(self):
        event = {"summary": "Sync", "all_day": False, "start": _in(minutes=30)}
        out = format_next_event(event)
        assert "·" in out
        assert out.endswith("m]")


class TestToZoomAppUrl:
    def test_basic_conversion(self):
        out = _to_zoom_app_url("https://us.zoom.us/j/123456789")
        assert out == "zoommtg://us.zoom.us/join?action=join&confno=123456789"

    def test_with_password(self):
        out = _to_zoom_app_url("https://us.zoom.us/j/123456789?pwd=secret")
        assert out == "zoommtg://us.zoom.us/join?action=join&confno=123456789&pwd=secret"

    def test_meeting_id_starting_with_j(self):
        out = _to_zoom_app_url("https://us.zoom.us/j/j99")
        assert out == "zoommtg://us.zoom.us/join?action=join&confno=j99"


class TestToTeamsAppUrl:
    def test_basic_conversion(self):
        url = "https://teams.microsoft.com/l/meetup-join/abc"
        assert _to_teams_app_url(url) == "msteams:/l/meetup-join/abc"

    def test_host_not_left_in_path(self):
        url = "https://teams.microsoft.com/l/x?u=https://other"
        assert _to_teams_app_url(url) == "msteams:/l/x?u=https://other"


def _ns_titles(menu) -> list[str]:
    """Titles of the visible NSMenu items (the layer where the duplicate showed)."""
    return [item.title() for item in menu._menu.itemArray()]


class TestQuitNotDuplicatedAtBoot:
    """Regression: booting the app then letting rumps add its quit button must
    not leave two "Quit" items in the visible NSMenu (issue: duplicate Quit at
    launch that self-healed after the first minute refresh)."""

    def test_single_quit_after_boot_and_framework_quit_add(self):
        # Drive the real boot path: __init__ -> refresh_meeting -> menu rebuild.
        with mock.patch.object(app_module, "get_credentials"), mock.patch.object(
            app_module, "get_next_event", return_value=None
        ):
            app = MeetingsApp()

        # After construction the menu should carry exactly one Quit.
        assert _ns_titles(app.menu).count("Quit") == 1

        # rumps' initializeStatusBar() adds the framework quit button at run()
        # time. With quit_button=None it is disabled, so nothing extra is added.
        assert app.quit_button is None

        # Belt-and-braces: even if the framework add ran, our menu owns Quit and
        # a subsequent refresh (clear + rebuild) keeps it at exactly one.
        app.refresh_meeting()
        assert _ns_titles(app.menu).count("Quit") == 1
