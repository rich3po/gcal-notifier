"""Unit tests for the pure helper functions in calendar_client."""

from datetime import datetime, timezone

from calendar_client import (
    _extract_teams_link,
    _extract_zoom_link,
    _is_declined,
    _parse_event_start,
)


class TestParseEventStart:
    def test_timed_event_with_z_suffix(self):
        dt, all_day = _parse_event_start({"dateTime": "2026-06-05T14:30:00Z"})
        assert all_day is False
        assert dt == datetime(2026, 6, 5, 14, 30, tzinfo=timezone.utc)

    def test_timed_event_with_offset(self):
        dt, all_day = _parse_event_start({"dateTime": "2026-06-05T14:30:00+01:00"})
        assert all_day is False
        assert dt.utcoffset().total_seconds() == 3600

    def test_all_day_event(self):
        dt, all_day = _parse_event_start({"date": "2026-06-05"})
        assert all_day is True
        assert dt == datetime(2026, 6, 5, tzinfo=timezone.utc)


class TestExtractZoomLink:
    def test_from_conference_data(self):
        event = {
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://us.zoom.us/j/123456"}
                ]
            }
        }
        assert _extract_zoom_link(event) == "https://us.zoom.us/j/123456"

    def test_non_video_entry_point_ignored(self):
        event = {
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "phone", "uri": "https://us.zoom.us/j/123456"}
                ]
            }
        }
        assert _extract_zoom_link(event) is None

    def test_from_location(self):
        event = {"location": "https://corp.zoom.us/j/987654321?pwd=abc"}
        assert _extract_zoom_link(event) == "https://corp.zoom.us/j/987654321?pwd=abc"

    def test_from_description(self):
        event = {"description": "Join here: https://zoom.us/j/555 cheers"}
        assert _extract_zoom_link(event) == "https://zoom.us/j/555"

    def test_conference_data_takes_priority_over_location(self):
        event = {
            "conferenceData": {
                "entryPoints": [
                    {"entryPointType": "video", "uri": "https://zoom.us/j/conf"}
                ]
            },
            "location": "https://zoom.us/j/loc",
        }
        assert _extract_zoom_link(event) == "https://zoom.us/j/conf"

    def test_no_zoom_link(self):
        assert _extract_zoom_link({}) is None
        assert _extract_zoom_link({"location": "Room 4B"}) is None


class TestExtractTeamsLink:
    def test_from_location(self):
        url = "https://teams.microsoft.com/l/meetup-join/abc123"
        assert _extract_teams_link({"location": url}) == url

    def test_from_description(self):
        url = "https://teams.microsoft.com/l/meetup-join/xyz"
        event = {"description": f"<a href=\"{url}\">Join</a>"}
        assert _extract_teams_link(event) == url

    def test_location_takes_priority(self):
        loc = "https://teams.microsoft.com/l/meetup-join/loc"
        desc = "https://teams.microsoft.com/l/meetup-join/desc"
        event = {"location": loc, "description": desc}
        assert _extract_teams_link(event) == loc

    def test_no_teams_link(self):
        assert _extract_teams_link({}) is None
        assert _extract_teams_link({"location": "https://zoom.us/j/1"}) is None


class TestIsDeclined:
    def test_self_declined(self):
        event = {"attendees": [{"self": True, "responseStatus": "declined"}]}
        assert _is_declined(event) is True

    def test_self_accepted(self):
        event = {"attendees": [{"self": True, "responseStatus": "accepted"}]}
        assert _is_declined(event) is False

    def test_other_attendee_declined_ignored(self):
        event = {"attendees": [{"self": False, "responseStatus": "declined"}]}
        assert _is_declined(event) is False

    def test_no_attendees(self):
        assert _is_declined({}) is False
