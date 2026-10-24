from langchain_core.messages import AIMessage, HumanMessage

from history import History


def test_recent_history_is_oldest_first_and_ignores_duplicates(tmp_path):
    store = History(tmp_path / "history.sqlite")
    assert store.add(7, 1, "Ada", "user", "earlier")
    assert store.add(7, 2, "Ben", "user", "later")
    assert store.add(7, 1, "Ada", "user", "earlier") is False
    rows = store.recent(7)
    assert [row.message_id for row in rows] == [1, 2]
    assert rows[0].text == "earlier"


def test_model_messages_name_the_speaker(tmp_path):
    store = History(tmp_path / "history.sqlite")
    store.add(7, 1, "Ada", "user", "hello")
    store.add(7, 2, "assistant", "assistant", "hi Ada")
    messages = store.as_model_messages(7)
    assert isinstance(messages[0], HumanMessage)
    assert messages[0].content == "Ada: hello"
    assert isinstance(messages[1], AIMessage)
    assert messages[1].content == "hi Ada"


def test_recent_history_keeps_the_newest_window(tmp_path):
    store = History(tmp_path / "history.sqlite")
    for index in range(1, 6):
        store.add(3, index, "Ada", "user", f"m{index}")
    rows = store.recent(3, limit=2)
    assert [row.text for row in rows] == ["m4", "m5"]
