import os
import re
from typing import Optional
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from src.hooks.logging_hook import log_call

load_dotenv()


class WorkflowIntent(BaseModel):
    intent_type: str = Field(..., description="Must be one of: 'github_review', 'task_and_reminder', 'unknown'")
    repo: Optional[str] = Field(None, description="GitHub repo in 'owner/repo' or 'repo' format if github_review")
    pr_number: Optional[int] = Field(None, description="PR number if github_review")
    notes_text: Optional[str] = Field(None, description="Extracted meeting notes or text for task/summarization")
    reminder_seconds: Optional[int] = Field(None, description="Reminder delay in seconds if specified")


@log_call
def classify_intent(message_text: str) -> WorkflowIntent:
    """
    Classifies user message intent into 'github_review' or 'task_and_reminder' using Claude API.
    Includes regex fallback for fast pattern matching.
    """
    # 1. Regex fast-path for "review PR #123" or "review octocat/Hello-World #123"
    pr_match = re.search(r"review\s+(?:PR\s*)?(?:#|pr)?\s*([\w\-]+/[\w\-]+)?\s*#?(\d+)", message_text, re.IGNORECASE)
    if pr_match:
        repo = pr_match.group(1) or os.getenv("DEFAULT_GITHUB_REPO", "owner/repo")
        pr_num = int(pr_match.group(2))
        return WorkflowIntent(
            intent_type="github_review",
            repo=repo,
            pr_number=pr_num,
        )

    # 1b. Fast-path regex for notes / task / reminder
    if any(k in message_text.lower() for k in ["notes", "summarize", "task", "remind"]):
        return WorkflowIntent(
            intent_type="task_and_reminder",
            notes_text=message_text,
        )

    # 2. LLM-based intent classifier for natural language / free-form queries
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return WorkflowIntent(intent_type="unknown")

    try:
        llm = ChatAnthropic(
            model_name="claude-haiku-4-5-20251001",
            anthropic_api_key=api_key,
            temperature=0.0,
        )
        structured_llm = llm.with_structured_output(WorkflowIntent)
        
        system_prompt = (
            "You are an intent classification router for an AI assistant. "
            "Classify the user's message into one of these intent types:\n"
            "- 'github_review': User wants to review, check, or comment on a pull request. Extract repo and pr_number.\n"
            "- 'task_and_reminder': User wants to summarize notes, extract tasks, or schedule reminders.\n"
            "- 'unknown': Neither of the above.\n"
            "Default repo to 'owner/repo' if not explicitly provided when intent is github_review."
        )
        
        messages = [
            ("system", system_prompt),
            ("user", message_text),
        ]
        
        return structured_llm.invoke(messages)
    except Exception:
        # Fallback if LLM call fails
        if "pr" in message_text.lower() or "review" in message_text.lower():
            digits = re.findall(r"\d+", message_text)
            if digits:
                return WorkflowIntent(
                    intent_type="github_review",
                    repo=os.getenv("DEFAULT_GITHUB_REPO", "owner/repo"),
                    pr_number=int(digits[0]),
                )
        return WorkflowIntent(intent_type="unknown", notes_text=message_text)
