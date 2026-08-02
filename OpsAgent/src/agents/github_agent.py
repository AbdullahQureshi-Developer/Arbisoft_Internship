from typing import Optional
from pydantic import BaseModel, Field
from src.hooks.logging_hook import log_call
from src.mcp_server.tools.github_tools import get_pr, post_pr_comment, get_file_content


class FetchPRRequest(BaseModel):
    repo: str = Field(..., description="Repository in 'owner/repo' format")
    pr_number: int = Field(..., description="Pull request number")


class FetchPRResult(BaseModel):
    repo: str
    pr_number: int
    title: str
    state: str
    html_url: str
    diff: str


class FetchFileContentRequest(BaseModel):
    repo: str = Field(..., description="Repository name or 'owner/repo'")
    file_path: str = Field(..., description="File path relative to repo root")
    ref: str = Field(default="main", description="Git ref/branch/commit")


class FetchFileContentResult(BaseModel):
    repo: str
    file_path: str
    content: str
    html_url: str


class PostCommentRequest(BaseModel):
    repo: str
    pr_number: int
    body: str


class PostCommentResult(BaseModel):
    status: str
    comment_id: Optional[int] = None
    html_url: Optional[str] = None
    body: str


@log_call
def fetch_pr_diff(request: FetchPRRequest) -> FetchPRResult:
    """Agent method to fetch PR diff and details via MCP tools."""
    raw_res = get_pr(repo=request.repo, pr_number=request.pr_number)
    return FetchPRResult(**raw_res)


@log_call
def fetch_file_content(request: FetchFileContentRequest) -> FetchFileContentResult:
    """Agent method to fetch raw file content via MCP tool."""
    raw_res = get_file_content(repo=request.repo, file_path=request.file_path, ref=request.ref)
    return FetchFileContentResult(**raw_res)


@log_call
def post_review_comment(request: PostCommentRequest) -> PostCommentResult:
    """Agent method to post a review comment via MCP tools."""
    raw_res = post_pr_comment(repo=request.repo, pr_number=request.pr_number, body=request.body)
    return PostCommentResult(**raw_res)
