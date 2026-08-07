# Phase 5 — Multi-User Support (Switchboard Workspace Rollout) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure per-user data isolation for tasks, reminders, actions log, and conversation history across OpsAgent (Marshal).

**Architecture:** Add `user_id` to SQLAlchemy models (`Task`, `Reminder`, `ActionsLog`, `ConversationHistory`), require `user_id` on all store CRUD operations, auto-migrate existing `opsagent.db` columns, thread `user_id` through `graph.py` and downstream agents, and verify with multi-user isolation tests.

**Tech Stack:** Python, SQLAlchemy, SQLite, LangGraph, pytest.

---

### Task 1: Update Database Models & Store with Multi-User Scoping & Migration

**Files:**
- Modify: `src/memory/models.py`
- Modify: `src/memory/store.py`
- Modify: `tests/test_memory_and_logging.py`

- [ ] **Step 1: Update `src/memory/models.py` to add `user_id` to `Task`, `ActionsLog`, and add `ConversationHistory` model**
- [ ] **Step 2: Update `src/memory/store.py` to require `user_id` in CRUD functions and add migration logic**
- [ ] **Step 3: Update `tests/test_memory_and_logging.py` with `user_id` arguments**
- [ ] **Step 4: Run tests to verify store and model tests pass**
```bash
uv run pytest tests/test_memory_and_logging.py -v
```

---

### Task 2: Thread `user_id` through Agents, Graph, and Slack Bot

**Files:**
- Modify: `src/agents/todo_agent.py`
- Modify: `src/agents/reminder_agent.py`
- Modify: `src/marshal/graph.py`
- Modify: `src/slack/bot.py`

- [ ] **Step 1: Update `todo_agent.py` `save_extracted_tasks(tasks, user_id)`**
- [ ] **Step 2: Update `reminder_agent.py` to deliver reminders to user's channel/DM**
- [ ] **Step 3: Update `graph.py` to thread `user_id` to `save_extracted_tasks`, context history, etc.**
- [ ] **Step 4: Update `slack/bot.py` to pass `user_id` into graph**

---

### Task 3: Multi-User Isolation Integration Tests

**Files:**
- Modify: `tests/test_integration.py`

- [ ] **Step 1: Add `test_multi_user_data_isolation` in `tests/test_integration.py` simulating Alice and Bob**
- [ ] **Step 2: Run full test suite and confirm 100% pass**
```bash
uv run pytest -v
```
