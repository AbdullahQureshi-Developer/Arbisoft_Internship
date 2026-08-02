import os
from contextlib import contextmanager
from datetime import datetime
from typing import Generator, List, Optional
from dotenv import load_dotenv
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from src.memory.models import ActionsLog, Base, ConversationHistory, Reminder, Task

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///opsagent.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, expire_on_commit=False, bind=engine)


def init_db() -> None:
    """Initialize database tables and run column migrations for existing SQLite database."""
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        if DATABASE_URL.startswith("sqlite"):
            # Migration for tasks table
            task_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(tasks)")).fetchall()]
            if "user_id" not in task_cols:
                conn.execute(text("ALTER TABLE tasks ADD COLUMN user_id TEXT NOT NULL DEFAULT 'U0BKEANUVP1'"))
            # Migration for reminders table
            rem_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(reminders)")).fetchall()]
            if "user_id" not in rem_cols:
                conn.execute(text("ALTER TABLE reminders ADD COLUMN user_id TEXT NOT NULL DEFAULT 'U0BKEANUVP1'"))
            # Migration for actions_log table
            actions_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(actions_log)")).fetchall()]
            if "user_id" not in actions_cols:
                conn.execute(text("ALTER TABLE actions_log ADD COLUMN user_id TEXT DEFAULT 'U0BKEANUVP1'"))
            conn.commit()


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


def create_task(user_id: str, description: str, assignee: Optional[str] = None, due_hint: Optional[str] = None) -> Task:
    """Create a new task in memory scoped to user_id."""
    with get_db() as db:
        task = Task(user_id=user_id, description=description, assignee=assignee, due_hint=due_hint)
        db.add(task)
        db.flush()
        db.refresh(task)
        return task


def get_tasks(user_id: str, status: Optional[str] = None) -> List[Task]:
    """Retrieve tasks strictly scoped by user_id, optionally filtered by status."""
    with get_db() as db:
        stmt = select(Task).where(Task.user_id == user_id)
        if status:
            stmt = stmt.where(Task.status == status)
        return list(db.scalars(stmt).all())


def create_reminder(
    user_id: str,
    channel_id: str,
    message: str,
    fire_at: datetime,
    task_id: Optional[int] = None,
) -> Reminder:
    """Create a new reminder scoped to user_id."""
    with get_db() as db:
        reminder = Reminder(
            user_id=user_id,
            channel_id=channel_id,
            message=message,
            fire_at=fire_at,
            task_id=task_id,
        )
        db.add(reminder)
        db.flush()
        db.refresh(reminder)
        return reminder


def get_pending_reminders(user_id: Optional[str] = None, now: Optional[datetime] = None) -> List[Reminder]:
    """Get all reminders scheduled to fire on or before `now` that haven't been delivered, optionally scoped by user_id."""
    if now is None:
        now = datetime.utcnow()
    with get_db() as db:
        stmt = select(Reminder).where(
            Reminder.fire_at <= now,
            Reminder.delivered == False
        )
        if user_id:
            stmt = stmt.where(Reminder.user_id == user_id)
        return list(db.scalars(stmt).all())


def mark_reminder_delivered(reminder_id: int, user_id: Optional[str] = None) -> None:
    """Mark a reminder as delivered."""
    with get_db() as db:
        stmt = select(Reminder).where(Reminder.id == reminder_id)
        if user_id:
            stmt = stmt.where(Reminder.user_id == user_id)
        reminder = db.scalars(stmt).first()
        if reminder:
            reminder.delivered = True


def log_action(func_name: str, inputs: str, outputs: str, status: str, latency_ms: float, user_id: Optional[str] = None) -> ActionsLog:
    """Write an entry into actions_log."""
    with get_db() as db:
        log_entry = ActionsLog(
            user_id=user_id,
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


def record_channel_message(channel_id: str, user_id: str, role: str, message: str) -> ConversationHistory:
    """Record message into conversation history keyed on (channel_id, user_id)."""
    with get_db() as db:
        entry = ConversationHistory(channel_id=channel_id, user_id=user_id, role=role, message=message)
        db.add(entry)
        db.flush()
        db.refresh(entry)
        return entry


def get_channel_history(channel_id: str, user_id: str, limit: int = 10) -> List[ConversationHistory]:
    """Retrieve history strictly keyed on (channel_id, user_id)."""
    with get_db() as db:
        stmt = (
            select(ConversationHistory)
            .where(ConversationHistory.channel_id == channel_id, ConversationHistory.user_id == user_id)
            .order_by(ConversationHistory.timestamp.desc())
            .limit(limit)
        )
        return list(reversed(db.scalars(stmt).all()))
