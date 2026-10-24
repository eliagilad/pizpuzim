import asyncio
from types import SimpleNamespace

import pytest
from telegram.error import TelegramError

from history import History
from integrations.telegram import bot as bot_module
from integrations.telegram.bot import FAILURE_REPLY, handle_message
from tests.fakes import FakeContext, FakeUpdate


def _run(update, context):
    asyncio.run(handle_message(update, context))


def test_group_text_includes_saved_history_and_stores_the_reply(tmp_path, monkeypatch):
    history = History(tmp_path / "history.sqlite")
    history.add(42, 1, "Ben", "user", "earlier note")
    seen = {}

    def run_turn(graph, messages):
        seen["messages"] = messages
        return "Standup at 9"

    monkeypatch.setattr(bot_module, "run_turn", run_turn)
    update = FakeUpdate(text="What is on today?", chat_type="group", message_id=10, chat_id=42)
    context = FakeContext(graph=object(), history=history)
    _run(update, context)
    assert [message.content for message in seen["messages"]] == [
        "Ben: earlier note",
        "Ada: What is on today?",
    ]
    assert update._replies == ["Standup at 9"]
    stored = history.recent(42)
    assert stored[-1].role == "assistant"
    assert stored[-1].text == "Standup at 9"


def test_private_chat_is_ignored(tmp_path, monkeypatch):
    history = History(tmp_path / "history.sqlite")
    monkeypatch.setattr(bot_module, "run_turn", lambda graph, messages: "nope")
    update = FakeUpdate(text="hi", chat_type="private")
    context = FakeContext(graph=object(), history=history)
    _run(update, context)
    assert update._replies == []
    assert history.recent(update.effective_chat.id) == []


def test_bot_message_is_ignored(tmp_path, monkeypatch):
    history = History(tmp_path / "history.sqlite")
    monkeypatch.setattr(bot_module, "run_turn", lambda graph, messages: "nope")
    update = FakeUpdate(text="hi", is_bot=True)
    context = FakeContext(graph=object(), history=history)
    _run(update, context)
    assert update._replies == []


def test_duplicate_message_is_not_answered_twice(tmp_path, monkeypatch):
    history = History(tmp_path / "history.sqlite")
    calls = {"n": 0}

    def run_turn(graph, messages):
        calls["n"] += 1
        return "ok"

    monkeypatch.setattr(bot_module, "run_turn", run_turn)
    context = FakeContext(graph=object(), history=history)
    update = FakeUpdate(text="hi", message_id=5, chat_id=42)
    _run(update, context)
    _run(update, context)
    assert calls["n"] == 1
    assert update._replies == ["ok"]


def test_failure_reply_hides_exception_text(tmp_path, monkeypatch):
    history = History(tmp_path / "history.sqlite")

    def run_turn(graph, messages):
        raise RuntimeError("token sk-secret")

    monkeypatch.setattr(bot_module, "run_turn", run_turn)
    update = FakeUpdate(text="hi", chat_type="supergroup")
    context = FakeContext(graph=object(), history=history)
    _run(update, context)
    assert update._replies == [FAILURE_REPLY]
    assert "sk-secret" not in update._replies[0]


def test_telegram_send_error_is_swallowed(tmp_path, monkeypatch):
    history = History(tmp_path / "history.sqlite")
    monkeypatch.setattr(bot_module, "run_turn", lambda graph, messages: "hello")
    update = FakeUpdate(text="hi")

    async def boom(_text):
        raise TelegramError("send failed token")

    update.effective_message.reply_text = boom
    context = FakeContext(graph=object(), history=history)
    _run(update, context)
    assert update._replies == []


def test_service_command_builds_one_runtime(monkeypatch, tmp_path):
    from service import build_runtime

    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.sqlite"))
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(tmp_path / "missing.json"))
    monkeypatch.setenv("GOOGLE_TOKEN_PATH", str(tmp_path / "token.json"))
    runtime = build_runtime()
    assert runtime.history.path == tmp_path / "history.sqlite"
    assert runtime.token == "test-token"
    assert runtime.graph is not None
