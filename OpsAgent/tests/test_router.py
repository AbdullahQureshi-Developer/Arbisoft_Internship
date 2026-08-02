import pytest
from src.marshal.router import classify_intent, WorkflowIntent


def test_router_regex_fastpath():
    res1 = classify_intent("review PR #123")
    assert res1.intent_type == "github_review"
    assert res1.pr_number == 123

    res2 = classify_intent("review octocat/Hello-World #456")
    assert res2.intent_type == "github_review"
    assert res2.repo == "octocat/Hello-World"
    assert res2.pr_number == 456


def test_router_file_review_intent_fastpath():
    res1 = classify_intent("check my activity.py in week-5_Assignment repository")
    assert res1.intent_type == "github_file_review"
    assert res1.file_path == "activity.py"
    assert res1.repo == "week-5_Assignment"
    assert res1.target_pr_number is None

    res2 = classify_intent("review file src/utils.py in my-org/my-repo repo post to PR #42")
    assert res2.intent_type == "github_file_review"
    assert res2.file_path == "src/utils.py"
    assert res2.repo == "my-org/my-repo"
    assert res2.target_pr_number == 42


def test_router_calendar_intent_fastpath():
    res1 = classify_intent("schedule a meeting with John tomorrow at 3pm")
    assert res1.intent_type == "calendar_schedule"

    res2 = classify_intent("book time with Sarah next Monday")
    assert res2.intent_type == "calendar_schedule"

    res3 = classify_intent("set up a call for 30 minutes")
    assert res3.intent_type == "calendar_schedule"


def test_router_llm_mocked(monkeypatch):
    def mock_invoke(self, messages):
        return WorkflowIntent(
            intent_type="task_and_reminder",
            notes_text="Meeting notes: Abdullah to fix bug tomorrow",
            reminder_seconds=86400,
        )

    from langchain_anthropic import ChatAnthropic
    monkeypatch.setattr(ChatAnthropic, "with_structured_output", lambda self, schema: type("MockRunner", (), {"invoke": mock_invoke})())

    res = classify_intent("Summarize these meeting notes: Abdullah to fix bug tomorrow")
    assert res.intent_type == "task_and_reminder"
    assert res.notes_text is not None
