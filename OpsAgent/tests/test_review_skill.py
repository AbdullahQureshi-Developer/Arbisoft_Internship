import os
import pytest
from src.skills.review_skill import review_pr_diff, PRReviewResult

SAMPLE_DIFF = """
--- a/src/main.py
+++ b/src/main.py
@@ -10,3 +10,6 @@ def process_data(items):
-    return sum(items)
+    if not items:
+        return 0
+    return sum(items) / len(items)
"""

def test_review_pr_diff_mocked(monkeypatch):
    """Test review skill using a mock structure when API call is mocked."""
    def mock_invoke(self, messages):
        return PRReviewResult(
            summary="Updated process_data to calculate average instead of sum, adding empty check.",
            issues=["Potential division by zero avoided by empty check."],
            comment_text="### Code Review\n- Good addition of zero check!\n- Note function behavior changed from sum to average."
        )

    from langchain_anthropic import ChatAnthropic
    monkeypatch.setattr(ChatAnthropic, "with_structured_output", lambda self, schema: type("MockRunner", (), {"invoke": mock_invoke})())
    
    res = review_pr_diff(diff_text=SAMPLE_DIFF, title="Fix process data average calculation")
    assert isinstance(res, PRReviewResult)
    assert "process_data" in res.summary
    assert len(res.issues) >= 1
    assert "Code Review" in res.comment_text
