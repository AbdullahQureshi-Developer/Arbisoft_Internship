import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from src.hooks.logging_hook import log_call

logger = logging.getLogger(__name__)


def _ensure_offset(dt_str: str, user_tz: Optional[str] = None) -> str:
    """
    Ensures an ISO 8601 datetime string has an explicit timezone offset.
    If no offset (Z, +, or - after position 10) is specified, appends user_tz or local timezone offset.
    """
    if "Z" not in dt_str and "+" not in dt_str and "-" not in dt_str[10:]:
        if user_tz:
            tz_offset = user_tz
        else:
            tz_offset = datetime.now().astimezone().strftime("%z")
        if tz_offset and len(tz_offset) == 5:
            tz_offset = f"{tz_offset[:3]}:{tz_offset[3:]}"
        return f"{dt_str}{tz_offset}" if tz_offset else f"{dt_str}Z"
    return dt_str


@log_call
def create_event(
    title: str,
    start_time: str,
    end_time: str,
    attendees: Optional[List[str]] = None,
    user_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Creates an event on the authenticated user's primary calendar via the Google Calendar API.

    Parameters:
      title: Event summary/title
      start_time: Start time string in ISO 8601 format (e.g. '2026-08-03T15:00:00Z')
      end_time: End time string in ISO 8601 format (e.g. '2026-08-03T15:30:00Z')
      attendees: List of attendee email addresses
      user_id: Optional Slack User ID to resolve per-user Google token

    Returns:
      Dict with event ID, shareable html_url, title, status, etc.
    """
    if attendees is None:
        attendees = []

    try:
        from src.integrations.google.auth import get_calendar_service

        service = get_calendar_service(user_id=user_id)
        if service is None:
            from src.integrations.google.auth import generate_auth_token

            token = generate_auth_token(user_id) if user_id else "default"
            auth_url = f"http://localhost:8000/auth/google?token={token}"
            return {
                "status": "auth_required",
                "event_id": "",
                "title": title,
                "start_time": start_time,
                "end_time": end_time,
                "html_url": auth_url,
                "attendees": attendees,
                "note": "auth_required",
            }

        start_obj = {"dateTime": _ensure_offset(start_time)}
        end_obj = {"dateTime": _ensure_offset(end_time)}

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
