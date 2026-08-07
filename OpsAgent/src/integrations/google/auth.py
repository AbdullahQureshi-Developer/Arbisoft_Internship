import hashlib
import hmac
import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

logger = logging.getLogger(__name__)

SECRET_KEY = os.getenv("AUTH_SECRET_KEY", "opsagent-secret-key-google-oauth-2026")
SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"


def generate_auth_token(user_id: str, expires_in: int = 600) -> str:
    """Mints a short-lived HMAC signed token containing user_id and expiration timestamp."""
    expires_at = int(time.time()) + expires_in
    payload = f"{user_id}:{expires_at}"
    sig = hmac.new(
        SECRET_KEY.encode("utf-8"), payload.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    return f"{user_id}:{expires_at}:{sig}"


def verify_auth_token(token: str) -> Optional[str]:
    """Verifies HMAC signature and expiration of an auth token, returning user_id if valid."""
    try:
        parts = token.split(":")
        if len(parts) != 3:
            return None
        user_id, expires_at_str, sig = parts
        expires_at = int(expires_at_str)
        if time.time() > expires_at:
            logger.warning(f"Auth token for user `{user_id}` has expired.")
            return None

        expected_payload = f"{user_id}:{expires_at_str}"
        expected_sig = hmac.new(
            SECRET_KEY.encode("utf-8"), expected_payload.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        if hmac.compare_digest(sig, expected_sig):
            return user_id
        logger.warning(f"Invalid HMAC signature on auth token for user `{user_id}`.")
        return None
    except Exception as e:
        logger.error(f"Failed to verify auth token: {e}")
        return None


def get_google_credentials() -> Any:
    """
    Retrieves or refreshes Google OAuth2 credentials using token.json or credentials.json.
    """
    from google_auth_oauthlib.flow import InstalledAppFlow

    creds = None
    if TOKEN_PATH.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_PATH), SCOPES)
        except Exception:
            creds = None

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception:
                creds = None

        if not creds:
            if not CREDENTIALS_PATH.exists():
                raise FileNotFoundError(
                    f"Google OAuth client credentials file not found at {CREDENTIALS_PATH}."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CREDENTIALS_PATH), SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save credentials for next run
        with open(TOKEN_PATH, "w", encoding="utf-8") as token_file:
            token_file.write(creds.to_json())

    return creds


def get_user_google_credentials(user_id: str) -> Optional[Any]:
    """
    Retrieves or refreshes a stored per-user Google OAuth2 credential from SQLite.
    Returns None if the user hasn't authenticated their Google account.
    """
    from src.memory.store import get_user_google_token, save_user_google_token

    token_json_str = get_user_google_token(user_id)
    if not token_json_str:
        return None

    try:
        token_data = json.loads(token_json_str)
        creds = Credentials.from_authorized_user_info(token_data, SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            save_user_google_token(user_id=user_id, token_json=creds.to_json())
        return creds if creds and creds.valid else None
    except Exception as e:
        logger.error(f"Error restoring Google credentials for user `{user_id}`: {e}")
        return None


def get_calendar_service(user_id: Optional[str] = None) -> Any:
    """
    Returns an authorized Google Calendar API service object for user_id.
    If user_id is provided, strictly uses per-user credentials (returns None if user not authenticated).
    If user_id is None, falls back to host credentials.
    """
    from googleapiclient.discovery import build

    if user_id:
        creds = get_user_google_credentials(user_id)
        if not creds:
            logger.info(f"No Google credentials stored for user `{user_id}`.")
            return None
    else:
        creds = get_google_credentials()

    if not creds:
        return None

    return build("calendar", "v3", credentials=creds)
