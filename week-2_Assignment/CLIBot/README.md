# CLIBot

A terminal chat app powered by [OpenRouter](https://openrouter.ai/).

## Setup

1. Install [uv](https://docs.astral.sh/uv/).
2. Copy the example env file and add your API key:

   ```bash
   cp .env.example .env
   ```

   Get a key from [openrouter.ai/keys](https://openrouter.ai/keys).

3. Install dependencies:

   ```bash
   uv sync
   ```

## Usage

Start an interactive chat session:

```bash
uv run clibot
```

Or run via the module entry point:

```bash
uv run python main.py
```

### Commands

| Command  | Description                    |
| -------- | ------------------------------ |
| `/help`  | Show available commands        |
| `/clear` | Clear conversation history     |
| `/model` | Show the current model         |
| `/quit`  | Exit the chat                  |

### Configuration

Set these in `.env`:

| Variable             | Default               | Description                          |
| -------------------- | --------------------- | ------------------------------------ |
| `OPENROUTER_API_KEY` | —                     | Your OpenRouter API key (required)   |
| `OPENROUTER_MODEL`   | `openai/gpt-4o-mini`  | Model slug from OpenRouter           |
| `OPENROUTER_APP_NAME`| `CLIBot`              | App name sent in `X-Title` header    |
| `OPENROUTER_SITE_URL`| —                     | Optional site URL for `HTTP-Referer` |

Browse models at [openrouter.ai/models](https://openrouter.ai/models).
