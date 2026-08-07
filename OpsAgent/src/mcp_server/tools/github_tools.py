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
        "Accept": "application/vnd.github.v3.diff"
        if as_diff
        else "application/vnd.github.v3+json",
        "User-Agent": "OpsAgent-GitHub-Tool/1.0",
    }
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers


@log_call
def get_pr(repo: str, pr_number: int) -> Dict[str, Any]:
    """
    Fetches the PR details and diff text for a given repository and PR number.
    `repo` should be in 'owner/repo' format.
    Raises RuntimeError if the GitHub API call fails.
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
                    "html_url": meta_data.get(
                        "html_url", f"https://github.com/{repo}/pull/{pr_number}"
                    ),
                    "diff": diff_resp.text
                    if diff_resp.text
                    else "No diff content returned.",
                }
            else:
                raise RuntimeError(
                    f"GitHub API error fetching PR #{pr_number} from '{repo}' "
                    f"(HTTP {diff_resp.status_code}): {diff_resp.text}"
                )
    except Exception as e:
        logger.error(f"GitHub API fetch failed for {repo} PR #{pr_number}: {e}")
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to fetch PR #{pr_number} from GitHub API ({repo}): {e}"
        ) from e


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
            else:
                raise RuntimeError(
                    f"GitHub API Error {resp.status_code} posting comment on PR #{pr_number}: {resp.text}"
                )
    except Exception as e:
        logger.error(f"GitHub API post comment failed for {repo} PR #{pr_number}: {e}")
        if isinstance(e, RuntimeError):
            raise
        raise RuntimeError(
            f"Failed to post PR #{pr_number} comment via GitHub API: {e}"
        ) from e
