# Week 5 Assignment: MCP LangGraph Agent Chat

This repository contains an agentic chat application built with **LangGraph**, **Streamlit**, and the **Model Context Protocol (MCP)**. The core intelligent agent utilizes the **Anthropic Claude API** to intelligently route requests to specialized workers, which then query an MCP Server for data and calculations.

## Features

* **Multi-Agent Architecture**: Built with LangGraph. A supervisor agent routes queries to specialized workers — `compute_worker` or `info_worker`. Queries that don't match either (no info/compute keyword) intentionally get no response, keeping the agent scoped to what the MCP server actually exposes rather than free-chatting outside its tools.
* **MCP Server Integration**: The backend server is developed using `FastMCP` exposing resources and tools over standard I/O (stdio).
* **Anthropic Claude**: Powered by Claude (via `langchain-anthropic`) to process natural language queries and decide when to call a tool.
* **Interactive UI**: A Streamlit frontend providing a modern chat experience, with a sidebar button to clear the conversation.
* **Specialized Tools**:
  * **Compute tools**: Math calculator (`calculate`), Temperature conversion (`convert_temperature`), Text processing (`word_count`).
  * **Info tools**: Live weather (`get_weather`), Current Time (`get_current_time`), Handbook reading (`get_student_handbook`), Policy reading (`get_company_policy`).
* **Package Management**: Uses `uv` for fast dependency resolution.

## Prerequisites

* Python >= 3.11
* `uv` package manager installed
* Anthropic API Key

## Setup & Installation

1. **Clone the repository and install dependencies:**
   Using `uv` to manage the environment and install dependencies:
   ```bash
   uv sync
   ```

2. **Configure Environment Variables:**
   Create a `.env` file in the root directory (see `.env.example` for the full list) with your Anthropic API key:
   ```env
   ANTHROPIC_API_KEY="your-anthropic-api-key"
   ```
   The app checks for this key on startup and will show an error in the UI if it's missing, rather than failing partway through a chat.

   *(Optional)* LangSmith tracing — logs every graph run to the LangSmith UI. Leave `LANGSMITH_TRACING` unset or `false` to skip it entirely; the app works the same either way.
   ```env
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY="your-langsmith-api-key"
   LANGSMITH_PROJECT="Week-5_Assignment"
   ```
   Never commit your `.env` file or paste real key values anywhere outside it — treat any key that leaks (chat, logs, commits) as compromised and rotate it immediately.

## Running the Application

Start the Streamlit application using `uv`:

```bash
uv run streamlit run src/ui/app.py
```

The Streamlit interface will open in your default browser. From there, you can ask the agent things like:

* *"What's the weather in New York right now?"*
* *"Calculate 250 * 42 + 10"*
* *"What does the company policy say?"*
* *"Convert 100 Celsius to Fahrenheit"*

## Project Structure

* `src/mcp_server/server.py`: The FastMCP server defining the tools and resources.
* `src/agent/graph.py`: The LangGraph setup containing the supervisor, routing logic (`determine_route`), and specialized workers.
* `src/ui/app.py`: The Streamlit chat UI that bridges communication between the user and the agent.
* `tests/`: Contains `pytest` tests — end-to-end integration tests that drive the compiled graph through the info and compute routing paths (including the tool-call loop) with a mocked LLM/MCP session, plus direct unit tests of the routing logic in `determine_route`.

## Development

* **Testing:** Run tests via `uv`:
  ```bash
  uv run pytest
  ```
* **Linting:** Use `ruff` and `pre-commit` hooks for maintaining code quality.

## Known Limitations

* Chat history is intentionally **not** sent back to the agent on each turn (to save API tokens), so the agent has no memory of earlier messages in the conversation.
* `get_weather` depends on the external Open-Meteo API; requests are capped with a timeout, but the tool can still fail if that service is down or the city name can't be geocoded.
