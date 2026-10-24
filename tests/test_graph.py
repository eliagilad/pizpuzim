import os
import time
from datetime import datetime, timezone
from unittest.mock import patch
from zoneinfo import ZoneInfo

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from agent.graph import AGENT_TOOLS, SYSTEM_PROMPT, build_graph, run_turn
from agent.prompts import SYSTEM_PROMPT as PROMPT_FROM_MODULE
from tests.fakes import FakeChatModel


def test_run_turn_returns_model_text_when_no_tool_call():
    model = FakeChatModel(responses=[AIMessage(content="hello")])
    graph = build_graph(model, tools=[])
    assert run_turn(graph, [HumanMessage(content="Ada: hi")]) == "hello"


def test_system_prompt_treats_email_as_untrusted():
    assert SYSTEM_PROMPT is PROMPT_FROM_MODULE
    lowered = SYSTEM_PROMPT.lower()
    assert "email" in lowered
    assert "must not" in lowered
    assert "history" in lowered


def test_system_message_includes_current_date_and_exact_time():
    israel = ZoneInfo("Asia/Jerusalem")
    instants = [
        datetime(2026, 10, 23, 19, 54, 7, tzinfo=timezone.utc),
        datetime(2026, 1, 15, 20, 54, 7, tzinfo=timezone.utc),
    ]
    model = FakeChatModel(responses=[AIMessage(content="ok"), AIMessage(content="ok")])
    graph = build_graph(model, tools=[])
    previous = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"
    time.tzset()
    try:
        for instant in instants:
            with patch("agent.prompts.datetime") as clock:
                clock.now.side_effect = lambda tz=None, instant=instant: (
                    instant if tz is None else instant.astimezone(tz)
                )
                run_turn(graph, [HumanMessage(content="Ada: hi")])
            expected = instant.astimezone(israel).strftime("%Y-%m-%d %H:%M:%S %z")
            assert model.seen[-1][0].content.endswith(f"Current date and time in Israel: {expected}\n")
    finally:
        if previous is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = previous
        time.tzset()


def test_run_turn_sends_group_history_to_the_model():
    model = FakeChatModel(responses=[AIMessage(content="standup at 9")])
    graph = build_graph(model, tools=[])
    history = [
        HumanMessage(content="Ada: what is on today?"),
        AIMessage(content="Checking."),
        HumanMessage(content="Ben: and tomorrow?"),
    ]
    assert run_turn(graph, history) == "standup at 9"
    sent = model.seen[0]
    assert isinstance(sent[0], SystemMessage)
    assert [message.content for message in sent[1:]] == [
        "Ada: what is on today?",
        "Checking.",
        "Ben: and tomorrow?",
    ]


def test_agent_executes_search_email_then_answers():
    model = FakeChatModel(
        responses=[
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "search_email",
                        "args": {"query": "newer_than:1d"},
                        "id": "call-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="You have 1 recent email."),
        ]
    )
    graph = build_graph(model, tools=AGENT_TOOLS)
    with patch(
        "tools.gmail.search_messages",
        return_value=[{"id": "m1", "thread_id": "t1", "subject": "Hi", "from": "a@b.c", "date": "today", "snippet": "hi"}],
    ):
        assert run_turn(graph, [HumanMessage(content="Ada: Any new mail?")]) == "You have 1 recent email."
