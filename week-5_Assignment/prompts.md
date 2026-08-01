**Prompt 1**  
"I want to build a LangGraph agent that uses an MCP server with tools for weather, time, calculation, and resources for handbooks. Suggest a folder structure and initial files."

**Prompt 2**  
"Write a FastMCP server that provides: calculate, get_weather, get_current_time, convert_temperature, word_count as tools, and student_handbook, company_policy as resources. Use Open‑Meteo API for weather."

**Prompt 3**  
"The calculate tool should safely evaluate mathematical expressions. Write a safe_eval function using ast that allows only basic arithmetic and limits exponent magnitude."

**Prompt 4**  
"Define the AgentState TypedDict with messages (Annotated list with operator.add) and a next_node field."

**Prompt 5**  
"Write a pure function determine_route that looks for keywords in a user message and returns 'info_worker', 'compute_worker', or 'FINISH'. Use regex patterns."

**Prompt 6**  
"Create a build_graph function that takes an MCP ClientSession. It should create the supervisor, info_worker, compute_worker, and the tool nodes. Use conditional edges to route between them."

**Prompt 7**  
"Write system prompts for the info worker and compute worker. They should instruct the LLM to use the appropriate tools rather than guessing."

**Prompt 8**  
"I need a decorator to trace every tool call and resource fetch – log name, args, duration, and result preview. Implement traced_tool_call."

**Prompt 9**  
"Inside build_graph, define async functions that call mcp_session.call_tool or read_resource. Wrap them with the tracing decorator and convert to StructuredTool."

**Prompt 10**  
"After the worker nodes, we need to route back to the supervisor if no more tool calls are needed, or to the tool node if there are tool calls. Write compute_router and info_router functions."

**Prompt 11**  
"The supervisor node should read the last message; if it's human, call determine_route and set next_node. If it's AI, return FINISH. Then add a conditional edge from supervisor to either worker or END."

**Prompt 12**  
"Write pytest parameterized tests for determine_route, covering info, compute, and fallback cases. Include a test that verifies info takes priority over compute."

**Prompt 13**  
"Create an async test that mocks the MCP session, calls build_graph, and asserts the returned graph has invoke/ainvoke methods."

**Prompt 14**  
"Build a Streamlit app that shows chat history, a sidebar button to clear, and an input. It should use asyncio.run to call the agent."

**Prompt 15**  
"In the run_agent function, start a stdio_client to the MCP server, initialize the session, build the graph, and stream the response. Keep the last 4 messages for context."

**Prompt 16**  
"Wrap the agent call in try/except. Unwrap any ExceptionGroup from asyncio to get the root cause. Display user‑friendly messages for rate limits and generic errors."

**Prompt 17**  
"Sometimes Claude returns content as a list of dictionaries with 'text' keys. Parse that and join into a string before displaying."

**Prompt 18**  
"Add a logger (mcp_agent.trace) that outputs to console with a specific format. Include timestamps and duration in milliseconds."

**Prompt 19**  
"When invoking the graph, use astream with a recursion_limit of 20. Collect the final AIMessage content from the stream."

**Prompt 20**  
"Load ANTHROPIC_API_KEY from .env. If missing, show an error in the Streamlit sidebar and stop execution."

**Prompt 21**  
"In server.py, use os.path.dirname(file) to locate student_handbook.md and company_policy.md. Return appropriate content or a 'not found' message."

**Prompt 22**  
"If the MCP server raises an exception (e.g., city not found, invalid expression), the tool should return an error string instead of crashing the graph."

**Prompt 23**  
"Set up pytest with asyncio mark. Use unittest.mock.AsyncMock for the session in test_build_graph."

**Prompt 24**  
"Add a .pre‑commit‑config.yaml with ruff for linting and formatting. Also include a check for missing imports."

**Prompt 25**  
"Add docstrings to all public functions, especially the tools and the routing function. Explain the purpose of the decorator."

**Prompt 26**  
"Review the entire codebase for consistency, remove unnecessary imports, and ensure all async functions are properly awaited. Write a README that explains how to run the project."
