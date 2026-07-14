import logging

from research_agent.hooks import ToolCallLoggingCallbackHandler


def test_logging_handler_accepts_bare_filename(tmp_path, monkeypatch):
    # Regression test: log_path with no directory component used to raise
    # FileNotFoundError from os.makedirs("").
    monkeypatch.chdir(tmp_path)
    handler = ToolCallLoggingCallbackHandler(log_path="tool_calls.log")
    assert handler.log_path == "tool_calls.log"


def test_logging_handler_writes_log_entries(tmp_path):
    log_path = tmp_path / "logs" / "tool_calls.log"
    handler = ToolCallLoggingCallbackHandler(log_path=str(log_path))

    handler.on_tool_start({"name": "web_search"}, "query='test'", run_id=None)
    handler.on_tool_end("some result", run_id=None)

    # Flush the file handler(s) so the write is visible before we read it.
    for h in handler._logger.handlers:
        h.flush()

    contents = log_path.read_text(encoding="utf-8")
    assert "Tool Started: web_search" in contents
    assert "Tool Ended" in contents


def test_logging_handler_reuses_handler_for_same_path(tmp_path):
    # Constructing the handler twice with the same path (e.g. across
    # Streamlit reruns) should not stack duplicate file handlers.
    log_path = tmp_path / "tool_calls.log"
    first = ToolCallLoggingCallbackHandler(log_path=str(log_path))
    second = ToolCallLoggingCallbackHandler(log_path=str(log_path))

    assert first._logger is second._logger
    assert len(second._logger.handlers) == 1

    # Cleanup so later tests aren't affected by this logger name persisting
    # in the logging module's global registry.
    for h in list(second._logger.handlers):
        h.close()
        second._logger.removeHandler(h)
    logging.Logger.manager.loggerDict.pop(second._logger.name, None)
