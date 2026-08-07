# Phase 5 — Multi-User Support (Switchboard Workspace Rollout) Design Spec

## Executive Summary
This design specification details the rollout of multi-user data isolation for OpsAgent (Marshal) across the Switchboard Slack workspace.
Goal: Ensure any user in Slack receives fully isolated tasks, reminders, conversation history, and action logs with zero cross-user data leakage.

## Architectural Changes & Key Decisions

### 1. Database Models (`src/memory/models.py`)
- **`Task`**: Add `user_id` (`String(255)`, `nullable=False`, `index=True`).
- **`Reminder`**: Ensure `user_id` (`String(255)`, `nullable=False`, `index=True`) is indexed and strictly enforced across queries.
- **`ActionsLog`**: Add `user_id` (`String(255)`, `nullable=True`, `index=True`) so audit logs record the acting user context where available.
- **`ConversationHistory`**: Create a new table `conversation_history` with:
  - `id`: Integer primary key
  - `channel_id`: String(255), indexed
  - `user_id`: String(255), indexed
  - `role`: String(50) ('user' or 'assistant')
  - `message`: Text
  - `timestamp`: DateTime (UTC)

### 2. Data Access Layer (`src/memory/store.py`)
- **`create_task(user_id: str, description: str, assignee: Optional[str] = None, due_hint: Optional[str] = None) -> Task`**: Require `user_id`.
- **`get_tasks(user_id: str, status: Optional[str] = None) -> List[Task]`**: Require `user_id` as mandatory parameter to scope task reads.
- **`create_reminder(channel_id: str, user_id: str, message: str, fire_at: datetime, task_id: Optional[int] = None) -> Reminder`**: Enforce `user_id`.
- **`get_pending_reminders(now: Optional[datetime] = None) -> List[Reminder]`**: Fetches undelivered reminders up to `now` for background delivery.
- **`record_channel_message(channel_id: str, user_id: str, role: str, message: str) -> ConversationHistory`**: Record user-scoped history.
- **`get_channel_history(channel_id: str, user_id: str, limit: int = 10) -> List[ConversationHistory]`**: Filter history strictly by `(channel_id, user_id)`.
- **`log_action(func_name: str, inputs: str, outputs: str, status: str, latency_ms: float, user_id: Optional[str] = None) -> ActionsLog`**: Accept optional `user_id`.

### 3. Database Migration Strategy
- Since `opsagent.db` currently contains 33 task rows and 645 action log rows from earlier testing, `init_db()` will execute schema migration logic (`PRAGMA table_info`) to safely add missing columns (`user_id`) without dropping any data.
- Backfill default value for existing legacy rows: `DEFAULT_USER` (or `U_DEFAULT`).

### 4. Downstream Pipeline Scoping
- **`src/agents/todo_agent.py`**: Update `save_extracted_tasks` to accept `user_id: str` and pass it to `create_task`.
- **`src/agents/reminder_agent.py`**: Ensure `ScheduleReminderRequest` and delivery pipeline preserve `user_id` and deliver reminders to the user's specific channel/DM.
- **`src/marshal/graph.py`**: Thread `user_id` from state into all downstream tasks, reminders, context lookups, and logs.
- **`src/slack/bot.py`**: Capture `user_id` and `channel_id` from Slack events and pass to `process_slack_message`.

### 5. Multi-User Integration Testing (`tests/test_integration.py`)
Simulate two concurrent users (`U_ALICE` and `U_BOB`) to verify:
1. `U_ALICE`'s task list never returns `U_BOB`'s tasks.
2. Reminders fire to the correct user channel.
3. Conversation history lookups return strictly user-isolated messages.

---
