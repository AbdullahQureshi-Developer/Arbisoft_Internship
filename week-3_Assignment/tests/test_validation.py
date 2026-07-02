import pytest
from pydantic import ValidationError

from rag_app.structured import ExtractedInfo


def test_valid_extracted_info():
    """Test that a valid LLM JSON output passes validation."""
    data = {
        "title": "Machine Learning",
        "summary": "An intro to ML.",
        "key_entities": ["AI", "Computers"],
        "confidence_score": 9,
    }
    obj = ExtractedInfo(**data)
    assert obj.title == "Machine Learning"
    assert obj.confidence_score == 9


def test_missing_field_hallucination():
    """Test when the LLM hallucinated a different schema and forgot a field."""
    data = {"title": "Incomplete Data", "summary": "Missing entities and score."}
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "key_entities" in str(exc_info.value)
    assert "confidence_score" in str(exc_info.value)


def test_wrong_type_hallucination():
    """Test when the LLM hallucinated a string instead of an int for the score."""
    data = {
        "title": "Wrong Type",
        "summary": "Score is a string.",
        "key_entities": ["Test"],
        "confidence_score": "High",  # Should be int
    }
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "confidence_score" in str(exc_info.value)
    assert "Input should be a valid integer" in str(exc_info.value)


def test_confidence_score_out_of_range_hallucination():
    """Test when the LLM hallucinated a valid int but outside the 1-10 range.

    A correctly-typed but semantically invalid score (e.g. 999) previously
    passed validation silently, since `confidence_score` had no bounds.
    """
    data = {
        "title": "Out of Range",
        "summary": "Score is a valid int but outside the allowed 1-10 range.",
        "key_entities": ["Test"],
        "confidence_score": 999,  # Should be between 1 and 10
    }
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "confidence_score" in str(exc_info.value)
    assert "less than or equal to 10" in str(exc_info.value)


def test_confidence_score_below_range_hallucination():
    """Test when the LLM hallucinated a score below the allowed range (e.g. 0)."""
    data = {
        "title": "Below Range",
        "summary": "Score is 0, outside the allowed 1-10 range.",
        "key_entities": ["Test"],
        "confidence_score": 0,
    }
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "confidence_score" in str(exc_info.value)
    assert "greater than or equal to 1" in str(exc_info.value)
