import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from src.integrations.google.auth import (
    CREDENTIALS_PATH,
    SCOPES,
    verify_auth_token,
)
from src.memory.store import init_db, save_user_google_token

import secrets
import time
from typing import Dict, Optional, Tuple

load_dotenv()

# Allow HTTP for local OAuth testing only when running in dev/local environments
if (
    os.getenv("ENVIRONMENT", os.getenv("ENV", "local")).lower()
    in ("local", "dev", "test")
    or os.getenv("DEBUG", "false").lower() == "true"
):
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("opsagent")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for database initialization and cleanup."""
    logger.info("Initializing database tables...")
    init_db()
    yield
    logger.info("Shutting down OpsAgent backend...")


app = FastAPI(
    title="OpsAgent Backend API",
    description="Slack-native AI assistant backend and webhook router",
    version="0.1.0",
    lifespan=lifespan,
)


@app.get("/")
def read_root():
    return {"status": "online", "app": "OpsAgent", "version": "0.1.0"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


# Per-flow PKCE verifier store keyed by state: (code_verifier, expires_at)
PENDING_PKCE_VERIFIERS: Dict[str, Tuple[str, float]] = {}


@app.get("/auth/google")
def google_auth_login(
    request: Request, token: Optional[str] = None, user_id: Optional[str] = None
):
    """Initiates Google OAuth authorization flow after verifying HMAC signed user token."""
    if not CREDENTIALS_PATH.exists():
        raise HTTPException(
            status_code=404, detail="Google credentials.json file not found on server."
        )

    resolved_user_id = None
    if token:
        resolved_user_id = verify_auth_token(token)
        if not resolved_user_id:
            raise HTTPException(
                status_code=401, detail="Invalid or expired authorization token."
            )
    elif user_id:
        # Fallback for direct user_id parameter in development/tests
        resolved_user_id = user_id

    if not resolved_user_id:
        raise HTTPException(
            status_code=400, detail="Missing required authorization token or user_id."
        )

    redirect_uri = str(request.url_for("google_auth_callback"))
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    code_verifier = secrets.token_urlsafe(32)
    PENDING_PKCE_VERIFIERS[resolved_user_id] = (code_verifier, time.time() + 600)

    flow.code_verifier = code_verifier
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", state=resolved_user_id
    )
    return RedirectResponse(auth_url)


@app.get("/auth/google/callback", response_class=HTMLResponse)
def google_auth_callback(request: Request, code: str, state: str):
    """Handles Google OAuth callback, exchanges code for token, and saves to user_id SQLite record."""
    user_id = state
    redirect_uri = str(request.url_for("google_auth_callback"))
    try:
        flow = Flow.from_client_secrets_file(
            str(CREDENTIALS_PATH),
            scopes=SCOPES,
            redirect_uri=redirect_uri,
        )
        pkce_entry = PENDING_PKCE_VERIFIERS.pop(user_id, None)
        if pkce_entry and time.time() < pkce_entry[1]:
            flow.code_verifier = pkce_entry[0]

        flow.fetch_token(code=code)
        creds = flow.credentials
        save_user_google_token(user_id=user_id, token_json=creds.to_json())
        return f"""
        <html>
            <body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                <h1 style="color: #2e7d32;">✅ Google Calendar Connected!</h1>
                <p>Slack User <code>{user_id}</code> is now authenticated with Google Calendar.</p>
                <p>You can close this tab and return to Slack.</p>
            </body>
        </html>
        """
    except Exception as e:
        logger.error(f"Failed to complete Google OAuth for user {user_id}: {e}")
        raise HTTPException(status_code=500, detail=f"OAuth Authorization Failed: {e}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
