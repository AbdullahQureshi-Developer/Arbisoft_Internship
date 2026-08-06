# OpsAgent — Master Developer Prompt Blueprint & Architectural Log

This document provides a comprehensive, 7-phase master prompt playbook (70 prompts) to build the entire **OpsAgent** platform from scratch.

---

## Phase 1: Project Architecture, Environment & Logging Hooks (10 Prompts)

- **Prompt 1.1**: "Initialize a clean Python 3.11 project structure named `OpsAgent` with directory layout: `src/`, `src/agents/`, `src/skills/`, `src/marshal/`, `src/memory/`, `src/integrations/`, `src/mcp_server/`, `src/hooks/`, and `tests/`."
- **Prompt 1.2**: "Create `pyproject.toml` using `uv` dependencies including `fastapi`, `uvicorn`, `slack-sdk`, `slack-bolt`, `langchain-anthropic`, `langgraph`, `sqlalchemy`, `pydantic`, `httpx`, `apscheduler`, `google-api-python-client`, `google-auth-oauthlib`, and `python-dotenv`."
- **Prompt 1.3**: "Create a `.python-version` file specifying `3.11.9` and run `uv venv` to set up the virtual environment."
- **Prompt 1.4**: "Create a `.env.example` template with placeholder keys for `ANTHROPIC_API_KEY`, `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `GITHUB_TOKEN`, `DATABASE_URL`, and `DEFAULT_MODEL_NAME`."
- **Prompt 1.5**: "Create `.gitignore` configured to ignore `.venv/`, `__pycache__/`, `*.pyc`, `opsagent.db`, `.env`, and `.pytest_cache/`."
- **Prompt 1.6**: "Create `src/config.py` that loads `.env` and exports `DEFAULT_MODEL_NAME = os.getenv('DEFAULT_MODEL_NAME', os.getenv('ANTHROPIC_MODEL', 'claude-sonnet-5'))`."
- **Prompt 1.7**: "Create `src/llm_client.py` with a `get_llm()` helper function returning a `ChatAnthropic` instance configured with model fallback and default max output tokens `max_tokens=4096`."
- **Prompt 1.8**: "Create `src/hooks/logging_hook.py` defining an `@log_call` function decorator that logs function entry, execution latency in milliseconds, and exit status."
- **Prompt 1.9**: "Add string truncation to `logging_hook.py` so that serialized return outputs exceeding 2,000 characters are capped before being logged or stored."
- **Prompt 1.10**: "Update `@log_call` in `logging_hook.py` to record function calls (func_name, inputs, outputs, status, latency_ms) into SQLite via `src.memory.store.record_action_log` asynchronously/safely without crashing caller execution."

---

## Phase 2: Database Schema & Memory Persistence Layer (10 Prompts)

- **Prompt 2.1**: "Create `src/memory/models.py` setting up SQLAlchemy 2.0 `DeclarativeBase` and `mapped_column` type hints."
- **Prompt 2.2**: "In `models.py`, define the `ActionsLog` table with fields `id` (autoincrement PK), `user_id`, `func_name`, `inputs`, `outputs`, `status`, `latency_ms`, and `created_at`."
- **Prompt 2.3**: "In `models.py`, define the `ConversationHistory` table with fields `id`, `channel_id` (indexed), `user_id` (indexed), `role`, `message`, and `timestamp`."
- **Prompt 2.4**: "In `models.py`, define the `Task` table with fields `id`, `user_id` (indexed), `description`, `assignee`, `due_hint`, `status` ('pending'/'completed'), and `created_at`."
- **Prompt 2.5**: "In `models.py`, define the `Reminder` table with fields `id`, `user_id` (indexed), `channel_id`, `message`, `fire_at` (indexed), `delivered` (boolean, default False), `task_id`."
- **Prompt 2.6**: "In `models.py`, define the `UserGoogleToken` table with fields `user_id` (primary key) and `token_json` (Text), `updated_at`."
- **Prompt 2.7**: "In `src/memory/store.py`, initialize SQLite SQLAlchemy engine with WAL mode (`PRAGMA journal_mode=WAL;`), busy timeout of 10,000ms, and create a context-managed `get_db()` session helper."
- **Prompt 2.8**: "In `store.py`, add `init_db()` to create all tables and `record_channel_message(channel_id, user_id, role, message)` to append chat messages."
- **Prompt 2.9**: "In `store.py`, add `get_channel_history(channel_id, user_id, limit=10)` returning the 10 most recent messages strictly filtered by `(channel_id, user_id)`."
- **Prompt 2.10**: "In `store.py`, add task CRUD functions (`save_task`, `get_tasks`) and token storage functions (`save_user_google_token`, `get_user_google_token`). Use `Reminder.delivered.is_(False)` for clean lints."

---

## Phase 3: Domain Agents & MCP Tools (10 Prompts)

- **Prompt 3.1**: "Create `src/mcp_server/tools/github_tools.py` with `get_pr(repo, pr_number)` that calls GitHub REST API with `Accept: application/vnd.github.v3.diff` and returns PR title, diff text, and HTML URL."
- **Prompt 3.2**: "In `github_tools.py`, add `post_pr_review_comment(repo, pr_number, body)` that posts a comment via GitHub API `POST /repos/{repo}/issues/{pr_number}/comments`."
- **Prompt 3.3**: "In `github_tools.py`, add error handling so HTTP/API failures log errors and raise `RuntimeError` cleanly."
- **Prompt 3.4**: "Create `src/agents/github_agent.py` defining Pydantic models `FetchPRRequest`, `FetchPRResult`, `PostCommentRequest`, `PostCommentResult`, and functions `fetch_pr_diff()` and `post_review_comment()`."
- **Prompt 3.5**: "Create `src/mcp_server/tools/calendar_tools.py` with helper `_ensure_offset(dt_str)` that appends local timezone offset (`+05:00`) to naive ISO datetime strings."
- **Prompt 3.6**: "In `calendar_tools.py`, implement `create_event(title, start_time, end_time, attendees, user_id)` calling Google Calendar API via `get_calendar_service(user_id=user_id)`. If service is `None`, return `status: 'auth_required'` and auth URL."
- **Prompt 3.7**: "Create `src/agents/calendar_agent.py` defining Pydantic models `CreateEventRequest` (with `user_id`) and `CreateEventResult`, exposing `schedule_calendar_event()`."
- **Prompt 3.8**: "Create `src/agents/todo_agent.py` defining `SaveTasksRequest` and `save_extracted_tasks()` to persist tasks into SQLite for a given `user_id`."
- **Prompt 3.9**: "Create `src/agents/reminder_agent.py` with `schedule_new_reminder(request: ScheduleReminderRequest)` saving reminders to SQLite with `fire_at = now + delay_seconds`."
- **Prompt 3.10**: "In `reminder_agent.py`, implement `check_and_deliver_pending_reminders(slack_say)` and `start_reminder_scheduler(slack_say)` using `APScheduler` BackgroundScheduler running every 15 seconds."

---

## Phase 4: Intelligence Skills Pipeline & Document Processing (10 Prompts)

- **Prompt 4.1**: "Create `src/skills/document_parser.py` with `parse_document(file_bytes, filename)`. Extract plain text from `.pdf` files using `pdfplumber`/`pypdf` and `.docx` using `python-docx`."
- **Prompt 4.2**: "In `document_parser.py`, raise `ValueError` for unsupported file extensions and handle empty/corrupted document files gracefully."
- **Prompt 4.3**: "Create `src/skills/review_skill.py` defining `PRReviewResult(summary, issues, comment_text)` and `review_pr_diff(diff_text, title)` using Claude to generate structured PR code feedback."
- **Prompt 4.4**: "Create `src/skills/summarization_skill.py` defining `SummaryResult(summary)` and `summarize_text(text)` to produce concise bulleted meeting summaries."
- **Prompt 4.5**: "Create `src/skills/task_extraction_skill.py` defining `ExtractedTask(description, assignee, due_hint, reminder_delay_seconds)` and `TaskExtractionResult(tasks)`."
- **Prompt 4.6**: "In `task_extraction_skill.py`, write `extract_tasks_and_reminders(text)` using Claude structured outputs to parse action items from text."
- **Prompt 4.7**: "Create `src/skills/date_extraction_skill.py` defining `ExtractedDateItem`, `DateExtractionResult`, and `extract_dates_and_updates(text, reference_now)`."
- **Prompt 4.8**: "In `date_extraction_skill.py`, route dates due within 4 hours to internal reminders and dates beyond 4 hours to Google Calendar scheduling."
- **Prompt 4.9**: "Create `src/skills/event_extraction_skill.py` defining `EventExtractionResult(title, start_time, end_time, attendees)`."
- **Prompt 4.10**: "In `event_extraction_skill.py`, default the reference datetime to `datetime.now().astimezone()` so relative user queries like '2 PM' parse accurately to local ISO strings."

---

## Phase 5: Intent Router, LangGraph Engine & Marshal (10 Prompts)

- **Prompt 5.1**: "Create `src/marshal/router.py` defining `WorkflowIntent` Pydantic model with `intent_type` enum (`github_review`, `task_and_reminder`, `calendar_schedule`, `document_processing`, `unknown`)."
- **Prompt 5.2**: "In `router.py`, implement `classify_intent(message_text)` using Claude structured output to categorize incoming user messages."
- **Prompt 5.3**: "Create `src/marshal/graph.py` defining `OpsAgentState(TypedDict)` containing `message_text`, `channel_id`, `user_id`, `intent`, `file_bytes`, `file_name`, and `result_text`."
- **Prompt 5.4**: "In `graph.py`, implement `classify_step(state)` that calls `classify_intent()` and populates `state['intent']`."
- **Prompt 5.5**: "In `graph.py`, implement `github_review_step(state)` to fetch PR diffs, invoke `review_pr_diff()`, and format Slack responses or post comments."
- **Prompt 5.6**: "In `graph.py`, implement `task_reminder_step(state)` to summarize notes, save tasks, schedule reminders, and fall back to `get_tasks(user_id)` from SQLite if 0 new tasks are extracted."
- **Prompt 5.7**: "In `graph.py`, implement `calendar_schedule_step(state)` to extract event details and call `schedule_calendar_event()`. If auth is required, return an interactive authentication link."
- **Prompt 5.8**: "In `graph.py`, implement `document_processing_step(state)` using `ThreadPoolExecutor` to run summarization, task extraction, and date routing in parallel."
- **Prompt 5.9**: "In `graph.py`, implement `unknown_step(state)` using LLM to generate warm, natural 1-2 sentence conversational responses for greetings and thank-yous."
- **Prompt 5.10**: "In `graph.py`, build the `StateGraph(OpsAgentState)` workflow, add conditional edges via `route_decision()`, and expose `process_slack_message()`."

---

## Phase 6: Per-User OAuth, FastAPI Server & Slack Bot (10 Prompts)

- **Prompt 6.1**: "In `src/integrations/google/auth.py`, add `os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'` to allow local HTTP OAuth testing."
- **Prompt 6.2**: "In `auth.py`, implement `get_user_google_credentials(user_id)` to load, validate, and auto-refresh credentials from SQLite `user_google_tokens`."
- **Prompt 6.3**: "In `auth.py`, update `get_calendar_service(user_id)` to return the user's specific Google Calendar client, returning `None` if unauthenticated."
- **Prompt 6.4**: "Create `src/main.py` initializing a FastAPI app with a lifespan context manager that calls `init_db()` on startup."
- **Prompt 6.5**: "In `main.py`, add `GET /` returning API metadata and `GET /health` returning `{'status': 'healthy'}`."
- **Prompt 6.6**: "In `main.py`, add constant `FIXED_PKCE_VERIFIER = 'OpsAgentGoogleOAuthSecretVerifierKey12345678901234567890'`."
- **Prompt 6.7**: "In `main.py`, implement `GET /auth/google?user_id=...` that sets `flow.code_verifier = FIXED_PKCE_VERIFIER` and redirects user to Google OAuth login."
- **Prompt 6.8**: "In `main.py`, implement `GET /auth/google/callback` that receives auth code, sets `flow.code_verifier = FIXED_PKCE_VERIFIER`, exchanges token, and calls `save_user_google_token(user_id, token_json)`."
- **Prompt 6.9**: "Create `src/slack/bot.py` initializing Slack Bolt `App` with Socket Mode enabled (`SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`)."
- **Prompt 6.10**: "In `bot.py`, listen for `message` events, download files if attached, delegate processing to `process_slack_message()`, start `start_reminder_scheduler(say)`, and post responses back to Slack."

---

## Phase 7: Pytest Suite, Dockerization & DevOps Deployment (10 Prompts)

- **Prompt 7.1**: "Create `tests/test_config.py` verifying `DEFAULT_MODEL_NAME` loads correctly from environment variables."
- **Prompt 7.2**: "Create `tests/test_github_tools.py` testing `get_pr()` and `post_pr_review_comment()` with monkeypatched `httpx.Client` responses."
- **Prompt 7.3**: "Create `tests/test_memory_and_logging.py` testing SQLite WAL mode, message recording, task CRUD, and multi-user data isolation."
- **Prompt 7.4**: "Create `tests/test_document_parser.py` testing plain text extraction from test `.pdf` and `.docx` files."
- **Prompt 7.5**: "Create `tests/test_integration.py` and `tests/test_document_routing_integration.py` testing end-to-end execution of `process_slack_message()` across PR reviews, task extraction, date routing, and calendar scheduling."
- **Prompt 7.6**: "Run `.venv/Scripts/python -m pytest tests/` and verify that all 29 tests pass cleanly."
- **Prompt 7.7**: "Create `.dockerignore` excluding `.venv`, `__pycache__`, `*.pyc`, `.git`, `.env`, `opsagent.db`, `tests/`, and temporary build artifacts."
- **Prompt 7.8**: "Create `Dockerfile` based on `python:3.11-slim`. Copy `uv` from `ghcr.io/astral-sh/uv:latest`, copy `pyproject.toml` and `uv.lock`, run `uv sync --frozen --no-dev`, copy `src/`, expose port 8000, and set default CMD."
- **Prompt 7.9**: "Create `docker-compose.yml` defining two services:
  - `api`: Runs FastAPI (`uv run uvicorn src.main:app --host 0.0.0.0 --port 8000`).
  - `bot`: Runs Slack Bot (`uv run python -m src.slack.bot`).
  - Shared volume `sqlite_data` mounted at `/app/data` with `DATABASE_URL=sqlite:////app/data/opsagent.db`."
- **Prompt 7.10**: "Run `docker compose build` and `docker compose up -d` to verify both containerized services launch, connect to Slack, and pass health checks."
