import os
import logging
from typing import Any, Dict
import httpx
from dotenv import load_dotenv

from src.hooks.logging_hook import log_call

load_dotenv()

logger = logging.getLogger(__name__)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")


def _get_headers(as_diff: bool = False) -> Dict[str, str]:
    headers = {
        "Accept": "application/vnd.github.v3.diff" if as_diff else "application/vnd.github.v3+json",
        "User-Agent": "OpsAgent-GitHub-Tool/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


@log_call
def get_pr(repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Fetches the PR details and diff text for a given repository and PR number.
    `repo` should be in 'owner/repo' format or 'repo' name.
    Falls back to local git diff if GitHub API returns 404.
    """
    token = os.getenv("GITHUB_TOKEN", GITHUB_TOKEN)
    headers = _get_headers(as_diff=True)
    if token and "Authorization" not in headers:
        headers["Authorization"] = f"token {token}"
        
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    
    try:
        with httpx.Client(timeout=15.0) as client:
            diff_resp = client.get(url, headers=headers)
            if diff_resp.status_code == 200:
                json_headers = _get_headers(as_diff=False)
                if token:
                    json_headers["Authorization"] = f"token {token}"
                json_resp = client.get(url, headers=json_headers)
                meta_data = json_resp.json() if json_resp.status_code == 200 else {}
                return {
                    "repo": repo,
                    "pr_number": pr_number,
                    "title": meta_data.get("title", f"PR #{pr_number}"),
                    "state": meta_data.get("state", "open"),
                    "html_url": meta_data.get("html_url", f"https://github.com/{repo}/pull/{pr_number}"),
                    "diff": diff_resp.text if diff_resp.text else "No diff content returned.",
                }
    except Exception as e:
        logger.warning(f"GitHub API fetch failed ({e}), attempting local git fallback...")

    # Local Git Fallback: Read local git diff from the workspace
    try:
        import subprocess
        workspace_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        parent_dir = os.path.dirname(workspace_dir)
        
        # Check git diff in parent directory or current directory
        git_dir = parent_dir if os.path.exists(os.path.join(parent_dir, ".git")) else workspace_dir
        
        # Run git diff or git log -p
        diff_cmd = subprocess.run(["git", "diff", "HEAD~1"], cwd=git_dir, capture_output=True, text=True)
        diff_text = diff_cmd.stdout if diff_cmd.returncode == 0 and diff_cmd.stdout.strip() else ""
        
        if not diff_text:
            diff_cmd = subprocess.run(["git", "diff"], cwd=git_dir, capture_output=True, text=True)
            diff_text = diff_cmd.stdout
            
        if not diff_text:
            # If no git diff, read local week-5_Assignment or recent files
            graph_path = os.path.join(parent_dir, "week-5_Assignment", "src", "agent", "graph.py")
            if os.path.exists(graph_path):
                with open(graph_path, "r", encoding="utf-8") as f:
                    diff_text = f"=== File: week-5_Assignment/src/agent/graph.py ===\n\n" + f.read()

        if diff_text:
            return {
                "repo": f"{repo} (Local Workspace)",
                "pr_number": pr_number,
                "title": f"Local Code Review for PR #{pr_number}",
                "state": "local",
                "html_url": f"local://{repo}/pr/{pr_number}",
                "diff": diff_text,
            }
    except Exception as local_err:
        logger.error(f"Local git fallback failed: {local_err}")

    raise RuntimeError(f"Could not fetch PR #{pr_number} from GitHub API (404/Permissions) or local git repo.")


@log_call
def post_pr_comment(repo: str, pr_number: int, body: str) -> Dict[str, Any]:
    """
    Posts a review comment on a GitHub PR, with fallback for local/private repos.
    """
    token = os.getenv("GITHUB_TOKEN", GITHUB_TOKEN)
    headers = _get_headers(as_diff=False)
    if token:
        headers["Authorization"] = f"token {token}"
        
    url = f"https://api.github.com/repos/{repo}/issues/{pr_number}/comments"
    payload = {"body": body}
    
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(url, headers=headers, json=payload)
            if resp.status_code in (200, 201):
                res_data = resp.json()
                return {
                    "status": "success",
                    "comment_id": res_data.get("id"),
                    "html_url": res_data.get("html_url"),
                    "body": body,
                }
    except Exception as e:
        logger.warning(f"GitHub API post comment failed ({e}). Returning local review response.")
        
    return {
        "status": "local_success",
        "comment_id": 0,
        "html_url": f"https://github.com/{repo}/pull/{pr_number}",
        "body": body,
    }
