import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from src.hooks.logging_hook import log_call


class ExtractedDateItem(BaseModel):
    description: str = Field(description="Description of the event, meeting, deadline, or milestone")
    date: datetime = Field(description="Exact date and time of the event in ISO format YYYY-MM-DDTHH:MM:SS")


class ExtractedDatesAndUpdates(BaseModel):
    dates: List[ExtractedDateItem] = Field(default_factory=list, description="List of important dates, deadlines, or scheduled events mentioned in the document")
    updates: List[str] = Field(default_factory=list, description="List of notable decisions, status changes, or scope updates mentioned in the document")


@log_call
def extract_dates_and_updates(text: str, reference_now: Optional[datetime] = None) -> ExtractedDatesAndUpdates:
    """
    Takes document text and extracts important dates/deadlines and notable updates using Claude structured output.
    """
    if reference_now is None:
        reference_now = datetime.utcnow()

    llm = ChatAnthropic(
        model_name="claude-3-7-sonnet-20250219",
        temperature=0.0,
        api_key=os.getenv("ANTHROPIC_API_KEY", "dummy-key"),
    )

    structured_llm = llm.with_structured_output(ExtractedDatesAndUpdates)

    prompt = (
        f"You are an assistant analyzing a business or technical document.\n"
        f"Reference Current Time: {reference_now.isoformat()}\n\n"
        f"Document Text:\n\"\"\"\n{text}\n\"\"\"\n\n"
        f"Extract all explicit or implicit dates, deadlines, and scheduled events with their exact timestamps and descriptions. "
        f"Also extract any notable decisions, status changes, or scope changes mentioned in the document."
    )

    result = structured_llm.invoke(prompt)
    return result
