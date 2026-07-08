import datetime
import os
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

from research_agent.tools import read_file, web_search


class ToolCallLoggingCallbackHandler(BaseCallbackHandler):
    """Callback handler that logs tool calls with timestamps."""

    def __init__(self, log_path: str = "logs/tool_calls.log"):
        self.log_path = log_path
        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def on_tool_start(
        self,
        serialized: Dict[str, Any],
        input_str: str,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        inputs: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        timestamp = datetime.datetime.now().isoformat()
        tool_name = serialized.get("name", "unknown_tool")
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] Tool Started: {tool_name} | Input: {input_str}\n")

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        timestamp = datetime.datetime.now().isoformat()
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] Tool Ended | Output: {str(output)[:200]}...\n")


def build_agent_executor(model_name: str = "gemini-2.5-flash"):
    """Build the agent executor with memory and tools."""
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.1)

    tools = [web_search, read_file]
    memory = MemorySaver()

    system_prompt = (
        "You are a helpful research assistant. "
        "You have access to two tools: web_search and read_file. "
        "IMPORTANT: Always check local files in the data/ directory first before "
        "searching the web. The file data/sample.txt contains a detailed research "
        "brief about Apple Inc. covering leadership, products, financials, history, "
        "competitors, and supply chain. The file data/sample.pdf contains information "
        "about Machine Learning basics and history. "
        "Use read_file on the relevant local file whenever the question could be "
        "answered from those documents. Only use web_search for current events, "
        "live data (stock prices, breaking news), or topics not covered in local files."
        "Be concise in your answers."
    )
    agent_executor = create_react_agent(
        llm,
        tools=tools,
        checkpointer=memory,
        prompt=system_prompt,
    )

    return agent_executor
