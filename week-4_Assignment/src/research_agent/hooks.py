"""LangChain callback handlers ("hooks") used by the research agent.

Kept separate from agent.py so a hook can be constructed and unit-tested
on its own, without needing to import or configure the LLM/tools/prompt
that make up agent construction.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Any, Dict, List, Optional
from uuid import UUID

from langchain_core.callbacks.base import BaseCallbackHandler


class ToolCallLoggingCallbackHandler(BaseCallbackHandler):
    """Callback handler that logs tool calls to a rotating log file.

    Uses the standard library `logging` module (via `RotatingFileHandler`)
    instead of manually opening/appending to the file on every call. This
    gives us:
      - thread-safe writes: each `Handler.emit()` call is protected by an
        internal lock, which matters once multiple concurrent Streamlit
        sessions share a process
      - log rotation, so the log file doesn't grow unbounded
      - standard log levels/formatting, so this integrates cleanly with
        any other logging config the app adds later
    """

    def __init__(self, log_path: str = "logs/tool_calls.log"):
        self.log_path = log_path

        # dirname("") happens when log_path is a bare filename with no
        # directory component (e.g. "tool_calls.log") -- makedirs("")
        # raises FileNotFoundError, so only create a directory if there is
        # one to create.
        log_dir = os.path.dirname(self.log_path)
        if log_dir:
            os.makedirs(log_dir, exist_ok=True)

        # Key the logger by the absolute log path so constructing this
        # handler multiple times with the same path (e.g. Streamlit
        # reruns) reuses the same underlying file handler instead of
        # stacking duplicate handlers / open file descriptors.
        self._logger = logging.getLogger(
            f"research_agent.tool_calls.{os.path.abspath(self.log_path)}"
        )
        self._logger.setLevel(logging.INFO)
        self._logger.propagate = False

        if not self._logger.handlers:
            handler = RotatingFileHandler(
                self.log_path,
                maxBytes=5 * 1024 * 1024,  # 5 MB
                backupCount=3,
                encoding="utf-8",
            )
            handler.setFormatter(logging.Formatter("[%(asctime)s] %(message)s"))
            self._logger.addHandler(handler)

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
        tool_name = serialized.get("name", "unknown_tool")
        self._logger.info("Tool Started: %s | Input: %s", tool_name, input_str)

    def on_tool_end(
        self,
        output: Any,
        *,
        run_id: UUID,
        parent_run_id: Optional[UUID] = None,
        **kwargs: Any,
    ) -> Any:
        self._logger.info("Tool Ended | Output: %s...", str(output)[:200])
