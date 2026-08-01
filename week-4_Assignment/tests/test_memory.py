from langgraph.checkpoint.memory import MemorySaver

from research_agent.memory import build_memory


def test_build_memory_returns_memory_saver():
    memory = build_memory()
    assert isinstance(memory, MemorySaver)


def test_build_memory_returns_a_fresh_instance_each_call():
    # Each agent session should get its own checkpointer instance rather
    # than accidentally sharing state via a module-level singleton.
    assert build_memory() is not build_memory()
