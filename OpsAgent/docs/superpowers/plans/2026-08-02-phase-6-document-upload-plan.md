# Phase 6 — Document Upload & Rich Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to upload PDF or DOCX files to Slack, extract raw text, run rich date/update extraction, route dates to internal reminders (<= 4h) or Google Calendar (> 4h), and return a formatted summary.

**Architecture:** Integrate `pypdf` and `python-docx` for document parsing, build `date_extraction_skill.py`, implement date-routing logic in `graph.py`, and wire Slack file download in `slack/bot.py`.

**Tech Stack:** Python, pypdf, python-docx, LangChain Anthropic, LangGraph, Slack Bolt, pytest.

---

### Task 1: Dependencies & Document Parser Skill

**Files:**
- Modify: `pyproject.toml`
- Create: `src/skills/document_parser.py`
- Test: `tests/test_document_parser.py`

- [ ] **Step 1: Add `pypdf` and `python-docx` dependencies via `uv add pypdf python-docx`**
- [ ] **Step 2: Write failing test in `tests/test_document_parser.py`**
- [ ] **Step 3: Run test to verify it fails**
- [ ] **Step 4: Implement `src/skills/document_parser.py` supporting PDF and DOCX text extraction**
- [ ] **Step 5: Run test to verify it passes**
```bash
uv run pytest tests/test_document_parser.py -v
```

---

### Task 2: Date Extraction Skill

**Files:**
- Create: `src/skills/date_extraction_skill.py`
- Test: `tests/test_date_extraction_skill.py`

- [ ] **Step 1: Write failing test in `tests/test_date_extraction_skill.py` with mock LLM response**
- [ ] **Step 2: Run test to verify it fails**
- [ ] **Step 3: Implement `src/skills/date_extraction_skill.py` using Claude structured output**
- [ ] **Step 4: Run test to verify it passes**
```bash
uv run pytest tests/test_date_extraction_skill.py -v
```

---

### Task 3: Graph Integration & Date Routing Logic

**Files:**
- Modify: `src/marshal/graph.py`
- Modify: `src/slack/bot.py`
- Test: `tests/test_document_routing_integration.py`

- [ ] **Step 1: Write integration test for document processing and date routing (<=4h reminder, >4h calendar, past skipped)**
- [ ] **Step 2: Update `graph.py` state and routing rules for file attachments and dates**
- [ ] **Step 3: Update `slack/bot.py` to download file attachments using `url_private_download`**
- [ ] **Step 4: Run integration test and full test suite to verify 100% pass**
```bash
uv run pytest -v
```
