from datetime import datetime, timedelta, timezone

import pytest
from google.oauth2.credentials import Credentials

from integrations.google.auth import SCOPES, GoogleAuthError, load_credentials


def settings_with(credentials_path, token_path):
    from config import Settings

    return Settings(
        openai_api_key="test-key",
        openai_model="gpt-4.1-mini",
        telegram_bot_token="test-token",
        google_credentials_path=credentials_path,
        google_token_path=token_path,
        history_path=credentials_path.parent / "history.sqlite",
    )


def expired_token(path):
    creds = Credentials(
        token="old-access",
        refresh_token="refresh",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="cid",
        client_secret="csecret",
        scopes=SCOPES,
        expiry=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1),
    )
    path.write_text(creds.to_json())


def test_expired_token_is_refreshed_and_saved(tmp_path, monkeypatch):
    token = tmp_path / "token.json"
    expired_token(token)

    def fake_refresh(self, request):
        self.token = "new-access"
        self.expiry = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1)

    monkeypatch.setattr("integrations.google.auth.Credentials.refresh", fake_refresh)
    creds = load_credentials(settings_with(tmp_path / "credentials.json", token))
    assert creds.valid
    assert creds.token == "new-access"
    assert '"token": "new-access"' in token.read_text() or '"token":"new-access"' in token.read_text().replace(" ", "")
    assert oct(token.stat().st_mode & 0o777) == "0o600"


def test_missing_client_file_raises(tmp_path):
    with pytest.raises(GoogleAuthError, match="credentials"):
        load_credentials(settings_with(tmp_path / "missing.json", tmp_path / "token.json"))
