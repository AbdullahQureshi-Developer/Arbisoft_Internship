import pytest
from src.marshal.graph import process_slack_message
from src.skills.review_skill import PRReviewResult
from src.skills.summarization_skill import SummaryResult
from src.skills.task_extraction_skill import TaskExtractionResult, ExtractedTask


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
