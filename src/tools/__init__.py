from tools.calendar import create_event, delete_event, list_calendars, list_events, update_event
from tools.gmail import read_email, read_thread, search_email

AGENT_TOOLS = [
    search_email,
    read_email,
    read_thread,
    list_calendars,
    list_events,
    create_event,
    update_event,
    delete_event,
]
