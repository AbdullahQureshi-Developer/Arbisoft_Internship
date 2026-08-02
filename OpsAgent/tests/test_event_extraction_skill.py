from datetime import datetime, timezone
import pytest
from src.skills.event_extraction_skill import extract_event_details, ExtractedEvent


def test_event_extraction_mocked(monkeypatch):
    def mock_invoke(self, messages):
        return ExtractedEvent(
            title="Meeting with John",
            start_time=datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 3, 15, 30, tzinfo=timezone.utc),
            attendees=["john@example.com"],
        )

    from langchain_anthropic import ChatAnthropic
    monkeypatch.setattr(
        ChatAnthropic,
        "with_structured_output",
        lambda self, schema: type("MockRunner", (), {"invoke": mock_invoke})(),
    )

    ref_time = datetime(2026, 8, 2, 12, 0, tzinfo=timezone.utc)
    res = extract_event_details("schedule a meeting with John tomorrow at 3pm for 30 minutes", current_time=ref_time)

    assert isinstance(res, ExtractedEvent)
    assert res.title == "Meeting with John"
    assert res.start_time.hour == 15
    assert "john@example.com" in res.attendees


def test_event_extraction_phrasings_mocked(monkeypatch):
    phrasings = [
        "book time with Sarah next Monday at 10am",
        "set up a call with dev team tomorrow at 2pm",
        "schedule sync with alex@company.com on Friday at 4pm for 1 hour",
    ]

    def mock_invoke(self, messages):
        user_msg = messages[1][1]
        return ExtractedEvent(
            title=f"Event for: {user_msg[:20]}",
            start_time=datetime(2026, 8, 3, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 8, 3, 15, 0, tzinfo=timezone.utc),
            attendees=["dev@company.com"],
        )

    from langchain_anthropic import ChatAnthropic
    monkeypatch.setattr(
        ChatAnthropic,
        "with_structured_output",
        lambda self, schema: type("MockRunner", (), {"invoke": mock_invoke})(),
    )

    for prompt in phrasings:
        res = extract_event_details(prompt)
        assert isinstance(res, ExtractedEvent)
        assert res.title.startswith("Event for:")
        assert len(res.attendees) > 0
