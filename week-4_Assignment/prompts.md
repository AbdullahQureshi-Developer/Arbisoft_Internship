# Prompts for Week 4 Assignment

This file documents the prompts used to generate the week-4 research agent.

## Part 1 — AI Coding Assistant Prompts

### prompt:1
Build a research agent project in Python using `uv` for dependency management. Include `pytest`, `ruff`, and `pre-commit` in the setup. Set up the `pyproject.toml` accordingly, following standard practices.

### prompt:2
Implement a LangChain agent (`research_agent/agent.py`) using `create_tool_calling_agent`. The agent should have `ConversationBufferMemory` so it can recall facts from earlier in the session.

### prompt:3
Implement custom tools for the agent in `research_agent/tools.py`:
1. `WebSearchTool`: Use `serpapi` to perform web search using a `SERPAPI_API_KEY` from the environment. Parse organic results and the answer box.
2. `FileReadTool`: Allow reading local `.txt` and `.pdf` files. Use `pypdf` for the PDF parsing.

### prompt:4
Implement a hook that logs every tool call with timestamps. Create a `ToolCallLoggingCallbackHandler` inheriting from `BaseCallbackHandler` that writes to `logs/tool_calls.log` on `on_tool_start` and `on_tool_end`.

### prompt:5
Create a demo script `research_agent/demo.py` that initializes the agent and asks it a sequence of multi-hop questions:
1. Read a file `data/sample.txt` to find a company name.
2. Search the web for recent news about that company.
3. Test its memory by asking what the company name was again.

### prompt:6
Write a simple `pytest` unit test in `tests/test_tools.py` to ensure the `read_file` tool can properly read a text file and handles missing files gracefully.

### prompt:7
Build a Streamlit UI for the Research Agent in `research_agent/app.py`. Use `st.chat_message` to render the conversation and `st.session_state` to store the agent's memory thread ID across Streamlit re-runs. Add it to `pyproject.toml` as `agent-ui`.
