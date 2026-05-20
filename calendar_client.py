"""Google Calendar read-only access and next-event lookup."""

import re
from datetime import datetime, timezone
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
CREDENTIALS_FILE = Path("credentials.json")
TOKEN_FILE = Path("token.json")


class CalendarSetupError(Exception):
    """Raised when OAuth credentials are missing or invalid."""


def get_credentials() -> Credentials:
    """Load or obtain OAuth credentials with calendar read-only scope."""
    if not CREDENTIALS_FILE.exists():
        raise CalendarSetupError(
            f"Missing {CREDENTIALS_FILE}. See README.md for setup instructions."
        )

    creds = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def _parse_event_start(start: dict) -> tuple[datetime, bool]:
    """Return (start datetime, is_all_day)."""
    if "dateTime" in start:
        dt = datetime.fromisoformat(start["dateTime"].replace("Z", "+00:00"))
        return dt, False
    # All-day events use date only (YYYY-MM-DD)
    dt = datetime.fromisoformat(start["date"]).replace(tzinfo=timezone.utc)
    return dt, True


def _extract_zoom_link(event: dict) -> str | None:
    """Return the Zoom join URL from an event, or None if not a Zoom call.

    Checks in priority order:
    1. conferenceData.entryPoints (Zoom Google Calendar Add-On)
    2. location field (bare URL)
    3. description field (HTML/text body)
    """
    zoom_re = re.compile(r"https://[a-z0-9.]*zoom\.us/j/[^\s\"'<>]+")

    # 1. Structured conferenceData (most reliable)
    for entry in event.get("conferenceData", {}).get("entryPoints", []):
        if entry.get("entryPointType") == "video":
            uri = entry.get("uri", "")
            if zoom_re.match(uri):
                return uri

    # 2. location field
    location = event.get("location", "")
    match = zoom_re.search(location)
    if match:
        return match.group()

    # 3. description field (may be HTML)
    description = event.get("description", "")
    match = zoom_re.search(description)
    if match:
        return match.group()

    return None


def _extract_teams_link(event: dict) -> str | None:
    """Return the MS Teams join URL from an event, or None if not a Teams call.

    Teams links appear in description and/or location as
    https://teams.microsoft.com/l/meetup-join/...
    """
    teams_re = re.compile(r"https://teams\.microsoft\.com/l/meetup-join/[^\s\"'<>]+")

    for field in (event.get("location", ""), event.get("description", "")):
        match = teams_re.search(field)
        if match:
            return match.group()

    return None


def get_next_event() -> dict | None:
    """Return the next upcoming primary-calendar event, or None."""
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    result = (
        service.events()
        .list(
            calendarId="primary",
            timeMin=now,
            maxResults=10,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    items = result.get("items", [])
    timed_events = []
    for event in items:
        start, all_day = _parse_event_start(event["start"])
        if all_day:
            continue
        timed_events.append((start, event))
        if len(timed_events) == 2:
            break

    if not timed_events:
        return None

    now_dt = datetime.now(timezone.utc)
    first_start, first_event = timed_events[0]

    if len(timed_events) == 2:
        second_start, second_event = timed_events[1]
        first_is_active = first_start <= now_dt
        next_starts_soon = (second_start - now_dt).total_seconds() <= 900
        if first_is_active and next_starts_soon:
            first_start, first_event = second_start, second_event

    return {
        "summary": first_event.get("summary", "(No title)"),
        "start": first_start,
        "all_day": False,
        "zoom_link": _extract_zoom_link(first_event),
        "teams_link": _extract_teams_link(first_event),
    }
