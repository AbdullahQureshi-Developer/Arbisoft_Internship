import pytest
from src.skills.summarization_skill import summarize_text, SummaryResult

SAMPLE_NOTES = """
Team sync meeting:
- Discussed Q3 roadmap.
- Decided to migrate database to PostgreSQL by end of month.
- Abdullah to prepare benchmark report by Friday.
"""

def test_summarize_text_mocked(monkeypatch):
    def mock_invoke(self, messages):
        return SummaryResult(summary="The team agreed on the Q3 roadmap, database migration, and benchmark report.")

    from langchain_anthropic import ChatAnthropic
    monkeypatch.setattr(ChatAnthropic, "with_structured_output", lambda self, schema: type("MockRunner", (), {"invoke": mock_invoke})())

    res = summarize_text(SAMPLE_NOTES)
    assert isinstance(res, SummaryResult)
    assert "roadmap" in res.summary
