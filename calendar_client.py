"""Google Calendar read-only access and next-event lookup."""

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
            maxResults=1,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )

    items = result.get("items", [])
    if not items:
        return None

    event = items[0]
    start, all_day = _parse_event_start(event["start"])
    return {
        "summary": event.get("summary", "(No title)"),
        "start": start,
        "all_day": all_day,
    }
