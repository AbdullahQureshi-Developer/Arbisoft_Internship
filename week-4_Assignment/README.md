# Week 4 Assignment: Research Agent

A research agent built with LangChain and LangGraph, featuring:
- 🔎 **Web search** (SerpAPI)
- 📄 **File reading** (`.txt` and `.pdf`), sandboxed to the project's `data/` directory
- 🧠 **Memory** — recalls facts across turns within a session (LangGraph checkpointer)
- 🪝 **Tool-call logging hook** — every tool invocation is logged to a rotating log file

## Project structure

```
week-4_Assignment/
├── src/research_agent/
│   ├── __init__.py
│   ├── agent.py      # agent construction, system prompt, response parsing (extract_text)
│   ├── config.py      # shared config (e.g. default model name, env-overridable)
│   ├── hooks.py        # ToolCallLoggingCallbackHandler (rotating file log)
│   ├── memory.py        # memory/checkpointer factory
│   └── tools.py          # web_search + read_file tools
├── tests/
│   ├── test_agent.py
│   ├── test_hooks.py
│   ├── test_memory.py
│   └── test_tools.py
├── data/                 # sample.txt, sample.pdf — read_file can only access this directory
├── logs/                 # tool_calls.log (rotating, created automatically on first run)
├── app.py                # Streamlit UI entrypoint
├── demo.py               # console demo entrypoint
├── pyproject.toml
└── .env                  # API keys (not committed — see Configuration below)
```

## Setup

```bash
uv sync
```

## Configuration

Create a `.env` file in the project root:

```bash
GEMINI_API_KEY=your_key_here
SERPAPI_API_KEY=your_key_here

# Optional — overrides the default model (gemini-3.5-flash) without touching code
RESEARCH_AGENT_MODEL=gemini-3.5-flash
```

## Run

**Console Demo:**
```bash
uv run agent-demo
```

**Streamlit UI:**
```bash
uv run agent-ui
```

## Testing

```bash
uv run pytest tests/ -v
```

Covers:
- `read_file` path-allowlisting (rejects `../` traversal, absolute paths, and access outside `data/`)
- Response-content parsing edge cases (empty lists, mixed content shapes)
- The tool-call logging hook (bare filenames, log writes, no duplicate handlers on reuse)
- The memory/checkpointer factory

## Security notes

`read_file` only reads files inside the project's `data/` directory. Requested paths are resolved and checked against that directory before anything is opened, which blocks directory traversal (`../../.env`), absolute paths (`/etc/passwd`), and symlink escapes — this matters because the LLM decides the file path argument itself, based on the conversation (including untrusted web search results), not just direct user input.

## Architecture

The package separates a few distinct concerns that used to live together in `agent.py`:

- **`agent.py`** — wires everything together: builds the LLM, attaches tools, sets the system prompt, and compiles the LangGraph agent. Also owns `extract_text()`, which normalizes the model's response content into a plain string.
- **`hooks.py`** — `ToolCallLoggingCallbackHandler`, a LangChain callback that logs every tool call (start/end, with input and output) to `logs/tool_calls.log` via a `RotatingFileHandler`. Kept separate so it can be constructed and tested without needing an LLM or tools configured.
- **`memory.py`** — `build_memory()`, a small factory that returns the LangGraph checkpointer (currently `MemorySaver`, in-process only — conversation history doesn't survive a restart). Kept behind a factory so the memory backend (e.g. a persistent SQLite/Postgres checkpointer) can be swapped later without touching agent construction.
- **`config.py`** — shared constants, currently just `DEFAULT_MODEL_NAME` (overridable via the `RESEARCH_AGENT_MODEL` env var), so the model name isn't duplicated across `agent.py`, `app.py`, and `demo.py`.
- **`tools.py`** — the `web_search` and `read_file` tools the agent can call.

This split means each piece — the hook, the memory backend, the tools — can be unit-tested in isolation, and swapping any one of them (a different log destination, a persistent memory backend, a different model) doesn't require touching the others.
