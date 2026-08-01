# CLIBot

CLIBot is a modern Python CLI chat application powered by OpenRouter, built to demonstrate modern packaging, API consumption, and local model interaction.

## Project Structure

This is a unified repository using a `src/` layout:

- `src/clibot/cli.py`: The main conversational interface.
- `src/clibot/client.py`: The unified OpenRouter streaming client.
- `src/clibot/compare.py`: Tool to evaluate and compare response times and costs for multiple models simultaneously.
- `src/clibot/ollama_chat.py`: Local model exploration via Ollama.

## Requirements

- Python >= 3.11
- [uv](https://github.com/astral-sh/uv) (for dependency management and running)
- An OpenRouter API Key (for `clibot` and `clibot-compare`)
- A local Ollama instance (for `clibot-ollama`)

## Setup

1. Copy the `.env.example` file to `.env` and fill in your keys:
   ```bash
   cp .env.example .env
   ```
2. Install dependencies (optional, as `uv run` handles this automatically):
   ```bash
   uv sync
   ```

## How to Run

### Main Chat CLI
Starts a terminal-based chat session with your specified model.
```bash
uv run clibot
```

### Model Comparison
Compare responses, token counts, TTFT (time-to-first-token), and cost across three models simultaneously.
```bash
uv run clibot-compare --prompt "What is a monad?" --parallel
```

### Ollama Chat (Local)
Test local models (requires Ollama running locally).
```bash
uv run clibot-ollama
```

## Quality Gates

The project is configured with `ruff`, `mypy`, and `pytest`. To run tests and linters:

```bash
uv run ruff check
uv run ruff format --check
uv run mypy src/
uv run pytest
```
