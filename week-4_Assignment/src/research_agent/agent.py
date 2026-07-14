from typing import Any

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph.state import CompiledStateGraph
from langgraph.prebuilt import create_react_agent

from research_agent.config import DEFAULT_MODEL_NAME
from research_agent.memory import build_memory
from research_agent.tools import read_file, web_search


def extract_text(content: Any) -> str:
    """
    Normalize a LangGraph/LangChain message's `.content` into a plain string.

    `content` can come back in a few different shapes depending on the model
    and how it decided to structure its reply:
      - a plain string (the common case)
      - a list of content blocks, where each block is either a dict with a
        "text" key or a plain string
      - occasionally something else entirely

    This never raises. Malformed or unexpected shapes (e.g. an empty list,
    or a list of plain strings instead of dicts) degrade to a best-effort
    string instead of throwing IndexError/AttributeError, which previously
    got swallowed by callers' broad `except Exception` blocks and misreported
    as an API-key problem.
    """
    if isinstance(content, str):
        return content

    if isinstance(content, list):
        if not content:
            return ""
        parts = []
        for block in content:
            if isinstance(block, dict):
                parts.append(block.get("text", str(block)))
            else:
                parts.append(str(block))
        return "\n".join(parts)

    return str(content)


SYSTEM_PROMPT = (
    "You are a helpful research assistant. "
    "You have access to two tools: web_search and read_file. "
    "IMPORTANT: Always check local files in the data/ directory first before "
    "searching the web. The file data/sample.txt contains a detailed research "
    "brief about Apple Inc. covering leadership, products, financials, history, "
    "competitors, and supply chain. The file data/sample.pdf contains information "
    "about Machine Learning basics and history. "
    "Use read_file on the relevant local file whenever the question could be "
    "answered from those documents. Only use web_search for current events, "
    "live data (stock prices, breaking news), or topics not covered in local files. "
    "Be concise in your answers."
)


def build_agent_executor(model_name: str = DEFAULT_MODEL_NAME) -> CompiledStateGraph:
    """Build the agent executor with memory and tools."""
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.1)

    tools = [web_search, read_file]
    memory = build_memory()

    agent_executor = create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        prompt=SYSTEM_PROMPT,
    )

    return agent_executor
