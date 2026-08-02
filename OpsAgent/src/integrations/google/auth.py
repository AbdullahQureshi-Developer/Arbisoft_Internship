import os
from pathlib import Path
from typing import Any

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]

BASE_DIR = Path(__file__).resolve().parent
CREDENTIALS_PATH = BASE_DIR / "credentials.json"
TOKEN_PATH = BASE_DIR / "token.json"


def get_google_credentials() -> Any:
    """
    Retrieves or refreshes Google OAuth2 credentials using token.json or credentials.json.
    """
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
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


def get_calendar_service() -> Any:
    """
    Returns an authorized Google Calendar API service object.
    """
    from googleapiclient.discovery import build

    creds = get_google_credentials()
    return build("calendar", "v3", credentials=creds)
