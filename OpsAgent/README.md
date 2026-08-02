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

## Development Workflow

This project uses **Superpowers-style skills** via the [agy-superpowers](https://www.npmjs.com/package/agy-superpowers) framework. Skill files live in `.agents/skills/` and are automatically detected by the Antigravity IDE, making them available as slash commands in the TUI.

### Available Slash Commands

| Command | Description |
|---|---|
| `/brainstorming` | Structured brainstorming and ideation workflow |
| `/writing-plans` | Write a detailed implementation plan before coding |
| `/executing-plans` | Execute an approved plan step-by-step |
| `/systematic-debugging` | Root-cause debugging with structured tracing |
| `/test-driven-development` | TDD workflow — write tests first, then code |
| `/requesting-code-review` | Prepare and request a code review |
| `/receiving-code-review` | Process and action incoming code review feedback |
| `/verification-before-completion` | Verify work is complete before marking done |
| `/finishing-a-development-branch` | Checklist for merging and closing a branch |
| `/subagent-driven-development` | Delegate tasks to parallel subagents |
| `/dispatching-parallel-agents` | Fan-out work across multiple agents |
| `/frontend-design` | UI/UX design workflow |
| `/frontend-developer` | Frontend implementation workflow |
| `/mobile-developer` | Mobile development workflow |
| `/product-manager` | Product requirements and planning workflow |
| `/using-superpowers` | Learn how to use the Superpowers skill system |
| `/using-git-worktrees` | Git worktree workflow for parallel branches |
| `/update-superpowers` | Update all skill files to the latest version |

### Updating Skills
To update all skill files to the latest version:
```bash
npx agy-superpowers@latest update
```

## Observability

LangSmith tracing is enabled automatically via environment variables configured in `.env`:

```env
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=your-langsmith-api-key
LANGSMITH_PROJECT=OpsAgent
```

Traces, agent decisions, skill executions, latency, and token consumption are automatically logged and visible at [smith.langchain.com](https://smith.langchain.com) under project **"OpsAgent"**.


