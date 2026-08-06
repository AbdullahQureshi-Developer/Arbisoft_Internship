from typing import List, Optional
from pydantic import BaseModel, Field
from src.hooks.logging_hook import log_call
from src.mcp_server.tools.calendar_tools import create_event


class CreateEventRequest(BaseModel):
    title: str = Field(..., description="Title or summary of the calendar event")
    start_time: str = Field(..., description="ISO 8601 formatted start datetime")
    end_time: str = Field(..., description="ISO 8601 formatted end datetime")
    attendees: List[str] = Field(
        default_factory=list, description="List of attendee email addresses or names"
    )
    user_id: Optional[str] = Field(
        None, description="Optional Slack user ID to scope OAuth token"
    )


class CreateEventResult(BaseModel):
    status: str
    event_id: str
    html_url: Optional[str] = None
    title: str
    start_time: str
    end_time: str
    attendees: List[str] = Field(default_factory=list)
    note: Optional[str] = None


@log_call
def schedule_calendar_event(request: CreateEventRequest) -> CreateEventResult:
    """
    Agent method calling create_event via MCP tool without internal LLM logic.
    """
    raw_res = create_event(
        title=request.title,
        start_time=request.start_time,
        end_time=request.end_time,
        attendees=request.attendees,
        user_id=request.user_id,
    )
    return CreateEventResult(**raw_res)
