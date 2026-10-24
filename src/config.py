from dataclasses import dataclass
from pathlib import Path
import os


class ConfigError(Exception):
    pass


_QUOTES = "\"'`״“”‘’«»"


def _clean(value: str) -> str:
    value = value.strip()
    while len(value) >= 2 and value[0] in _QUOTES and value[-1] in _QUOTES:
        value = value[1:-1].strip()
    return value


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    openai_model: str
    telegram_bot_token: str
    google_credentials_path: Path
    google_token_path: Path
    history_path: Path


def _required(name: str) -> str:
    value = _clean(os.environ.get(name, ""))
    if not value:
        raise ConfigError(f"Missing environment variable {name}")
    return value


def load_settings() -> Settings:
    return Settings(
        openai_api_key=_required("OPENAI_API_KEY"),
        openai_model=os.environ.get("OPENAI_MODEL", "").strip() or "gpt-4.1-mini",
        telegram_bot_token=_required("TELEGRAM_BOT_TOKEN"),
        google_credentials_path=Path(os.environ.get("GOOGLE_CREDENTIALS_PATH", "secrets/credentials.json")),
        google_token_path=Path(os.environ.get("GOOGLE_TOKEN_PATH", "secrets/token.json")),
        history_path=Path(os.environ.get("HISTORY_PATH", "data/history.sqlite")),
    )
