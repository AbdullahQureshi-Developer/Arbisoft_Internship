# Phase 6 — Document Upload & Rich Extraction Design Spec

## Executive Summary
Phase 6 adds document parsing and rich extraction capabilities to OpsAgent (Marshal). When a user uploads a PDF or DOCX file to Slack, Marshal parses the raw text from the document, runs summarization, task extraction, and date/update extraction skills, and routes extracted dates to either internal reminders (<= 4 hours away) or Google Calendar events (> 4 hours away). Past dates are flagged as skipped. All operations are strictly scoped to the uploading user's `user_id`.

## System Components & Architectural Flow

```
Slack Message with File Attachment (PDF / DOCX)
          │
          ▼
   slack/bot.py (Detect file attachment & download using Bot token `url_private_download`)
          │
          ▼
   src/skills/document_parser.py (Extract raw text using pypdf / python-docx)
          │
          ▼
   src/marshal/graph.py (OpsAgent Graph)
          ├── Summarization Skill (summarize_text)
          ├── Task Extraction Skill (extract_tasks_and_reminders)
          └── Date Extraction Skill (src/skills/date_extraction_skill.py)
                │
                ▼ Returns Pydantic model:
                  ExtractedDatesAndUpdates(
                      dates: List[ExtractedDateItem(description, date: datetime)],
                      updates: List[str]
                  )
          │
          ▼ Routing Rule Evaluation (per extracted date item):
            time_until = date - now()
            ├── time_until < 0  ==> Flag as "already past — not scheduled"
            ├── time_until <= 4 hours ==> Schedule internal reminder via reminder_agent.py (fire_at = exact date/time)
            └── time_until > 4 hours  ==> Schedule Google Calendar event via calendar_agent.py (start_time = date, end_time = date + 30m)
          │
          ▼
   Slack Confirmation Response (Summary, Tasks, Date Routing details, Notable Updates)
```

## Detailed Component Specifications

### 1. Dependencies (`pyproject.toml`)
- `pypdf`: For PDF text extraction.
- `python-docx`: For DOCX text extraction.

### 2. Document Parser (`src/skills/document_parser.py`)
- Function: `parse_document(file_bytes: bytes, filename: str) -> str`
- Inspects extension (`.pdf` vs `.docx` / `.doc`).
- PDF: Uses `pypdf.PdfReader(io.BytesIO(file_bytes))` to extract text page by page.
- DOCX: Uses `docx.Document(io.BytesIO(file_bytes))` to extract text paragraph by paragraph.
- Returns raw string extracted from document.

### 3. Date & Updates Extraction Skill (`src/skills/date_extraction_skill.py`)
- Pydantic Models:
  ```python
  class ExtractedDateItem(BaseModel):
      description: str
      date: datetime  # ISO format / parsed datetime

  class ExtractedDatesAndUpdates(BaseModel):
      dates: List[ExtractedDateItem]
      updates: List[str]
  ```
- Skill Function: `extract_dates_and_updates(text: str, reference_now: Optional[datetime] = None) -> ExtractedDatesAndUpdates`
- Calls Anthropic Claude API via Structured Output / `with_structured_output` or JSON parsing.

### 4. Graph Pipeline Update (`src/marshal/graph.py`)
- Extend `OpsAgentState` to include `file_bytes: Optional[bytes]` and `file_name: Optional[str]`.
- Add `document_processing_step`:
  1. Parse document text via `parse_document`.
  2. Run summarization, task extraction, date extraction in parallel / sequence.
  3. Route each date item:
     - `time_until < 0`: Mark skipped ("already past — not scheduled").
     - `time_until <= 4h`: Calculate `delay_seconds = int(time_until.total_seconds())`, schedule reminder via `schedule_new_reminder`.
     - `time_until > 4h`: Call `schedule_calendar_event` via `calendar_agent.py`.
  4. Format confirmation message.

### 5. Slack Bot File Interception (`src/slack/bot.py`)
- In `handle_slack_message`: Check if `event` contains `files` array (or `file_shared`).
- If files attached: Fetch `url_private_download` using HTTP GET with `Authorization: Bearer <SLACK_BOT_TOKEN>`.
- Pass `file_bytes` and `file_name` into `process_slack_message`.

---
