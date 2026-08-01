import logging
from mcp.server.fastmcp import FastMCP
from src.mcp_server.tools.github_tools import get_pr as _get_pr, post_pr_comment as _post_pr_comment

logger = logging.getLogger("mcp_server")

# Initialize FastMCP Server
mcp = FastMCP("OpsAgent-GitHub-MCP-Server")


@mcp.tool()
def get_pr(repo: str, pr_number: int) -> dict:
    """Fetch PR details and diff from GitHub REST API."""
    return _get_pr(repo=repo, pr_number=pr_number)


@mcp.tool()
def post_pr_comment(repo: str, pr_number: int, body: str) -> dict:
    """Post a comment on a GitHub PR."""
    return _post_pr_comment(repo=repo, pr_number=pr_number, body=body)


if __name__ == "__main__":
    mcp.run()
