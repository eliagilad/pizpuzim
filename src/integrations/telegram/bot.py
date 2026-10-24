import logging

from telegram.error import TelegramError

from agent.graph import run_turn
from history import History

logger = logging.getLogger(__name__)

FAILURE_REPLY = "Something went wrong. Try again in a moment."
GROUP_TYPES = {"group", "supergroup"}


def _log_failure(chat_id, update_id, error_name: str) -> None:
    logger.error("agent failed chat_id=%s update_id=%s error=%s", chat_id, update_id, error_name)


async def handle_message(update, context) -> None:
    chat = update.effective_chat
    message = update.effective_message
    user = update.effective_user
    if chat is None or message is None or not getattr(message, "text", None):
        return
    if chat.type not in GROUP_TYPES:
        return
    if user is not None and user.is_bot:
        return

    history: History = context.application.bot_data["history"]
    graph = context.application.bot_data["graph"]
    label = user.full_name if user is not None and user.full_name else "Someone"
    if not history.add(chat.id, message.message_id, label, "user", message.text):
        return

    update_id = getattr(update, "update_id", None)
    try:
        answer = run_turn(graph, history.as_model_messages(chat.id))
    except Exception as exc:
        _log_failure(chat.id, update_id, type(exc).__name__)
        try:
            await message.reply_text(FAILURE_REPLY)
        except TelegramError:
            _log_failure(chat.id, update_id, "TelegramError")
        return

    try:
        sent = await message.reply_text(answer)
    except TelegramError:
        _log_failure(chat.id, update_id, "TelegramError")
        return
    if sent is not None and getattr(sent, "message_id", None) is not None:
        history.add(chat.id, sent.message_id, "assistant", "assistant", answer)
