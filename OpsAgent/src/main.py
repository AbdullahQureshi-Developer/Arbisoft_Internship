import os
import logging
from contextlib import asynccontextmanager
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow
from src.integrations.google.auth import CREDENTIALS_PATH, SCOPES
from src.memory.store import init_db, save_user_google_token

load_dotenv()

# Allow HTTP for local OAuth testing
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


# Fixed PKCE verifier for stateless local OAuth redirect flow (RFC 7636 compliant 50-char string)
FIXED_PKCE_VERIFIER = "OpsAgentGoogleOAuthSecretVerifierKey12345678901234567890"


@app.get("/auth/google")
def google_auth_login(user_id: str, request: Request):
    """Initiates Google OAuth authorization flow for a specific Slack user_id."""
    if not CREDENTIALS_PATH.exists():
        raise HTTPException(
            status_code=404, detail="Google credentials.json file not found on server."
        )

    redirect_uri = str(request.url_for("google_auth_callback"))
    flow = Flow.from_client_secrets_file(
        str(CREDENTIALS_PATH),
        scopes=SCOPES,
        redirect_uri=redirect_uri,
    )
    flow.code_verifier = FIXED_PKCE_VERIFIER
    auth_url, _ = flow.authorization_url(
        prompt="consent", access_type="offline", state=user_id
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
        flow.code_verifier = FIXED_PKCE_VERIFIER
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
