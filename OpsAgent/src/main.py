import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from dotenv import load_dotenv

from src.memory.store import init_db
from src.slack.bot import app as slack_app

load_dotenv()

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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
