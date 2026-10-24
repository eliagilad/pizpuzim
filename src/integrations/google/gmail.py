import base64

from googleapiclient.discovery import build

from config import load_settings
from integrations.google.auth import load_credentials
from integrations.google.http import GoogleApiError, execute

BODY_LIMIT = 4000
SEARCH_LIMIT = 5


def gmail_service():
    return build("gmail", "v1", credentials=load_credentials(load_settings()), cache_discovery=False)


def _decode(data: str | None) -> str:
    if not data:
        return ""
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")


def _headers(payload: dict) -> dict[str, str]:
    found: dict[str, str] = {}
    for header in payload.get("headers") or []:
        name = str(header.get("name", "")).lower()
        if name in {"from", "to", "subject", "date"} and name not in found:
            found[name] = str(header.get("value", ""))
    return found


def _plain_text(payload: dict) -> str:
    mime = payload.get("mimeType", "")
    body = (payload.get("body") or {}).get("data")
    if mime == "text/plain" and body:
        return _decode(body)
    for part in payload.get("parts") or []:
        text = _plain_text(part)
        if text:
            return text
    if body and str(mime).startswith("text/"):
        return _decode(body)
    return ""


def _record(message: dict, include_body: bool) -> dict:
    payload = message.get("payload") or {}
    headers = _headers(payload)
    record = {
        "id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", ""),
        "snippet": message.get("snippet", ""),
    }
    if include_body:
        record["body"] = _plain_text(payload)[:BODY_LIMIT]
    return record


def search_messages(query: str, max_results: int = SEARCH_LIMIT, service=None) -> list[dict]:
    service = service or gmail_service()
    capped = min(max_results, SEARCH_LIMIT)
    listed = execute(service.users().messages().list(userId="me", q=query, maxResults=capped))
    rows = []
    for item in (listed.get("messages") or [])[:capped]:
        full = execute(
            service.users()
            .messages()
            .get(
                userId="me",
                id=item["id"],
                format="metadata",
                metadataHeaders=["From", "To", "Subject", "Date"],
            )
        )
        rows.append(_record(full, include_body=False))
    return rows


def get_message(message_id: str, service=None) -> dict:
    service = service or gmail_service()
    message = execute(service.users().messages().get(userId="me", id=message_id, format="full"))
    return _record(message, include_body=True)


def get_thread(thread_id: str, service=None) -> dict:
    service = service or gmail_service()
    thread = execute(service.users().threads().get(userId="me", id=thread_id, format="full"))
    return {
        "id": thread_id,
        "messages": [_record(item, include_body=True) for item in thread.get("messages") or []],
    }
