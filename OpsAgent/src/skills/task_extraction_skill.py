import os
from typing import List, Optional
from pydantic import BaseModel, Field
from src.llm_client import get_llm
from src.hooks.logging_hook import log_call


class ExtractedTask(BaseModel):
    description: str = Field(..., description="Action item description")
    assignee: Optional[str] = Field(None, description="Person responsible for the task")
    due_hint: Optional[str] = Field(None, description="Time or date hint e.g., 'tomorrow', 'Friday'")
    reminder_delay_seconds: Optional[int] = Field(None, description="Extracted reminder delay in seconds from now (e.g. 86400 for 1 day, 60 for 1 min)")


class TaskExtractionResult(BaseModel):
    tasks: List[ExtractedTask] = Field(default_factory=list, description="Extracted action items")


@log_call
def extract_tasks_and_reminders(text: str) -> TaskExtractionResult:
    """
    Extracts action items, assignees, due dates, and reminder requests from raw text.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in environment variables.")

    llm = get_llm()
    
    structured_llm = llm.with_structured_output(TaskExtractionResult)
    
    system_prompt = (
        "You are an AI task manager. Parse the user's input to extract all specific action items, "
        "tasks, assignees, due date hints, and requested reminder timings. "
        "If a reminder timing like 'tomorrow', 'in 1 hour', 'next day', or 'in 1 minute' is requested, "
        "estimate the appropriate delay in seconds (e.g., 60 seconds for 1 min, 86400 for tomorrow)."
    )
    
    messages = [
        ("system", system_prompt),
        ("user", text),
    ]
    
    return structured_llm.invoke(messages)
