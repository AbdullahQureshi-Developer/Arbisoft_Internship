import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.agent.graph import (
    build_graph,
    determine_route,
    INFO_SYSTEM_PROMPT,
    GENERAL_SYSTEM_PROMPT,
)
from dotenv import load_dotenv
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage


@pytest.mark.asyncio
async def test_build_graph():
    load_dotenv()
    # Mock the ClientSession
    mock_session = AsyncMock()

    # Ensure build_graph returns a compiled StateGraph
    graph = build_graph(mock_session)
    assert graph is not None
    assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")


# --- End-to-end routing tests --------------------------------------------
# test_build_graph above only checks that build_graph() returns *something*
# invokable -- it never calls .invoke()/.ainvoke(), so it never exercises the
# routing edges, the tool-call loop, or the supervisor's FINISH/END path.
# These tests mock ChatAnthropic and the MCP ClientSession, then actually
# drive the compiled graph with graph.ainvoke() for an info query, a compute
# query (including a full tool-call round trip), and an unmatched/general
# query, asserting on the final message content in each case.


def _make_fake_llm(responses):
    """Stand-in for ChatAnthropic: .ainvoke() replays `responses` in order
    (one AIMessage per call), and .bind_tools() returns itself so
    compute_llm/info_llm/plain-llm all share the same call queue."""
    fake_llm = MagicMock()
    fake_llm.bind_tools.return_value = fake_llm
    fake_llm.ainvoke = AsyncMock(side_effect=responses)
    return fake_llm


@pytest.mark.asyncio
async def test_graph_info_query_end_to_end():
    final_reply = AIMessage(content="It's 20°C in Paris.", tool_calls=[])
    fake_llm = _make_fake_llm([final_reply])
    mock_session = AsyncMock()

    with patch("src.agent.graph.ChatAnthropic", return_value=fake_llm):
        graph = build_graph(mock_session)
        result = await graph.ainvoke(
            {
                "messages": [HumanMessage(content="What's the weather in Paris?")],
                "next_node": "",
            },
            {"recursion_limit": 20},
        )

    last_message = result["messages"][-1]
    assert last_message.content == "It's 20°C in Paris."
    assert not last_message.tool_calls
    # Confirm info_worker (not compute_worker or general_worker) actually ran.
    called_messages = fake_llm.ainvoke.call_args.args[0]
    assert called_messages[0].content == INFO_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_graph_general_query_end_to_end():
    final_reply = AIMessage(content="Happy to help however I can!", tool_calls=[])
    fake_llm = _make_fake_llm([final_reply])
    mock_session = AsyncMock()

    with patch("src.agent.graph.ChatAnthropic", return_value=fake_llm):
        graph = build_graph(mock_session)
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="hi there")], "next_node": ""},
            {"recursion_limit": 20},
        )

    last_message = result["messages"][-1]
    assert last_message.content == "Happy to help however I can!"
    assert not last_message.tool_calls
    # Confirm general_worker (the previously-missing node) actually ran,
    # rather than the graph silently ending with no messages added.
    called_messages = fake_llm.ainvoke.call_args.args[0]
    assert called_messages[0].content == GENERAL_SYSTEM_PROMPT


@pytest.mark.asyncio
async def test_graph_compute_query_end_to_end_uses_tool_loop():
    # First LLM turn: model decides it needs the calculate tool.
    tool_call_reply = AIMessage(
        content="",
        tool_calls=[
            {
                "name": "calculate",
                "args": {"expression": "2 + 2"},
                "id": "call_1",
                "type": "tool_call",
            }
        ],
    )
    # Second LLM turn, after the tool result comes back: final answer.
    final_reply = AIMessage(content="2 + 2 = 4", tool_calls=[])
    fake_llm = _make_fake_llm([tool_call_reply, final_reply])

    mock_session = AsyncMock()
    mock_session.call_tool = AsyncMock(return_value=MagicMock(content="4"))

    with patch("src.agent.graph.ChatAnthropic", return_value=fake_llm):
        graph = build_graph(mock_session)
        result = await graph.ainvoke(
            {"messages": [HumanMessage(content="What is 2 + 2?")], "next_node": ""},
            {"recursion_limit": 20},
        )

    last_message = result["messages"][-1]
    assert last_message.content == "2 + 2 = 4"
    assert not last_message.tool_calls
    # The MCP session's calculate tool was actually invoked with the routed args.
    mock_session.call_tool.assert_awaited_once_with(
        "calculate", {"expression": "2 + 2"}
    )
    # A ToolMessage should sit between the two AI turns, proving the
    # compute_tools -> compute_worker loop actually ran (not just FINISH/END).
    tool_messages = [m for m in result["messages"] if isinstance(m, ToolMessage)]
    assert len(tool_messages) == 1
    assert tool_messages[0].content == "4"


# --- Routing tests -----------------------------------------------------
# determine_route is a pure function, so these run without mocking an
# MCP session or compiling a graph.


@pytest.mark.parametrize(
    "content",
    [
        "What's the weather in Paris?",
        "What time is it?",
        "Can you show me the company policy?",
        "Where can I find the student handbook?",
        "What's today's date?",
    ],
)
def test_determine_route_info(content):
    assert determine_route(content) == "info_worker"


@pytest.mark.parametrize(
    "content",
    [
        "Calculate 250 * 42 + 10",
        "Convert 100F to Celsius",
        "How many words are in this sentence?",
        "What is 5 + 5?",
        "12 / 4",
    ],
)
def test_determine_route_compute(content):
    assert determine_route(content) == "compute_worker"


@pytest.mark.parametrize(
    "content",
    [
        "hi there",
        "thanks!",
        "what can you do?",
        "tell me a joke",
        "my co-worker mentioned this",
        "I love sci-fi movies",
        "what happened on 07-20-2026",
    ],
)
def test_determine_route_general_fallback(content):
    # Unmatched messages fall through to general_worker, which gives a plain
    # conversational response instead of no response at all. This also
    # covers messages containing bare hyphens (hyphenated words, dates) that
    # must NOT be misrouted to compute_worker.
    assert determine_route(content) == "general_worker"


def test_determine_route_info_takes_priority_over_compute():
    # "convert the temperature" contains both an info-ish word ("temperature")
    # and compute-ish words ("convert"); info_pattern is checked first.
    content = "what's the weather like, and can you convert 100F to Celsius?"
    assert determine_route(content) == "info_worker"
