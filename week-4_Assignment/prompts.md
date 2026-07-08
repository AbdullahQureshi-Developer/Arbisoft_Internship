# Prompts for Week 4 Assignment

## A

### prompt:1

Set up a Python research agent project using uv for dependency management. Include pytest, ruff, and pre-commit from the start, with the pyproject.toml configured the standard way.

### prompt:2

Build out the LangChain agent in research_agent/agent.py using create_tool_calling_agent. It needs ConversationBufferMemory so it can actually remember things mentioned earlier in the conversation.

### prompt:3

Now the tools, in research_agent/tools.py. First is WebSearchTool, which hits SerpAPI for web search, reading the key from SERPAPI_API_KEY, and pulls out both the organic results and the answer box. Second is FileReadTool, which reads local .txt and .pdf files, using pypdf for the PDF side.

### prompt:4

Add a hook that logs every tool call with a timestamp. Create a ToolCallLoggingCallbackHandler that extends BaseCallbackHandler and writes to logs/tool_calls.log on both on_tool_start and on_tool_end.

### prompt:5

Write a demo script, research_agent/demo.py, that spins up the agent and walks it through a multi-hop task. First it reads data/sample.txt to pull out a company name. Then it searches the web for recent news on that company. Finally it asks what the company name was, to check that the memory actually works.

### prompt:6

Add a quick pytest unit test in tests/test_tools.py for the read_file tool, checking that it reads a text file correctly and does not break when the file is missing.

### prompt:7

Build a Streamlit UI for the agent in research_agent/app.py. Use st.chat_message for the conversation view, and st.session_state to keep the memory thread ID persistent across re-runs. Register it in pyproject.toml as agent-ui.
