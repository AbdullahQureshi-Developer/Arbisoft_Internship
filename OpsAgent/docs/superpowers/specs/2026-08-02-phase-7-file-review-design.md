# Phase 7 — GitHub Agent: File Review Capability Design Spec

## Executive Summary
Phase 7 extends OpsAgent with direct file review capabilities. A user can ask Marshal to review a specific file by repository and file path (e.g., "check my activity.py in week-5_Assignment repository") independent of any PR. If requested or confirmed by the user, the review can be posted to a target PR using the existing `post_pr_comment` tool. All states are scoped strictly per user (`user_id`).

## Architectural Components & Changes

### 1. MCP Tool: `get_file_content` (`src/mcp_server/tools/github_tools.py`)
- Tool signature: `get_file_content(repo: str, file_path: str, ref: str = "main") -> dict`
- REST Endpoint: `GET https://api.github.com/repos/{owner}/{repo}/contents/{file_path}?ref={ref}`
- Returns base64 decoded file content or plain text raw content.
- Registered in `src/mcp_server/server.py`.

### 2. GitHub Agent Extension (`src/agents/github_agent.py`)
- Request / Result Pydantic models:
  ```python
  class FetchFileContentRequest(BaseModel):
      repo: str
      file_path: str
      ref: str = "main"

  class FetchFileContentResult(BaseModel):
      repo: str
      file_path: str
      content: str
      html_url: str
  ```
- Method: `fetch_file_content(request: FetchFileContentRequest) -> FetchFileContentResult` (calls MCP tool `get_file_content`).

### 3. File Review Skill (`src/skills/file_review_skill.py`)
- Pydantic Return Model:
  ```python
  class FileReviewResult(BaseModel):
      summary: str
      issues: List[str]
      comment_text: str
  ```
- Function: `review_file_content(file_content: str, file_path: str) -> FileReviewResult`
- Uses Claude API to perform a full-file code review (analyzing code quality, bug risks, style, and maintainability).

### 4. Router Extension (`src/marshal/router.py`)
- Extend `WorkflowIntent`:
  ```python
  class WorkflowIntent(BaseModel):
      intent_type: str  # "github_review", "task_and_reminder", "calendar_schedule", "github_file_review"
      pr_number: Optional[int] = None
      repo: Optional[str] = None
      file_path: Optional[str] = None
      target_pr_number: Optional[int] = None
      notes_text: Optional[str] = None
  ```
- Fast-path regex & Claude LLM structured classifier: Recognize patterns like "check my X.py in Y repository", "review file X in repo Y".

### 5. Graph Pipeline & Comment-Posting Rule (`src/marshal/graph.py`)
- Node: `github_file_review_step`:
  1. Calls `fetch_file_content` via `github_agent.py`.
  2. Runs `review_file_content` via `file_review_skill.py`.
  3. Comment-posting rule:
     - If `intent.target_pr_number` is provided AND explicitly requested by user: Call `post_review_comment` to attach comment to that PR.
     - If no PR specified in user request: Do NOT guess PR. Show file review summary in response and append:
       `"\n💡 Would you like to post this review as a comment to a PR? Reply with 'post to PR #X'."`
  4. Scoped per `user_id`.

---
