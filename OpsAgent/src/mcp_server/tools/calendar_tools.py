import logging
from typing import Any, Dict, List, Optional
from src.hooks.logging_hook import log_call

logger = logging.getLogger(__name__)


@log_call
def create_event(
    title: str,
    start_time: str,
    end_time: str,
    attendees: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Creates an event on the authenticated user's primary calendar via the Google Calendar API.
    
    Parameters:
      title: Event summary/title
      start_time: Start time string in ISO 8601 format (e.g. '2026-08-03T15:00:00Z')
      end_time: End time string in ISO 8601 format (e.g. '2026-08-03T15:30:00Z')
      attendees: List of attendee email addresses
      
    Returns:
      Dict with event ID, shareable html_url, title, status, etc.
    """
    if attendees is None:
        attendees = []

    try:
        from src.integrations.google.auth import get_calendar_service

        service = get_calendar_service()

        # Format start and end dateTime objects with timezone specification for Google Calendar API
        start_obj = {"dateTime": start_time}
        end_obj = {"dateTime": end_time}

        if "Z" not in start_time and "+" not in start_time and "-" not in start_time[10:]:
            import time
            tz_offset = time.strftime("%z")
            if tz_offset and len(tz_offset) == 5:
                formatted_tz = f"{tz_offset[:3]}:{tz_offset[3:]}"
                start_obj = {"dateTime": f"{start_time}{formatted_tz}"}
            else:
                start_obj = {"dateTime": f"{start_time}Z"}

        if "Z" not in end_time and "+" not in end_time and "-" not in end_time[10:]:
            import time
            tz_offset = time.strftime("%z")
            if tz_offset and len(tz_offset) == 5:
                formatted_tz = f"{tz_offset[:3]}:{tz_offset[3:]}"
                end_obj = {"dateTime": f"{end_time}{formatted_tz}"}
            else:
                end_obj = {"dateTime": f"{end_time}Z"}

        event_body = {
            "summary": title,
            "start": start_obj,
            "end": end_obj,
            "attendees": [{"email": email} for email in attendees],
        }

        created_event = (
            service.events()
            .insert(calendarId="primary", body=event_body, sendUpdates="all")
            .execute()
        )

        return {
            "status": "success",
            "event_id": created_event.get("id"),
            "html_url": created_event.get("htmlLink"),
            "title": created_event.get("summary", title),
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
        }
    except Exception as e:
        logger.error(f"Google Calendar API call failed for event '{title}': {e}")
        raise
