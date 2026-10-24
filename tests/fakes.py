from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field


class FakeChatModel(BaseChatModel):
    responses: list[AIMessage]
    seen: list = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "fake"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.seen.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=self.responses.pop(0))])


class FakeMessage:
    def __init__(self, text, message_id, chat, replies):
        self.text = text
        self.message_id = message_id
        self.chat = chat
        self._replies = replies

    async def reply_text(self, text):
        self._replies.append(text)
        return FakeMessage(text, self.message_id + 1000, self.chat, self._replies)


class FakeChat:
    def __init__(self, chat_id, chat_type):
        self.id = chat_id
        self.type = chat_type


class FakeUser:
    def __init__(self, full_name, is_bot=False):
        self.full_name = full_name
        self.is_bot = is_bot


class FakeUpdate:
    def __init__(self, text, chat_type="group", is_bot=False, message_id=10, chat_id=42, update_id=99):
        self.update_id = update_id
        self._replies = []
        chat = FakeChat(chat_id, chat_type)
        self.effective_chat = chat
        self.effective_user = FakeUser("Ada", is_bot=is_bot)
        self.effective_message = FakeMessage(text, message_id, chat, self._replies)
        self.message = self.effective_message


class FakeContext:
    def __init__(self, graph, history):
        self.application = type("App", (), {})()
        self.application.bot_data = {"graph": graph, "history": history}
