import pytest
from src.skills.file_review_skill import review_file_content, FileReviewResult


def test_file_review_skill_mocked(monkeypatch):
    sample_content = (
        "def calculate_total(prices):\n"
        "    total = 0\n"
        "    for p in prices:\n"
        "        total += p\n"
        "    return total\n"
    )

    mock_review = FileReviewResult(
        summary="Clean implementation of calculate_total function.",
        issues=["Consider adding type hints for parameters and return value."],
        comment_text="### File Code Review\n\n- Summary: Clean implementation.\n- Suggestion: Add type hints."
    )

    class MockStructuredRunnable:
        def invoke(self, prompt):
            return mock_review

    class MockLLM:
        def with_structured_output(self, schema):
            return MockStructuredRunnable()

    monkeypatch.setattr("src.skills.file_review_skill.ChatAnthropic", lambda **kwargs: MockLLM())

    res = review_file_content(file_content=sample_content, file_path="utils/calculator.py")
    assert "Clean implementation" in res.summary
    assert len(res.issues) == 1
    assert "type hints" in res.issues[0]
    assert "### File Code Review" in res.comment_text
