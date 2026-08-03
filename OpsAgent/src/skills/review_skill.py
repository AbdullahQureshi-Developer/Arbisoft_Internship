import os
from typing import List
from pydantic import BaseModel, Field
from src.llm_client import get_llm
from src.hooks.logging_hook import log_call


class PRReviewResult(BaseModel):
    summary: str = Field(..., description="High-level summary of changes introduced in the diff")
    issues: List[str] = Field(default_factory=list, description="List of potential issues, bugs, or code smell observations")
    comment_text: str = Field(..., description="Complete GitHub markdown comment text ready to post on the PR")


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
        "You are an expert senior software engineer performing code reviews. "
        "Review the provided git diff carefully. Produce a concise summary of the changes, "
        "a list of potential issues or areas for improvement, and a well-formatted GitHub comment text."
    )
    
    user_prompt = f"PR Title: {title}\n\nDiff Content:\n{diff_text}"
    
    messages = [
        ("system", system_prompt),
        ("user", user_prompt),
    ]
    
    result = structured_llm.invoke(messages)
    return result
