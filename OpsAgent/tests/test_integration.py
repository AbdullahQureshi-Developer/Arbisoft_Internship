import pytest
from datetime import datetime, timedelta
from sqlalchemy import text
from src.marshal.graph import process_slack_message
from src.skills.review_skill import PRReviewResult
from src.skills.summarization_skill import SummaryResult
from src.skills.task_extraction_skill import TaskExtractionResult, ExtractedTask
from src.memory.store import get_tasks, get_pending_reminders, get_channel_history, init_db, get_db
from src.agents.reminder_agent import check_and_deliver_pending_reminders


@pytest.fixture(autouse=True)
def setup_database():
    init_db()
    with get_db() as db:
        db.execute(text("DELETE FROM conversation_history"))
        db.execute(text("DELETE FROM reminders"))
        db.execute(text("DELETE FROM tasks"))


def test_integration_github_flow(monkeypatch):
    """Simulate end-to-end GitHub PR review flow."""
    # Mock GitHub tools in graph namespace
    monkeypatch.setattr(
        "src.marshal.graph.fetch_pr_diff",
        lambda req: type("MockFetchPRResult", (), {
            "repo": req.repo,
            "pr_number": req.pr_number,
            "title": "Add feature X",
            "state": "open",
            "html_url": f"https://github.com/{req.repo}/pull/{req.pr_number}",
            "diff": "--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new",
        })()
    )
    monkeypatch.setattr(
        "src.marshal.graph.post_review_comment",
        lambda req: type("MockPostCommentResult", (), {
            "status": "success",
            "comment_id": 999,
            "html_url": f"https://github.com/{req.repo}/pull/{req.pr_number}#comment-999",
            "body": req.body,
        })()
    )
    # Mock Review Skill in graph namespace
    monkeypatch.setattr(
        "src.marshal.graph.review_pr_diff",
        lambda diff_text, title="": PRReviewResult(
            summary="Added feature X cleanly.",
            issues=[],
            comment_text="### Review\nLooks good to merge!"
        )
    )

    response = process_slack_message(
        message_text="review PR #123",
        channel_id="C12345",
        user_id="U12345",
    )

    assert "GitHub Review Posted" in response
    assert "PR #123" in response
    assert "Added feature X cleanly" in response


def test_integration_task_reminder_flow(monkeypatch):
    """Simulate end-to-end Task & Reminder flow."""
    monkeypatch.setattr(
        "src.marshal.graph.summarize_text",
        lambda notes_text: SummaryResult(summary="Discussed feature design and assigned action items.")
    )
    monkeypatch.setattr(
        "src.marshal.graph.extract_tasks_and_reminders",
        lambda text: TaskExtractionResult(
            tasks=[
                ExtractedTask(description="Deploy to staging", assignee="Abdullah", due_hint="today", reminder_delay_seconds=30)
            ]
        )
    )

    response = process_slack_message(
        message_text="Meeting notes: Deploy to staging today. Remind me in 30 seconds.",
        channel_id="C12345",
        user_id="U12345",
    )

    assert "Summary & Task Extraction Complete" in response
    assert "Deploy to staging" in response
    assert "reminder(s) scheduled" in response


def test_multi_user_data_isolation(monkeypatch):
    """
    Simulates two different users (U_ALICE and U_BOB) sending overlapping requests.
    Asserts:
    1. Alice's task list never contains Bob's tasks, and vice versa.
    2. A reminder scheduled for Alice fires to Alice's channel, not Bob's.
    3. Conversation history used for context injection never mixes messages from two users.
    """
    # Custom extraction mock per user
    def mock_extract(text: str) -> TaskExtractionResult:
        if "Alice" in text:
            return TaskExtractionResult(
                tasks=[ExtractedTask(description="Alice task: write report", assignee="Alice", reminder_delay_seconds=5)]
            )
        else:
            return TaskExtractionResult(
                tasks=[ExtractedTask(description="Bob task: fix bug", assignee="Bob", reminder_delay_seconds=5)]
            )

    monkeypatch.setattr("src.marshal.graph.summarize_text", lambda text: SummaryResult(summary="Summary"))
    monkeypatch.setattr("src.marshal.graph.extract_tasks_and_reminders", mock_extract)

    # Alice sends request in C_ALICE
    resp_alice = process_slack_message(
        message_text="Notes for Alice task: write report. Remind me in 5s",
        channel_id="C_ALICE",
        user_id="U_ALICE",
    )
    assert "Summary & Task Extraction Complete" in resp_alice

    # Bob sends request in C_BOB
    resp_bob = process_slack_message(
        message_text="Notes for Bob task: fix bug. Remind me in 5s",
        channel_id="C_BOB",
        user_id="U_BOB",
    )
    assert "Summary & Task Extraction Complete" in resp_bob

    # 1. Assert Task List Isolation
    alice_tasks = get_tasks(user_id="U_ALICE")
    bob_tasks = get_tasks(user_id="U_BOB")

    assert len(alice_tasks) >= 1
    assert all("Alice task" in t.description for t in alice_tasks)
    assert not any("Bob task" in t.description for t in alice_tasks)

    assert len(bob_tasks) >= 1
    assert all("Bob task" in t.description for t in bob_tasks)
    assert not any("Alice task" in t.description for t in bob_tasks)

    # 2. Assert Reminder Delivery Isolation
    future_time = datetime.utcnow() + timedelta(seconds=10)
    alice_pending = get_pending_reminders(user_id="U_ALICE", now=future_time)
    bob_pending = get_pending_reminders(user_id="U_BOB", now=future_time)

    assert len(alice_pending) >= 1
    assert alice_pending[0].channel_id == "C_ALICE"
    assert alice_pending[0].user_id == "U_ALICE"

    assert len(bob_pending) >= 1
    assert bob_pending[0].channel_id == "C_BOB"
    assert bob_pending[0].user_id == "U_BOB"

    # Deliver pending reminders at future_time
    delivered_messages = []
    def mock_say(text: str, channel: str):
        delivered_messages.append((channel, text))

    check_and_deliver_pending_reminders(slack_say=mock_say, now=future_time)
    alice_delivered = [msg for ch, msg in delivered_messages if ch == "C_ALICE"]
    bob_delivered = [msg for ch, msg in delivered_messages if ch == "C_BOB"]

    assert any("<@U_ALICE>" in msg for msg in alice_delivered)
    assert not any("<@U_BOB>" in msg for msg in alice_delivered)

    assert any("<@U_BOB>" in msg for msg in bob_delivered)
    assert not any("<@U_ALICE>" in msg for msg in bob_delivered)

    # 3. Assert Conversation History Isolation (even in a shared channel)
    process_slack_message("Shared channel message from Alice", channel_id="C_SHARED", user_id="U_ALICE")
    process_slack_message("Shared channel message from Bob", channel_id="C_SHARED", user_id="U_BOB")

    alice_history = get_channel_history(channel_id="C_SHARED", user_id="U_ALICE")
    bob_history = get_channel_history(channel_id="C_SHARED", user_id="U_BOB")

    assert any("message from Alice" in h.message for h in alice_history)
    assert not any("message from Bob" in h.message for h in alice_history)

    assert any("message from Bob" in h.message for h in bob_history)
    assert not any("message from Alice" in h.message for h in bob_history)
