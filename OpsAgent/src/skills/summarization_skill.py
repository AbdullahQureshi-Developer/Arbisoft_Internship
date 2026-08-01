import os
from pydantic import BaseModel, Field
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from src.hooks.logging_hook import log_call

load_dotenv()


class SummaryResult(BaseModel):
    summary: str = Field(..., description="Clear, concise summary of notes or document text")


@log_call
def summarize_text(notes_text: str) -> SummaryResult:
    """
    Summarizes raw meeting notes or text using the Claude API.
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not configured in environment variables.")

    llm = ChatAnthropic(
        model_name="claude-haiku-4-5-20251001",
        anthropic_api_key=api_key,
        temperature=0.2,
    )
    
    structured_llm = llm.with_structured_output(SummaryResult)
    
    system_prompt = (
        "You are an executive assistant. Read the provided text or meeting notes "
        "and produce a crisp, structured summary highlighting key decisions and context."
    )
    
    messages = [
        ("system", system_prompt),
        ("user", notes_text),
    ]
    
    return structured_llm.invoke(messages)
