import logging
from mcp.server.fastmcp import FastMCP
from src.mcp_server.tools.github_tools import get_pr as _get_pr, post_pr_comment as _post_pr_comment, get_file_content as _get_file_content
from src.mcp_server.tools.calendar_tools import create_event as _create_event

logger = logging.getLogger("mcp_server")

# Initialize FastMCP Server
mcp = FastMCP("OpsAgent-MCP-Server")


@mcp.tool()
def get_pr(repo: str, pr_number: int) -> dict:
    """Fetch PR details and diff from GitHub REST API."""
    return _get_pr(repo=repo, pr_number=pr_number)


@mcp.tool()
def get_file_content(repo: str, file_path: str, ref: str = "main") -> dict:
    """Fetch file content directly from GitHub repository by path."""
    return _get_file_content(repo=repo, file_path=file_path, ref=ref)


@mcp.tool()
def post_pr_comment(repo: str, pr_number: int, body: str) -> dict:
    """Post a comment on a GitHub PR."""
    return _post_pr_comment(repo=repo, pr_number=pr_number, body=body)


@mcp.tool()
def create_event(title: str, start_time: str, end_time: str, attendees: list[str] = None) -> dict:
    """Creates a Google Calendar event for authenticated primary user."""
    return _create_event(title=title, start_time=start_time, end_time=end_time, attendees=attendees or [])


if __name__ == "__main__":
    mcp.run()
