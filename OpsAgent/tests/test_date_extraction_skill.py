import pytest
from datetime import datetime
from src.skills.date_extraction_skill import extract_dates_and_updates, ExtractedDatesAndUpdates, ExtractedDateItem


def test_date_extraction_skill_mocked(monkeypatch):
    sample_text = (
        "Project Update Notes:\n"
        "- Quick review meeting today at 6pm (2026-08-02 18:00:00).\n"
        "- Design spec submission due next week on 2026-08-10 10:00:00.\n"
        "- Decision: Approved dark mode UI layout for dashboard."
    )

    mock_result = ExtractedDatesAndUpdates(
        dates=[
            ExtractedDateItem(description="Review meeting today", date=datetime(2026, 8, 2, 18, 0, 0)),
            ExtractedDateItem(description="Design spec submission due", date=datetime(2026, 8, 10, 10, 0, 0)),
        ],
        updates=["Approved dark mode UI layout for dashboard"],
    )

    class MockStructuredRunnable:
        def invoke(self, prompt):
            return mock_result

    class MockLLM:
        def with_structured_output(self, schema):
            return MockStructuredRunnable()

    monkeypatch.setattr("src.skills.date_extraction_skill.get_llm", lambda: MockLLM())

    res = extract_dates_and_updates(sample_text)
    assert len(res.dates) == 2
    assert res.dates[0].description == "Review meeting today"
    assert res.dates[0].date == datetime(2026, 8, 2, 18, 0, 0)
    assert res.dates[1].date == datetime(2026, 8, 10, 10, 0, 0)
    assert len(res.updates) == 1
    assert "Approved dark mode UI layout" in res.updates[0]
