"""Memory (checkpointer) construction for the research agent.

Kept behind a small factory function, rather than instantiating
MemorySaver directly inside agent construction, so the memory backend can
be swapped later (e.g. for a persistent SQLite/Postgres checkpointer) or
unit-tested in isolation without needing to build the whole agent.
"""

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver


def build_memory() -> BaseCheckpointSaver:
    """Build the checkpointer used for conversation memory.

    Currently an in-memory MemorySaver, meaning conversation history does
    not survive a process restart. Swap the implementation here if that
    changes (e.g. SqliteSaver) -- callers don't need to know which backend
    is in use.
    """
    return MemorySaver()
