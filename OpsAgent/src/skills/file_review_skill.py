import os
import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from src.llm_client import get_llm
from src.hooks.logging_hook import log_call

logger = logging.getLogger(__name__)


class FileReviewResult(BaseModel):
    summary: str = Field(description="Summary of the code review for the file")
    issues: List[str] = Field(default_factory=list, description="List of potential bugs, code smells, performance issues, or edge cases")
    comment_text: str = Field(description="Formatted markdown review summary suitable for posting as a comment")


@log_call
def review_file_content(file_content: str, file_path: str = "") -> FileReviewResult:
    """
    Performs a full-file code review (not diff-based) analyzing code quality, edge cases, and maintainability.
    """
    llm = get_llm()

    structured_llm = llm.with_structured_output(FileReviewResult)

    prompt = (
        f"You are a senior software engineer performing a full-file code review.\n"
        f"File Path: {file_path or 'Source Code'}\n\n"
        f"File Content:\n```\n{file_content}\n```\n\n"
        f"Analyze the entire file content for bugs, edge cases, design flaws, performance bottlenecks, and style improvements. "
        f"Provide a concise summary, list of issues, and markdown comment text."
    )

    result = structured_llm.invoke(prompt)
    return result
