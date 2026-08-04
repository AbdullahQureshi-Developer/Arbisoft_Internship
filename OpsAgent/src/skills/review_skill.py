import os
from typing import List, Any
from pydantic import BaseModel, Field, field_validator, model_validator
from src.llm_client import get_llm
from src.hooks.logging_hook import log_call


class PRReviewResult(BaseModel):
    summary: str = Field(..., description="High-level summary of changes introduced in the diff")
    issues: List[str] = Field(default_factory=list, description="List of potential issues, bugs, or code smell observations")
    comment_text: str = Field(default="", description="Complete GitHub markdown comment text ready to post on the PR")

    @field_validator("issues", mode="before")
    @classmethod
    def coerce_issues_list(cls, v: Any) -> List[str]:
        if isinstance(v, str):
            lines = [line.strip("- •*").strip() for line in v.split("\n") if line.strip() and not line.strip().startswith("<")]
            return lines if lines else [v.strip()]
        return v if isinstance(v, list) else []

    @model_validator(mode="before")
    @classmethod
    def ensure_comment_text(cls, values: Any) -> Any:
        if isinstance(values, dict):
            summary = values.get("summary", "Code review complete.")
            issues = values.get("issues", [])
            if not values.get("comment_text"):
                if isinstance(issues, list):
                    issues_formatted = "\n".join([f"• {item}" for item in issues]) if issues else "No critical issues identified."
                else:
                    issues_formatted = str(issues)
                values["comment_text"] = (
                    f"## 🔍 Code Review Summary\n\n{summary}\n\n"
                    f"### ⚠️ Issues & Observations\n{issues_formatted}\n"
                )
        return values


@log_call
def review_pr_diff(diff_text: str, title: str = "") -> PRReviewResult:
    """
    Analyzes a GitHub PR diff using the Claude API and returns structured review feedback.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in environment variables.")

    llm = get_llm()
    structured_llm = llm.with_structured_output(PRReviewResult)

    system_prompt = (
        "You are an expert senior software engineer performing code reviews.\n"
        "Review the provided git diff carefully.\n"
        "Provide:\n"
        "1. summary: A concise high-level summary of the changes.\n"
        "2. issues: A JSON array of string items (e.g. [\"Issue 1\", \"Issue 2\"]). Do NOT output XML tags or raw text.\n"
        "3. comment_text: A complete GitHub markdown review comment ready to post on the PR."
    )

    MAX_DIFF_LENGTH = 40000  # Safe limit (~10k tokens)
    if len(diff_text) > MAX_DIFF_LENGTH:
        diff_text = diff_text[:MAX_DIFF_LENGTH] + f"\n\n... [Diff truncated for review: total length was {len(diff_text)} characters] ..."

    user_prompt = f"PR Title: {title}\n\nDiff Content:\n{diff_text}"

    messages = [
        ("system", system_prompt),
        ("user", user_prompt),
    ]

    result = structured_llm.invoke(messages)
    return result
