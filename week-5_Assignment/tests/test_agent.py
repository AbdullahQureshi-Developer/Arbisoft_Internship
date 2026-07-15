import pytest
from unittest.mock import AsyncMock
from src.agent.graph import build_graph, determine_route
from dotenv import load_dotenv


@pytest.mark.asyncio
async def test_build_graph():
    load_dotenv()
    # Mock the ClientSession
    mock_session = AsyncMock()

    # Ensure build_graph returns a compiled StateGraph
    graph = build_graph(mock_session)
    assert graph is not None
    assert hasattr(graph, "invoke") or hasattr(graph, "ainvoke")


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
    ],
)
def test_determine_route_general_fallback(content):
    # Previously these fell through to FINISH with no response at all.
    assert determine_route(content) == "general_worker"


def test_determine_route_info_takes_priority_over_compute():
    # "convert the temperature" contains both an info-ish word ("temperature")
    # and compute-ish words ("convert"); info_pattern is checked first.
    content = "what's the weather like, and can you convert 100F to Celsius?"
    assert determine_route(content) == "info_worker"
