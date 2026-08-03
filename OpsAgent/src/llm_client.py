import os
from typing import Optional
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv

from src.config import DEFAULT_MODEL_NAME

load_dotenv()


def get_llm(
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
    api_key: Optional[str] = None,
) -> ChatAnthropic:
    """
    Returns a configured ChatAnthropic instance using centralized defaults.
    Temperature is omitted by default to maintain compatibility with models (e.g. claude-sonnet-5)
    that deprecate or reject temperature configuration.
    """
    key = api_key or os.getenv("ANTHROPIC_API_KEY", "dummy-key")
    model = model_name or DEFAULT_MODEL_NAME

    kwargs = {
        "model_name": model,
        "anthropic_api_key": key,
    }

    if temperature is not None:
        kwargs["temperature"] = temperature

    return ChatAnthropic(**kwargs)


def call_claude(
    prompt: str,
    system_prompt: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
    """
    Shared helper to execute a text completion call against the Anthropic API using the centralized LLM client.
    """
    llm = get_llm(model_name=model_name, temperature=temperature)
    messages = []
    if system_prompt:
        messages.append(("system", system_prompt))
    messages.append(("user", prompt))

    response = llm.invoke(messages)
    return str(response.content) if hasattr(response, "content") else str(response)
