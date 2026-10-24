import logging
from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from config import Settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
]


class GoogleAuthError(Exception):
    pass


def _write_token(path: Path, creds: Credentials) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(creds.to_json())
    path.chmod(0o600)


def load_credentials(settings: Settings) -> Credentials:
    token_path = settings.google_token_path
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
    if creds and creds.valid:
        return creds
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
        _write_token(token_path, creds)
        return creds
    if not settings.google_credentials_path.exists():
        raise GoogleAuthError(f"Google credentials file not found: {settings.google_credentials_path}")
    raise GoogleAuthError("Google login required. Run: pizpuzim --login")


def login(settings: Settings) -> None:
    path = settings.google_credentials_path
    if not path.exists():
        raise GoogleAuthError(f"Google credentials file not found: {path}")
    flow = InstalledAppFlow.from_client_secrets_file(str(path), SCOPES)
    creds = flow.run_local_server(port=0)
    _write_token(settings.google_token_path, creds)


def ensure_google(settings: Settings) -> None:
    if not settings.google_credentials_path.exists():
        logger.warning(
            "Google client file missing at %s. Gmail and Calendar stay unavailable until it is added.",
            settings.google_credentials_path,
        )
        return
    try:
        load_credentials(settings)
    except GoogleAuthError:
        logger.info("Starting Google login")
        login(settings)
