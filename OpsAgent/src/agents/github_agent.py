from typing import Optional
from pydantic import BaseModel, Field
from src.hooks.logging_hook import log_call
from src.mcp_server.tools.github_tools import get_pr, post_pr_comment


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
    return FetchPRResult(
        repo=raw_res.get("repo", request.repo),
        pr_number=raw_res.get("pr_number", request.pr_number),
        title=raw_res.get("title", ""),
        state=raw_res.get("state", "open"),
        html_url=raw_res.get("html_url", ""),
        diff=raw_res.get("diff", ""),
    )


@log_call
def post_review_comment(request: PostCommentRequest) -> PostCommentResult:
    """Agent method to post a review comment to a GitHub PR via MCP tools."""
    raw_res = post_pr_comment(
        repo=request.repo, pr_number=request.pr_number, body=request.body
    )
    return PostCommentResult(
        status=raw_res.get("status", "success"),
        comment_id=raw_res.get("comment_id"),
        html_url=raw_res.get("html_url"),
        body=raw_res.get("body", request.body),
    )
