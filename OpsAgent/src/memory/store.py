import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from src.memory.models import ActionsLog, Base, Reminder, Task

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///opsagent.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def init_db() -> None:
    """Initialize database tables."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Generator[Session, None, None]:
    """Provide a transactional scope around a series of operations."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_task(description: str, assignee: Optional[str] = None, due_hint: Optional[str] = None) -> Task:
    """Create a new task in memory."""
    with get_db() as db:
        task = Task(description=description, assignee=assignee, due_hint=due_hint)
        db.add(task)
        db.flush()
        db.refresh(task)
        return task


def get_tasks(status: Optional[str] = None) -> List[Task]:
    """Retrieve tasks optionally filtered by status."""
    with get_db() as db:
        stmt = select(Task)
        if status:
            stmt = stmt.where(Task.status == status)
        return list(db.scalars(stmt).all())


def create_reminder(
    channel_id: str,
    user_id: str,
    message: str,
    fire_at: datetime,
    task_id: Optional[int] = None,
) -> Reminder:
    """Create a new reminder."""
    with get_db() as db:
        reminder = Reminder(
            channel_id=channel_id,
            user_id=user_id,
            message=message,
            fire_at=fire_at,
            task_id=task_id,
        )
        db.add(reminder)
        db.flush()
        db.refresh(reminder)
        return reminder


def get_pending_reminders(now: Optional[datetime] = None) -> List[Reminder]:
    """Get all reminders scheduled to fire on or before `now` that haven't been delivered."""
    if now is None:
        now = datetime.utcnow()
    with get_db() as db:
        stmt = select(Reminder).where(
            Reminder.fire_at <= now,
            Reminder.delivered == False
        )
        return list(db.scalars(stmt).all())


def mark_reminder_delivered(reminder_id: int) -> None:
    """Mark a reminder as delivered."""
    with get_db() as db:
        reminder = db.get(Reminder, reminder_id)
        if reminder:
            reminder.delivered = True


def log_action(func_name: str, inputs: str, outputs: str, status: str, latency_ms: float) -> ActionsLog:
    """Write an entry into actions_log."""
    with get_db() as db:
        log_entry = ActionsLog(
            func_name=func_name,
            inputs=inputs,
            outputs=outputs,
            status=status,
            latency_ms=latency_ms,
        )
        db.add(log_entry)
        db.flush()
        db.refresh(log_entry)
        return log_entry
