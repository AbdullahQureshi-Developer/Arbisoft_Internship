import pytest
from unittest.mock import MagicMock, patch
from src.mcp_server.tools.github_tools import get_pr


def test_get_pr_success():
    mock_diff_resp = MagicMock()
    mock_diff_resp.status_code = 200
    mock_diff_resp.text = "diff --git a/file.py b/file.py\n+new line"

    mock_json_resp = MagicMock()
    mock_json_resp.status_code = 200
    mock_json_resp.json.return_value = {
        "title": "Fix bug",
        "state": "open",
        "html_url": "https://github.com/owner/repo/pull/1",
    }

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.side_effect = [mock_diff_resp, mock_json_resp]
        mock_client_cls.return_value = mock_client

        res = get_pr("owner/repo", 1)

        assert res["repo"] == "owner/repo"
        assert res["pr_number"] == 1
        assert res["title"] == "Fix bug"
        assert "new line" in res["diff"]


def test_get_pr_api_failure_raises_runtime_error():
    mock_resp = MagicMock()
    mock_resp.status_code = 404
    mock_resp.text = "Not Found"

    with patch("httpx.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.__enter__.return_value = mock_client
        mock_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_client

        with pytest.raises(RuntimeError) as exc_info:
            get_pr("owner/repo", 999)

        assert "404" in str(exc_info.value)
