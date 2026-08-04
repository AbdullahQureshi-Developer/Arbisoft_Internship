import os
import logging
import requests
from typing import Callable, Optional
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from src.hooks.logging_hook import log_call
from src.marshal.graph import process_slack_message
from src.agents.reminder_agent import start_reminder_scheduler

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("slack_bot")

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN", "")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET", "")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN", "")

# Ensure Bolt uses token mode
client_id = os.environ.pop("SLACK_CLIENT_ID", None)
client_secret = os.environ.pop("SLACK_CLIENT_SECRET", None)

is_valid_token = bool(SLACK_BOT_TOKEN and SLACK_BOT_TOKEN.startswith("xoxb-"))

app = App(
    token=SLACK_BOT_TOKEN if is_valid_token else "xoxb-dummy-token",
    signing_secret=SLACK_SIGNING_SECRET,
    token_verification_enabled=is_valid_token,
)

if client_id:
    os.environ["SLACK_CLIENT_ID"] = client_id
if client_secret:
    os.environ["SLACK_CLIENT_SECRET"] = client_secret


def download_slack_file(url_private_download: str, filename: str = "document") -> bytes:
    """Downloads a private file from Slack using Bot token authentication."""
    headers = {"Authorization": f"Bearer {SLACK_BOT_TOKEN}"}
    response = requests.get(url_private_download, headers=headers, allow_redirects=True, timeout=30)
    response.raise_for_status()

    content = response.content
    if not content:
        raise ValueError(f"Downloaded file '{filename}' from Slack is empty (0 bytes).")

    logger.info(f"Downloaded {len(content)} bytes for {filename}")
    return content


@log_call
def handle_slack_message(event: dict, say: Callable) -> str:
    """Core handler routing incoming Slack messages through Marshal LangGraph."""
    thread_ts = event.get("thread_ts", event.get("ts"))
    user_id = event.get("user", "unknown_user")
    channel_id = event.get("channel", "unknown_channel")
    text = event.get("text", "")
    
    # Ignore bot's own messages to prevent loops
    if event.get("bot_id") or event.get("subtype") == "bot_message":
        logger.info("Ignoring message sent by bot itself.")
        return ""

    file_bytes = None
    file_name = None

    files = event.get("files", [])
    if files and isinstance(files, list):
        first_file = files[0]
        url_download = first_file.get("url_private_download") or first_file.get("url_private")
        filename = first_file.get("name", "document.pdf")
        if url_download and is_valid_token:
            logger.info(f"Downloading file attachment '{filename}' from {url_download}")
            try:
                file_bytes = download_slack_file(url_download, filename=filename)
                file_name = filename
            except Exception as e:
                logger.error(f"Failed to download attachment '{filename}': {e}")
                file_bytes = b""
                file_name = filename
        
    logger.info(f"Processing incoming message from {user_id} in {channel_id}: '{text}' (file={file_name})")
    
    # Process through Marshal LangGraph
    response_text = process_slack_message(
        message_text=text,
        channel_id=channel_id,
        user_id=user_id,
        thread_ts=thread_ts,
        file_bytes=file_bytes,
        file_name=file_name,
    )
    
    logger.info(f"Sending response back to Slack channel {channel_id}: {response_text[:60]}...")
    say(text=response_text, thread_ts=thread_ts)
    return response_text


@app.middleware
def log_incoming_payload(req, resp, next):
    """Global middleware logging every event received from Slack."""
    event_type = req.body.get("event", {}).get("type", req.body.get("type"))
    logger.info(f"Slack Event received: {event_type}")
    return next()


@app.event("app_mention")
def handle_app_mention_events(body: dict, say: Callable):
    event = body.get("event", {})
    handle_slack_message(event=event, say=say)


@app.event("message")
def handle_all_messages(body: dict, say: Callable):
    event = body.get("event", {})
    handle_slack_message(event=event, say=say)


@app.event("file_shared")
def handle_file_shared_events(body: dict, say: Callable):
    event = body.get("event", {})
    handle_slack_message(event=event, say=say)



def start_socket_mode():
    """Start the app in Socket Mode and launch background reminder scheduler."""
    if not SLACK_APP_TOKEN:
        logger.error("SLACK_APP_TOKEN is missing in environment variables.")
        return
        
    start_reminder_scheduler(slack_say=app.client.chat_postMessage, interval_seconds=15)
    
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    logger.info("Starting Slack Bolt app in Socket Mode...")
    handler.start()


if __name__ == "__main__":
    start_socket_mode()
