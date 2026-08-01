import pytest
import asyncio
from datetime import datetime
from src.memory.store import init_db, create_task, get_tasks, create_reminder, get_pending_reminders, get_db
from src.memory.models import ActionsLog
from src.hooks.logging_hook import log_call
from sqlalchemy import select


@pytest.fixture(autouse=True)
def setup_db():
    init_db()


def test_database_task_and_reminder_creation():
    # Test task creation
    task = create_task(description="Write unit tests", assignee="Abdullah", due_hint="tomorrow")
    assert task.id is not None
    assert task.description == "Write unit tests"
    assert task.assignee == "Abdullah"

    tasks = get_tasks()
    assert len(tasks) >= 1

    # Test reminder creation
    now = datetime.utcnow()
    reminder = create_reminder(
        channel_id="C12345",
        user_id="U12345",
        message="Follow up with John",
        fire_at=now,
        task_id=task.id,
    )
    assert reminder.id is not None
    assert reminder.delivered is False

    pending = get_pending_reminders(now=now)
    assert len(pending) >= 1


def test_sync_logging_hook():
    @log_call
    def sample_sync_func(a: int, b: int) -> int:
        return a + b

    result = sample_sync_func(5, 10)
    assert result == 15

    with get_db() as db:
        stmt = select(ActionsLog).where(ActionsLog.func_name.contains("sample_sync_func"))
        logs = list(db.scalars(stmt).all())
        assert len(logs) >= 1
        last_log = logs[-1]
        assert last_log.status == "success"
        assert "15" in last_log.outputs


@pytest.mark.asyncio
async def test_async_logging_hook():
    @log_call
    async def sample_async_func(name: str) -> str:
        await asyncio.sleep(0.01)
        return f"Hello, {name}"

    res = await sample_async_func("OpsAgent")
    assert res == "Hello, OpsAgent"

    with get_db() as db:
        stmt = select(ActionsLog).where(ActionsLog.func_name.contains("sample_async_func"))
        logs = list(db.scalars(stmt).all())
        assert len(logs) >= 1
        last_log = logs[-1]
        assert last_log.status == "success"
        assert "Hello, OpsAgent" in last_log.outputs
