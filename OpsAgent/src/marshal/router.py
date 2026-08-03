import os
import re
from typing import Optional
from pydantic import BaseModel, Field
from src.llm_client import get_llm
from src.hooks.logging_hook import log_call


class WorkflowIntent(BaseModel):
    intent_type: str = Field(..., description="Must be one of: 'github_review', 'github_file_review', 'task_and_reminder', 'calendar_schedule', 'unknown'")
    repo: Optional[str] = Field(None, description="GitHub repo in 'owner/repo' or 'repo' format if github_review or github_file_review")
    pr_number: Optional[int] = Field(None, description="PR number if github_review")
    file_path: Optional[str] = Field(None, description="File path relative to repo if github_file_review")
    target_pr_number: Optional[int] = Field(None, description="Target PR number to post comment to if explicitly specified by user")
    notes_text: Optional[str] = Field(None, description="Extracted meeting notes or text for task/summarization")
    reminder_seconds: Optional[int] = Field(None, description="Reminder delay in seconds if specified")


@log_call
def classify_intent(message_text: str) -> WorkflowIntent:
    """
    Classifies user message intent into 'github_review', 'github_file_review', 'task_and_reminder', or 'calendar_schedule' using Claude API.
    Includes regex fallback for fast pattern matching.
    """
    msg_lower = message_text.lower()

    # 1. Regex fast-path for file review intent (e.g. "check my activity.py in week-5_Assignment repository")
    file_review_match = re.search(
        r"(?:check|review)\s+(?:file\s+|my\s+|file\s+my\s+)?([\w\-\./]+\.[a-zA-Z0-9]+)\s+in\s+([\w\-\./]+)(?:\s+repository|\s+repo)?",
        message_text,
        re.IGNORECASE
    )
    if file_review_match:
        file_path = file_review_match.group(1)
        repo = file_review_match.group(2)
        pr_target_match = re.search(r"(?:post\s+to|attach\s+to|on)\s+PR\s*#?(\d+)", message_text, re.IGNORECASE)
        target_pr = int(pr_target_match.group(1)) if pr_target_match else None
        return WorkflowIntent(
            intent_type="github_file_review",
            repo=repo,
            file_path=file_path,
            target_pr_number=target_pr,
        )

    # 2. Regex fast-path for calendar scheduling intent
    if any(k in msg_lower for k in ["schedule a meeting", "book time with", "set up a call", "schedule a call", "book meeting", "schedule meeting", "set up a meeting"]):
        return WorkflowIntent(
            intent_type="calendar_schedule",
            notes_text=message_text,
        )

    # 3. Regex fast-path for PR review ("review PR #123" or "review octocat/Hello-World #123")
    pr_match = re.search(r"review\s+(?:PR\s*)?(?:#|pr)?\s*([\w\-]+/[\w\-]+)?\s*#?(\d+)", message_text, re.IGNORECASE)
    if pr_match:
        repo = pr_match.group(1) or os.getenv("DEFAULT_GITHUB_REPO", "owner/repo")
        pr_num = int(pr_match.group(2))
        return WorkflowIntent(
            intent_type="github_review",
            repo=repo,
            pr_number=pr_num,
        )

    # 4. Fast-path regex for notes / task / reminder
    if any(k in msg_lower for k in ["notes", "summarize", "task", "remind"]):
        return WorkflowIntent(
            intent_type="task_and_reminder",
            notes_text=message_text,
        )

    # 5. LLM-based intent classifier for natural language / free-form queries
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        if any(k in msg_lower for k in ["schedule", "meeting", "calendar", "book"]):
            return WorkflowIntent(intent_type="calendar_schedule", notes_text=message_text)
        return WorkflowIntent(intent_type="unknown")

    try:
        llm = get_llm()
        structured_llm = llm.with_structured_output(WorkflowIntent)
        
        system_prompt = (
            "You are an intent classification router for an AI assistant. "
            "Classify the user's message into one of these intent types:\n"
            "- 'github_review': User wants to review a pull request by PR number. Extract repo and pr_number.\n"
            "- 'github_file_review': User wants to review a specific file by file path and repository (independent of PR). Extract repo, file_path, and target_pr_number if mentioned.\n"
            "- 'task_and_reminder': User wants to summarize notes, extract tasks, or schedule reminders.\n"
            "- 'calendar_schedule': User wants to schedule a meeting, call, or calendar event.\n"
            "- 'unknown': None of the above."
        )
        
        messages = [
            ("system", system_prompt),
            ("user", message_text),
        ]
        
        return structured_llm.invoke(messages)
    except Exception:
        # Fallback if LLM call fails
        if any(k in msg_lower for k in ["schedule", "meeting", "calendar", "book"]):
            return WorkflowIntent(intent_type="calendar_schedule", notes_text=message_text)
        if "pr" in msg_lower or "review" in msg_lower:
            digits = re.findall(r"\d+", message_text)
            if digits:
                return WorkflowIntent(
                    intent_type="github_review",
                    repo=os.getenv("DEFAULT_GITHUB_REPO", "owner/repo"),
                    pr_number=int(digits[0]),
                )
        return WorkflowIntent(intent_type="unknown", notes_text=message_text)
