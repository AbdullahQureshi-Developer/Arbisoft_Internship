import pytest
import asyncio
from datetime import datetime
from src.memory.store import init_db, create_task, get_tasks, create_reminder, get_pending_reminders, get_db
from src.memory.models import ActionsLog
from src.hooks.logging_hook import log_call
from sqlalchemy import select, text


@pytest.fixture(autouse=True)
def setup_db():
    init_db()
    with get_db() as db:
        db.execute(select(ActionsLog))  # ensure schema loaded
        db.execute(text("DELETE FROM conversation_history"))
        db.execute(text("DELETE FROM reminders"))
        db.execute(text("DELETE FROM tasks"))



def test_database_task_and_reminder_creation():
    # Test task creation scoped to user_id
    task = create_task(user_id="U12345", description="Write unit tests", assignee="Abdullah", due_hint="tomorrow")
    assert task.id is not None
    assert task.user_id == "U12345"
    assert task.description == "Write unit tests"
    assert task.assignee == "Abdullah"

    tasks = get_tasks(user_id="U12345")
    assert len(tasks) >= 1
    assert all(t.user_id == "U12345" for t in tasks)

    # Verify cross-user task isolation
    other_tasks = get_tasks(user_id="U99999")
    assert len(other_tasks) == 0

    # Test reminder creation scoped to user_id
    now = datetime.utcnow()
    reminder = create_reminder(
        user_id="U12345",
        channel_id="C12345",
        message="Follow up with John",
        fire_at=now,
        task_id=task.id,
    )
    assert reminder.id is not None
    assert reminder.user_id == "U12345"
    assert reminder.delivered is False

    pending = get_pending_reminders(user_id="U12345", now=now)
    assert len(pending) >= 1
    assert pending[0].user_id == "U12345"

    pending_other = get_pending_reminders(user_id="U99999", now=now)
    assert len(pending_other) == 0


def test_conversation_history_scoping():
    from src.memory.store import record_channel_message, get_channel_history

    record_channel_message(channel_id="C100", user_id="U_ALICE", role="user", message="Hello from Alice")
    record_channel_message(channel_id="C100", user_id="U_BOB", role="user", message="Hello from Bob")

    alice_hist = get_channel_history(channel_id="C100", user_id="U_ALICE")
    bob_hist = get_channel_history(channel_id="C100", user_id="U_BOB")

    assert len(alice_hist) == 1
    assert alice_hist[0].message == "Hello from Alice"

    assert len(bob_hist) == 1
    assert bob_hist[0].message == "Hello from Bob"


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

