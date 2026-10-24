from googleapiclient.discovery import build

from config import load_settings
from integrations.google.auth import load_credentials
from integrations.google.http import execute

EVENT_LIMIT = 10
TEXT_LIMIT = 4000


def calendar_service():
    return build("calendar", "v3", credentials=load_credentials(load_settings()), cache_discovery=False)


def _when(value: dict | None) -> str:
    if not value:
        return ""
    return str(value.get("dateTime") or value.get("date") or "")


def _event(item: dict) -> dict:
    description = str(item.get("description") or "")[:TEXT_LIMIT]
    return {
        "id": item.get("id", ""),
        "summary": item.get("summary", ""),
        "description": description,
        "start": _when(item.get("start")),
        "end": _when(item.get("end")),
        "calendar_id": item.get("organizer", {}).get("email", ""),
    }


def list_calendars(service=None) -> list[dict]:
    service = service or calendar_service()
    data = execute(service.calendarList().list())
    return [
        {
            "id": item.get("id", ""),
            "summary": item.get("summary", ""),
            "primary": bool(item.get("primary", False)),
        }
        for item in data.get("items") or []
    ]


def list_events(
    time_min: str,
    time_max: str,
    query: str = "",
    max_results: int = EVENT_LIMIT,
    calendar_id: str = "primary",
    service=None,
) -> list[dict]:
    service = service or calendar_service()
    data = execute(
        service.events().list(
            calendarId=calendar_id,
            timeMin=time_min,
            timeMax=time_max,
            q=query,
            maxResults=min(max_results, EVENT_LIMIT),
            singleEvents=True,
            orderBy="startTime",
        )
    )
    return [_event(item) for item in data.get("items") or []]


def create_event(
    summary: str,
    start: str,
    end: str,
    description: str = "",
    calendar_id: str = "primary",
    service=None,
) -> dict:
    service = service or calendar_service()
    created = execute(
        service.events().insert(
            calendarId=calendar_id,
            body={
                "summary": summary,
                "description": description,
                "start": {"dateTime": start},
                "end": {"dateTime": end},
            },
        )
    )
    return _event(created)


def update_event(
    event_id: str,
    calendar_id: str = "primary",
    summary: str | None = None,
    start: str | None = None,
    end: str | None = None,
    description: str | None = None,
    service=None,
) -> dict:
    service = service or calendar_service()
    body: dict = {}
    if summary is not None:
        body["summary"] = summary
    if start is not None:
        body["start"] = {"dateTime": start}
    if end is not None:
        body["end"] = {"dateTime": end}
    if description is not None:
        body["description"] = description
    updated = execute(service.events().patch(calendarId=calendar_id, eventId=event_id, body=body))
    return _event(updated)


def delete_event(event_id: str, calendar_id: str = "primary", service=None) -> None:
    service = service or calendar_service()
    execute(service.events().delete(calendarId=calendar_id, eventId=event_id))
