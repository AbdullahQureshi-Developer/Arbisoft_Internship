import pytest
from src.skills.task_extraction_skill import extract_tasks_and_reminders, TaskExtractionResult, ExtractedTask

SAMPLE_INPUT = "Extract tasks: Prepare benchmark report by Friday, assign to Abdullah. Remind me tomorrow to follow up with John."

def test_task_extraction_mocked(monkeypatch):
    def mock_invoke(self, messages):
        return TaskExtractionResult(
            tasks=[
                ExtractedTask(description="Prepare benchmark report", assignee="Abdullah", due_hint="Friday"),
                ExtractedTask(description="Follow up with John", assignee="user", due_hint="tomorrow", reminder_delay_seconds=86400)
            ]
        )

    from langchain_anthropic import ChatAnthropic
    monkeypatch.setattr(ChatAnthropic, "with_structured_output", lambda self, schema: type("MockRunner", (), {"invoke": mock_invoke})())

    res = extract_tasks_and_reminders(SAMPLE_INPUT)
    assert isinstance(res, TaskExtractionResult)
    assert len(res.tasks) == 2
    assert res.tasks[0].assignee == "Abdullah"
