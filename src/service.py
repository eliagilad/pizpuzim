import logging
import sys
from dataclasses import dataclass

from dotenv import load_dotenv
from telegram.ext import Application, MessageHandler, filters

from agent.graph import build_app
from config import Settings, load_settings
from history import History
from integrations.google.auth import ensure_google, login
from integrations.telegram.bot import handle_message

logger = logging.getLogger(__name__)


@dataclass
class Runtime:
    settings: Settings
    history: History
    graph: object
    token: str


def _configure_logging() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("telegram").setLevel(logging.WARNING)


def build_runtime() -> Runtime:
    settings = load_settings()
    history = History(settings.history_path)
    graph = build_app(settings)
    return Runtime(settings=settings, history=history, graph=graph, token=settings.telegram_bot_token)


def run_bot(token: str, graph, history: History) -> None:
    application = Application.builder().token(token).build()
    application.bot_data["graph"] = graph
    application.bot_data["history"] = history
    application.add_handler(MessageHandler(filters.TEXT, handle_message))
    application.run_polling(allowed_updates=["message"])


def main(argv: list[str] | None = None) -> None:
    _configure_logging()
    load_dotenv(override=False)
    args = sys.argv[1:] if argv is None else argv
    settings = load_settings()
    if "--login" in args:
        login(settings)
        return
    ensure_google(settings)
    runtime = build_runtime()
    logger.info("service listening for Telegram group messages")
    run_bot(runtime.token, runtime.graph, runtime.history)


if __name__ == "__main__":
    main()
