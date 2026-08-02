import os
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from src.hooks.logging_hook import log_call

load_dotenv()


class ExtractedEvent(BaseModel):
    title: str = Field(..., description="Event title or summary")
    start_time: datetime = Field(..., description="Calculated ISO start datetime of the event")
    end_time: datetime = Field(..., description="Calculated ISO end datetime of the event")
    attendees: List[str] = Field(default_factory=list, description="Extracted attendee names or emails")


@log_call
def extract_event_details(text: str, current_time: Optional[datetime] = None) -> ExtractedEvent:
    """
    Parses a free-form natural language Slack message into event fields (title, start_time, end_time, attendees).
    Uses the Claude API structured output.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in environment variables.")

    if current_time is None:
        current_time = datetime.now(timezone.utc)

    now_iso = current_time.isoformat()

    llm = ChatAnthropic(
        model_name="claude-haiku-4-5-20251001",
        anthropic_api_key=api_key,
        temperature=0.0,
    )

    structured_llm = llm.with_structured_output(ExtractedEvent)

    system_prompt = (
        "You are an AI assistant specialized in parsing calendar event scheduling requests. "
        f"The current reference datetime is '{now_iso}'. "
        "Extract the event title, start_time (ISO datetime), end_time (ISO datetime), and attendees list. "
        "If duration is not explicitly specified, default duration to 30 minutes after start_time. "
        "If title is missing, infer a concise title like 'Meeting with [Name]' or 'Call'."
    )

    messages = [
        ("system", system_prompt),
        ("user", text),
    ]

    return structured_llm.invoke(messages)
