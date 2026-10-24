from langchain_core.tools import tool

from integrations.google.auth import GoogleAuthError
from integrations.google.calendar import (
    create_event as create_event_api,
)
from integrations.google.calendar import (
    delete_event as delete_event_api,
)
from integrations.google.calendar import (
    list_calendars as list_calendars_api,
)
from integrations.google.calendar import (
    list_events as list_events_api,
)
from integrations.google.calendar import (
    update_event as update_event_api,
)
from integrations.google.http import GoogleApiError


def _fail(exc: Exception) -> str:
    return f"Google error: {exc}"


def _line(event: dict) -> str:
    return (
        f"- id={event['id']} start={event['start']} end={event['end']} "
        f"summary={event['summary']} description={event['description']}"
    )


@tool
def list_calendars() -> str:
    """List the Google calendars the user can access."""
    try:
        rows = list_calendars_api()
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    if not rows:
        return "Calendar data\nNo calendars."
    lines = ["Calendar data"]
    for row in rows:
        lines.append(f"- id={row['id']} summary={row['summary']} primary={row['primary']}")
    return "\n".join(lines)


@tool
def list_events(time_min: str, time_max: str, query: str = "", max_results: int = 10, calendar_id: str = "primary") -> str:
    """List events between two RFC3339 times. query searches summary, description, location, and attendees."""
    try:
        rows = list_events_api(time_min, time_max, query=query, max_results=max_results, calendar_id=calendar_id)
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    if not rows:
        return "Calendar data\nNo events."
    return "Calendar data\n" + "\n".join(_line(row) for row in rows)


@tool
def create_event(summary: str, start: str, end: str, description: str = "", calendar_id: str = "primary") -> str:
    """Create an event. start and end are RFC3339 datetimes."""
    try:
        event = create_event_api(summary, start, end, description=description, calendar_id=calendar_id)
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    return "Calendar data\n" + _line(event)


@tool
def update_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
) -> str:
    """Update an event. Pass only the fields that should change. Times are RFC3339."""
    try:
        event = update_event_api(
            event_id,
            calendar_id=calendar_id,
            summary=summary,
            start=start,
            end=end,
            description=description,
        )
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    return "Calendar data\n" + _line(event)


@tool
def delete_event(event_id: str, calendar_id: str = "primary") -> str:
    """Delete an event by id."""
    try:
        delete_event_api(event_id, calendar_id=calendar_id)
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    return f"Calendar data\ndeleted {event_id}"
