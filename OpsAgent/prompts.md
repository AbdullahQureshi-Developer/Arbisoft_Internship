# OpsAgent — Running Log of Prompts and Architectural Decisions

## Project Inception & Phase 0: Foundation

### Key Decisions
1. **Tech Stack Selection**:
   - Python 3.11 with `uv` for fast dependency resolution and execution.
   - Slack Bolt SDK in **Socket Mode** using `SLACK_APP_TOKEN` and `SLACK_BOT_TOKEN`. This allows local development and testing without requiring public webhook URLs/ngrok.
   - SQLAlchemy with SQLite (`opsagent.db`) for lightweight transactional persistence of `tasks`, `reminders`, and `actions_log`.
   - Custom `@log_call` decorator wrapping synchronous and asynchronous calls to fulfill full observability requirements.

2. **Database Schemas**:
   - `tasks`: stores task description, assignee, due_hint, status (`pending`, `completed`).
   - `reminders`: stores scheduled fire time, channel_id, user_id, message, delivery status.
   - `actions_log`: records func_name, inputs, outputs, status (`success`/`error`), and latency in ms.

## Phase 1: GitHub PR Review Workflow

### Key Decisions
1. **MCP Tools Integration**:
   - Implemented `get_pr` and `post_pr_comment` tools in `mcp_server/tools/github_tools.py` accessing GitHub REST API with `GITHUB_TOKEN`.
   - Implemented `github_agent.py` as a thin wrapper over MCP tools without internal LLM logic.
2. **Review Skill**:
   - `skills/review_skill.py` uses Claude API with `with_structured_output` returning `PRReviewResult(summary, issues, comment_text)`.

## Phase 2: Task & Reminder Workflow

### Key Decisions
1. **Notes Summarization & Task Extraction**:
   - `skills/summarization_skill.py`: Summarizes raw meeting text into `SummaryResult`.
   - `skills/task_extraction_skill.py`: Parses tasks, assignees, due dates, and reminder delay into `TaskExtractionResult`.
2. **Persistence & Scheduling**:
   - `agents/todo_agent.py`: Persists extracted tasks to SQLite `tasks` table.
   - `agents/reminder_agent.py`: Schedules reminders in SQLite `reminders` table and uses **APScheduler** background job polling every 15 seconds to deliver pending reminders via Slack Bolt.

## Phase 3: Unified Marshal Router & LangGraph Orchestration

### Key Decisions
1. **LangGraph StateGraph**:
   - Unified routing architecture in `marshal/graph.py` with intent classification node -> conditional edge -> workflow execution node.
2. **Fault Tolerance & Observability**:
   - Automatic retry logic (with backoff) on GitHub API calls.
   - Every single agent, skill, and tool invocation wrapped in `@log_call` for complete SQLite `actions_log` auditability.
