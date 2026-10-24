from integrations.google.calendar import delete_event, list_events


class FakeCalendar:
    def __init__(self, items=None):
        self.items = items or []
        self.last_list = None
        self.deleted = []

    def events(self):
        return self

    def list(self, **kwargs):
        self.last_list = kwargs
        items = self.items

        class Request:
            def execute(_self):
                return {"items": items}

        return Request()

    def delete(self, **kwargs):
        self.deleted.append((kwargs["calendarId"], kwargs["eventId"]))

        class Request:
            def execute(_self):
                return ""

        return Request()


def test_list_events_passes_time_window_and_query():
    service = FakeCalendar(
        items=[
            {
                "id": "e1",
                "summary": "Standup",
                "description": "daily",
                "start": {"dateTime": "2026-10-24T09:00:00Z"},
                "end": {"dateTime": "2026-10-24T09:15:00Z"},
            }
        ]
    )
    rows = list_events(
        "2026-10-24T00:00:00Z",
        "2026-10-25T00:00:00Z",
        query="Standup",
        service=service,
    )
    assert service.last_list["q"] == "Standup"
    assert service.last_list["timeMin"] == "2026-10-24T00:00:00Z"
    assert service.last_list["singleEvents"] is True
    assert rows[0]["summary"] == "Standup"


def test_delete_event_calls_delete():
    service = FakeCalendar()
    delete_event("e1", service=service)
    assert service.deleted == [("primary", "e1")]
