import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Callable
from pydantic import BaseModel, Field
from apscheduler.schedulers.background import BackgroundScheduler

from src.hooks.logging_hook import log_call
from src.memory.store import create_reminder, get_pending_reminders, mark_reminder_delivered

logger = logging.getLogger(__name__)


class ScheduleReminderRequest(BaseModel):
    channel_id: str
    user_id: str
    message: str
    delay_seconds: int = Field(default=60, description="Delay in seconds before firing reminder")
    task_id: Optional[int] = None


class ScheduleReminderResult(BaseModel):
    reminder_id: int
    fire_at: str
    status: str


class ReminderCheckResult(BaseModel):
    delivered_count: int


@log_call
def schedule_new_reminder(request: ScheduleReminderRequest) -> ScheduleReminderResult:
    """
    Schedules a new reminder in SQLite database.
    """
    fire_at = datetime.utcnow() + timedelta(seconds=max(5, request.delay_seconds))
    reminder = create_reminder(
        user_id=request.user_id,
        channel_id=request.channel_id,
        message=request.message,
        fire_at=fire_at,
        task_id=request.task_id,
    )
    return ScheduleReminderResult(
        reminder_id=reminder.id,
        fire_at=fire_at.isoformat(),
        status="scheduled",
    )


@log_call
def check_and_deliver_pending_reminders(slack_say: Optional[Callable] = None, now: Optional[datetime] = None) -> ReminderCheckResult:
    """
    Polls pending reminders across all users where fire_at <= now and delivered = False, delivers via Slack, and marks delivered.
    """
    if now is None:
        now = datetime.utcnow()
    pending_list = get_pending_reminders(now=now)
    delivered_count = 0
    
    for rem in pending_list:
        msg_text = f"⏰ **Reminder**: {rem.message}"
        if rem.user_id:
            msg_text = f"⏰ <@{rem.user_id}> **Reminder**: {rem.message}"
            
        logger.info(f"Delivering scheduled reminder #{rem.id} to user {rem.user_id} in channel {rem.channel_id}")
        
        if slack_say:
            try:
                slack_say(text=msg_text, channel=rem.channel_id)
            except Exception as e:
                logger.error(f"Failed to send Slack message for reminder #{rem.id}: {e}")
        else:
            logger.info(f"[SIMULATED SLACK DELIVERY] Channel: {rem.channel_id} | User: {rem.user_id} | Message: {msg_text}")
            
        mark_reminder_delivered(rem.id, user_id=rem.user_id)
        delivered_count += 1
        
    return ReminderCheckResult(delivered_count=delivered_count)


# APScheduler global background runner
_scheduler: Optional[BackgroundScheduler] = None


def start_reminder_scheduler(slack_say: Optional[Callable] = None, interval_seconds: int = 15):
    """
    Starts APScheduler background job polling for pending reminders.
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            check_and_deliver_pending_reminders,
            "interval",
            seconds=interval_seconds,
            kwargs={"slack_say": slack_say},
            id="reminder_poller_job",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(f"APScheduler started polling for reminders every {interval_seconds}s.")
