import sys
import uvicorn
from dotenv import load_dotenv

load_dotenv()

from src.memory.store import init_db


def main():
    """Unified entry point for OpsAgent."""
    print("🚀 Initializing OpsAgent database...")
    init_db()

    if len(sys.argv) > 1 and sys.argv[1] == "bot":
        from src.slack.bot import start_socket_mode
        print("🤖 Starting OpsAgent Slack Bot (Socket Mode)...")
        start_socket_mode()
    else:
        print("🌐 Starting OpsAgent FastAPI Server at http://localhost:8000...")
        uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)


if __name__ == "__main__":
    main()
