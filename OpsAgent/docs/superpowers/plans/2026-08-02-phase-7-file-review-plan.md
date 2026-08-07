# Phase 7 — GitHub Agent: File Review Capability Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to request direct full-file code reviews by repo and file path, with optional user-confirmed PR comment posting.

**Architecture:** Implement `get_file_content` MCP tool, extend `github_agent.py`, create `file_review_skill.py`, update `router.py` classifier, and implement `github_file_review_step` in `graph.py`.

**Tech Stack:** Python, GitHub REST API, FastMCP, LangChain Anthropic, LangGraph, pytest.

---

### Task 1: MCP Tool & GitHub Agent Extension

**Files:**
- Modify: `src/mcp_server/tools/github_tools.py`
- Modify: `src/mcp_server/server.py`
- Modify: `src/agents/github_agent.py`
- Test: `tests/test_github_agent.py`

- [ ] **Step 1: Add `get_file_content` tool to `github_tools.py` and register in `server.py`**
- [ ] **Step 2: Extend `github_agent.py` with `fetch_file_content` wrapper method**
- [ ] **Step 3: Write test in `tests/test_github_agent.py` to verify `fetch_file_content`**
- [ ] **Step 4: Run test to verify it passes**
```bash
uv run pytest tests/test_github_agent.py -v
```

---

### Task 2: File Review Skill & Router Classification

**Files:**
- Create: `src/skills/file_review_skill.py`
- Modify: `src/marshal/router.py`
- Test: `tests/test_file_review_skill.py`
- Modify: `tests/test_router.py`

- [ ] **Step 1: Write failing test in `tests/test_file_review_skill.py`**
- [ ] **Step 2: Implement `src/skills/file_review_skill.py`**
- [ ] **Step 3: Add `github_file_review` intent to `router.py` and write router test in `tests/test_router.py`**
- [ ] **Step 4: Run tests to verify they pass**
```bash
uv run pytest tests/test_file_review_skill.py tests/test_router.py -v
```

---

### Task 3: Graph Workflow Integration & Confirmation Flow

**Files:**
- Modify: `src/marshal/graph.py`
- Test: `tests/test_file_review_integration.py`

- [ ] **Step 1: Write integration test covering standalone file review and review-plus-confirmed-PR-comment**
- [ ] **Step 2: Implement `github_file_review_step` and route logic in `graph.py`**
- [ ] **Step 3: Run integration test and full test suite to verify 100% pass**
```bash
uv run pytest -v
```
