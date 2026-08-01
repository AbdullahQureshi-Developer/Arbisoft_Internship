import functools
import logging
import operator
import re
import time
from typing import Annotated, Sequence, TypedDict

from langchain_core.messages import BaseMessage, SystemMessage
from langchain_core.tools import StructuredTool
from langchain_anthropic import ChatAnthropic
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from mcp.client.session import ClientSession

tracer = logging.getLogger("mcp_agent.trace")
if not tracer.handlers:
    _handler = logging.StreamHandler()
    _handler.setFormatter(logging.Formatter("%(asctime)s [TRACE] %(message)s"))
    tracer.addHandler(_handler)
    tracer.setLevel(logging.INFO)
    tracer.propagate = False


def traced_tool_call(kind: str, name: str):
    """Decorator that logs a single tool call or resource fetch: name,
    arguments, duration, and outcome (success / error). `kind` is either
    "tool" or "resource", used to label the log line."""

    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(*args, **kwargs):
            call_args = kwargs if kwargs else (args if args else {})
            start = time.monotonic()
            tracer.info("CALL  kind=%s name=%s args=%s", kind, name, call_args)
            try:
                result = await fn(*args, **kwargs)
            except Exception as exc:
                elapsed_ms = (time.monotonic() - start) * 1000
                tracer.info(
                    "ERROR kind=%s name=%s duration_ms=%.1f error=%s",
                    kind,
                    name,
                    elapsed_ms,
                    exc,
                )
                raise
            elapsed_ms = (time.monotonic() - start) * 1000
            preview = str(result)
            if len(preview) > 200:
                preview = preview[:200] + "...(truncated)"
            tracer.info(
                "OK    kind=%s name=%s duration_ms=%.1f result=%s",
                kind,
                name,
                elapsed_ms,
                preview,
            )
            return result

        return wrapper

    return decorator


# Agent State
class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next_node: str


# --- Routing patterns & pure routing function -------------------------------
# Pulled out to module level (instead of nested inside build_graph) so the
# routing logic can be unit-tested directly, without mocking an MCP session
# or compiling a graph. See test_agent.py::test_determine_route.
INFO_PATTERN = re.compile(r"\b(weather|time|policy|handbook|date)\b", re.IGNORECASE)
# The bare-symbol alternatives require a digit on each side of the operator,
# so they only fire on actual arithmetic ("5 + 5", "12/4") and not on
# ordinary punctuation like hyphenated words ("co-worker", "sci-fi").
# The minus sign specifically also requires whitespace on both sides
# (\d\s+-\s+\d rather than \d\s*-\s*\d) — without that, digit-hyphen-digit
# still matches inside dates like "07-20-2026", which don't have spaces
# around the hyphen the way a written-out subtraction like "10 - 3" does.
COMPUTE_PATTERN = re.compile(
    r"\b(calculate|math|convert|temperature|count|words?)\b"
    r"|\d\s*[\+\*\/]\s*\d"
    r"|\d\s+-\s+\d",
    re.IGNORECASE,
)


def determine_route(content: str) -> str:
    """Pure function: decide which worker should handle a human message.

    Returns one of "info_worker", "compute_worker", or "FINISH".
    Unmatched messages fall through to FINISH with no response.
    """
    if INFO_PATTERN.search(content):
        return "info_worker"
    elif COMPUTE_PATTERN.search(content):
        return "compute_worker"
    return "FINISH"


COMPUTE_SYSTEM_PROMPT = (
    "You are a computation assistant. Use the available tools (calculate, "
    "convert_temperature, word_count) whenever the user's request needs "
    "one of them, rather than computing the answer yourself. Report results "
    "clearly and concisely."
)

INFO_SYSTEM_PROMPT = (
    "You are an information-lookup assistant. Use the available tools "
    "(get_weather, get_current_time, get_student_handbook, "
    "get_company_policy) whenever the user's request needs current or "
    "reference information, rather than guessing. Report results clearly "
    "and concisely."
)


def build_graph(mcp_session: ClientSession):
    llm = ChatAnthropic(model="claude-sonnet-4-6", temperature=0, max_tokens=500)

    @traced_tool_call("tool", "calculate")
    async def mcp_calculate(expression: str) -> str:
        """Perform mathematical calculations on an expression."""
        result = await mcp_session.call_tool("calculate", {"expression": expression})
        return str(result.content)

    @traced_tool_call("tool", "get_weather")
    async def mcp_get_weather(city: str) -> str:
        """Return weather information for a given city."""
        result = await mcp_session.call_tool("get_weather", {"city": city})
        return str(result.content)

    @traced_tool_call("tool", "get_current_time")
    async def mcp_get_current_time() -> str:
        """Return the current date and time."""
        result = await mcp_session.call_tool("get_current_time", {})
        return str(result.content)

    @traced_tool_call("tool", "convert_temperature")
    async def mcp_convert_temperature(value: float, unit: str) -> str:
        """Convert between Celsius and Fahrenheit."""
        result = await mcp_session.call_tool(
            "convert_temperature", {"value": value, "unit": unit}
        )
        return str(result.content)

    @traced_tool_call("tool", "word_count")
    async def mcp_word_count(text: str) -> str:
        """Count words in text."""
        result = await mcp_session.call_tool("word_count", {"text": text})
        return str(result.content)

    @traced_tool_call("resource", "student_handbook")
    async def mcp_get_student_handbook() -> str:
        """Get the student handbook from the MCP server."""
        result = await mcp_session.read_resource("app://docs/student_handbook")
        return str(result.contents)

    @traced_tool_call("resource", "company_policy")
    async def mcp_get_company_policy() -> str:
        """Get the company policy from the MCP server."""
        result = await mcp_session.read_resource("app://docs/company_policy")
        return str(result.contents)

    # --- LangChain Tools ---
    calc_tool = StructuredTool.from_function(
        coroutine=mcp_calculate,
        name="calculate",
        description="Perform mathematical calculations on an expression.",
    )
    weather_tool = StructuredTool.from_function(
        coroutine=mcp_get_weather,
        name="get_weather",
        description="Return weather information for a given city.",
    )
    time_tool = StructuredTool.from_function(
        coroutine=mcp_get_current_time,
        name="get_current_time",
        description="Return the current date and time.",
    )
    temp_tool = StructuredTool.from_function(
        coroutine=mcp_convert_temperature,
        name="convert_temperature",
        description="Convert between Celsius and Fahrenheit. unit is 'C' or 'F'.",
    )
    word_tool = StructuredTool.from_function(
        coroutine=mcp_word_count, name="word_count", description="Count words in text."
    )
    handbook_tool = StructuredTool.from_function(
        coroutine=mcp_get_student_handbook,
        name="get_student_handbook",
        description="Get the student handbook from the MCP server.",
    )
    policy_tool = StructuredTool.from_function(
        coroutine=mcp_get_company_policy,
        name="get_company_policy",
        description="Get the company policy from the MCP server.",
    )

    # Group tools by domain
    compute_tools_list = [calc_tool, temp_tool, word_tool]
    info_tools_list = [weather_tool, time_tool, handbook_tool, policy_tool]

    compute_llm = llm.bind_tools(compute_tools_list)
    info_llm = llm.bind_tools(info_tools_list)

    # --- Nodes ---
    async def supervisor_node(state: AgentState):
        messages = state.get("messages", [])
        if not messages:
            return {"next_node": "FINISH"}

        last_message = messages[-1]

        # Only route human messages to workers. If an AI just responded, we finish.
        if last_message.type != "human":
            return {"next_node": "FINISH"}

        content = str(last_message.content)
        route = determine_route(content)
        tracer.info("ROUTE next_node=%s query=%r", route, content[:120])
        return {"next_node": route}

    async def compute_worker_node(state: AgentState):
        messages = [SystemMessage(content=COMPUTE_SYSTEM_PROMPT), *state["messages"]]
        response = await compute_llm.ainvoke(messages)
        return {"messages": [response]}

    async def info_worker_node(state: AgentState):
        messages = [SystemMessage(content=INFO_SYSTEM_PROMPT), *state["messages"]]
        response = await info_llm.ainvoke(messages)
        return {"messages": [response]}

    compute_tools_node = ToolNode(compute_tools_list)
    info_tools_node = ToolNode(info_tools_list)

    # --- Build Graph ---
    workflow = StateGraph(AgentState)
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("compute_worker", compute_worker_node)
    workflow.add_node("info_worker", info_worker_node)

    workflow.add_node("compute_tools", compute_tools_node)
    workflow.add_node("info_tools", info_tools_node)

    # Routing from tools back to workers
    workflow.add_edge("compute_tools", "compute_worker")
    workflow.add_edge("info_tools", "info_worker")

    # Routing from workers to tools or supervisor
    def compute_router(state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "compute_tools"
        return "supervisor"

    def info_router(state: AgentState):
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "info_tools"
        return "supervisor"

    workflow.add_conditional_edges("compute_worker", compute_router)
    workflow.add_conditional_edges("info_worker", info_router)

    # Supervisor routing
    def supervisor_router(state: AgentState):
        if state["next_node"] == "FINISH":
            return END
        return state["next_node"]

    workflow.add_conditional_edges("supervisor", supervisor_router)

    workflow.add_edge(START, "supervisor")

    return workflow.compile()
