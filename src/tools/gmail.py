from langchain_core.tools import tool

from integrations.google.auth import GoogleAuthError
from integrations.google.gmail import get_message, get_thread, search_messages
from integrations.google.http import GoogleApiError


def _fail(exc: Exception) -> str:
    return f"Google error: {exc}"


@tool
def search_email(query: str, max_results: int = 5) -> str:
    """Search the user's Gmail. query uses Gmail search syntax, such as from:ada@example.com newer_than:7d."""
    try:
        rows = search_messages(query, max_results=max_results)
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    if not rows:
        return "Email data\nNo messages."
    lines = ["Email data"]
    for row in rows:
        lines.append(
            f"- id={row['id']} thread_id={row['thread_id']} date={row['date']} from={row['from']} subject={row['subject']}"
        )
        if row.get("snippet"):
            lines.append(f"  {row['snippet']}")
    return "\n".join(lines)


@tool
def read_email(message_id: str) -> str:
    """Read one Gmail message by id, including its plain-text body."""
    try:
        message = get_message(message_id)
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    return "\n".join(
        [
            "Email data",
            f"id: {message['id']}",
            f"thread_id: {message['thread_id']}",
            f"from: {message['from']}",
            f"to: {message['to']}",
            f"subject: {message['subject']}",
            f"date: {message['date']}",
            "",
            message.get("body", ""),
        ]
    )


@tool
def read_thread(thread_id: str) -> str:
    """Read a Gmail thread by id, including each message body."""
    try:
        thread = get_thread(thread_id)
    except (GoogleAuthError, GoogleApiError) as exc:
        return _fail(exc)
    lines = ["Email data", f"thread_id: {thread['id']}"]
    for message in thread["messages"]:
        lines.append(
            f"\nid: {message['id']}\nfrom: {message['from']}\nsubject: {message['subject']}\ndate: {message['date']}\n{message.get('body', '')}"
        )
    return "\n".join(lines)
