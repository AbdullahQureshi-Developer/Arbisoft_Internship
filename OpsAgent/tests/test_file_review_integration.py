import pytest
from src.marshal.graph import process_slack_message
from src.agents.github_agent import FetchFileContentResult, PostCommentResult
from src.skills.file_review_skill import FileReviewResult


def test_file_review_standalone_flow(monkeypatch):
    """Path A: Standalone file review (no PR specified)."""
    monkeypatch.setattr(
        "src.marshal.graph.fetch_file_content",
        lambda req: FetchFileContentResult(
            repo=req.repo,
            file_path=req.file_path,
            content="def add(a, b):\n    return a + b",
            html_url=f"https://github.com/{req.repo}/blob/main/{req.file_path}",
        )
    )
    monkeypatch.setattr(
        "src.marshal.graph.review_file_content",
        lambda file_content, file_path="": FileReviewResult(
            summary="Clean simple function.",
            issues=["No type annotations."],
            comment_text="### Review\nLooks good."
        )
    )

    response = process_slack_message(
        message_text="check my activity.py in week-5_Assignment repository",
        channel_id="C12345",
        user_id="U_USER_1",
    )

    assert "File Code Review Complete" in response
    assert "activity.py" in response
    assert "Clean simple function" in response
    assert "PR Comment Offer" in response or "reply with" in response.lower() or "post to pr" in response.lower()


def test_file_review_with_confirmed_pr_flow(monkeypatch):
    """Path B: File review with explicit PR target specified."""
    monkeypatch.setattr(
        "src.marshal.graph.fetch_file_content",
        lambda req: FetchFileContentResult(
            repo=req.repo,
            file_path=req.file_path,
            content="def add(a, b):\n    return a + b",
            html_url=f"https://github.com/{req.repo}/blob/main/{req.file_path}",
        )
    )
    monkeypatch.setattr(
        "src.marshal.graph.review_file_content",
        lambda file_content, file_path="": FileReviewResult(
            summary="Clean simple function.",
            issues=[],
            comment_text="### Review\nVerified OK."
        )
    )

    posted_comments = []
    def mock_post_comment(req):
        posted_comments.append(req)
        return PostCommentResult(
            status="success",
            comment_id=777,
            html_url=f"https://github.com/{req.repo}/pull/{req.pr_number}#comment-777",
            body=req.body,
        )

    monkeypatch.setattr("src.marshal.graph.post_review_comment", mock_post_comment)

    response = process_slack_message(
        message_text="review file activity.py in week-5_Assignment repo post to PR #42",
        channel_id="C12345",
        user_id="U_USER_1",
    )

    assert len(posted_comments) == 1
    assert posted_comments[0].pr_number == 42
    assert "File Review Posted to PR #42" in response
    assert "activity.py" in response
