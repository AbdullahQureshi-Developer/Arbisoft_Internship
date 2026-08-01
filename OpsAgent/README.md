# OpsAgent — Slack-Native AI Assistant

OpsAgent is an intelligent, Slack-native multi-agent AI assistant designed to streamline engineering operations and team productivity with two core workflows:

1. **GitHub PR Review Workflow**: Automatically fetches PR diffs, analyzes code, posts structured code reviews to GitHub, and confirms status back in Slack.
2. **Task & Reminder Workflow**: Summarizes notes, extracts actionable tasks into memory, and schedules automated reminders delivered via Slack.

## Architecture

```
Slack (Bolt SDK / Socket Mode)
        ↓
Marshal Agent (LangGraph) — classifies intent, routes to workflow
        ↓
   ┌────────────────────┬─────────────────────────┐
   │  Workflow 1:        │  Workflow 2:            │
   │  GitHub Review      │  Task & Reminder        │
   └────────────────────┴─────────────────────────┘
        ↓
Shared Memory (SQLite via SQLAlchemy: tasks, reminders, actions_log)
        ↓
Global logging hook (@log_call) wraps every tool/agent call
```

## Setup Instructions

### Prerequisites
- Python 3.11+
- `uv` package manager

### Environment Configuration
Copy `.env.example` to `.env` and fill in required secrets:
```bash
cp .env.example .env
```

Required variables:
- `SLACK_APP_TOKEN`: Slack App-level Token (`xapp-...`) with `connections:write` scope
- `SLACK_BOT_TOKEN`: Slack Bot User OAuth Token (`xoxb-...`)
- `GITHUB_TOKEN`: GitHub Personal Access Token
- `ANTHROPIC_API_KEY`: Claude LLM API Key

### Running Locally
To run the FastAPI server and database initializer:
```bash
uv run uvicorn src.main:app --reload
```

To run the Slack Bot in Socket Mode:
```bash
uv run python -m src.slack.bot
```
