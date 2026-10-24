import pytest

from config import ConfigError, load_settings


def test_load_settings_reads_env(monkeypatch, tmp_path):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("GOOGLE_CREDENTIALS_PATH", str(tmp_path / "credentials.json"))
    monkeypatch.setenv("GOOGLE_TOKEN_PATH", str(tmp_path / "token.json"))
    monkeypatch.setenv("HISTORY_PATH", str(tmp_path / "history.sqlite"))
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    settings = load_settings()
    assert settings.openai_api_key == "test-key"
    assert settings.openai_model == "gpt-4.1-mini"
    assert settings.telegram_bot_token == "test-token"
    assert settings.history_path == tmp_path / "history.sqlite"


def test_load_settings_names_missing_openai_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    with pytest.raises(ConfigError, match="OPENAI_API_KEY"):
        load_settings()


def test_load_settings_strips_wrapped_secrets(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "״test-key״")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", '"test-token"')
    settings = load_settings()
    assert settings.openai_api_key == "test-key"
    assert settings.telegram_bot_token == "test-token"


def test_load_settings_names_missing_telegram_token(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    with pytest.raises(ConfigError, match="TELEGRAM_BOT_TOKEN"):
        load_settings()
