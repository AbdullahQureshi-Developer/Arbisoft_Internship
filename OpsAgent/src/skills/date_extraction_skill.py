import json
import os
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from src.llm_client import get_llm
from src.hooks.logging_hook import log_call


class ExtractedDateItem(BaseModel):
    description: str = Field(description="Description of the event, meeting, deadline, or milestone")
    date: datetime = Field(description="Exact date and time of the event in ISO format YYYY-MM-DDTHH:MM:SS")


class ExtractedDatesAndUpdates(BaseModel):
    dates: List[ExtractedDateItem] = Field(default_factory=list, description="List of important dates, deadlines, or scheduled events mentioned in the document")
    updates: List[str] = Field(default_factory=list, description="List of notable decisions, status changes, or scope updates mentioned in the document")

    @field_validator("dates", mode="before")
    @classmethod
    def parse_dates_if_string(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict) and "dates" in parsed:
                    return parsed["dates"]
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v

    @field_validator("updates", mode="before")
    @classmethod
    def parse_updates_if_string(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict) and "updates" in parsed:
                    return parsed["updates"]
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                pass
        return v


@log_call
def extract_dates_and_updates(text: str, reference_now: Optional[datetime] = None) -> ExtractedDatesAndUpdates:
    """
    Takes document text and extracts important dates/deadlines and notable updates using Claude structured output.
    """
    if reference_now is None:
        reference_now = datetime.utcnow()

    llm = get_llm()

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
