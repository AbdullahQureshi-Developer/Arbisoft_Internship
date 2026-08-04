from unittest.mock import MagicMock
import pytest
import requests
from src.slack.bot import handle_slack_message, download_slack_file
from src.marshal.graph import document_processing_step, process_slack_message


def test_handle_slack_message():
    mock_event = {
        "text": "Hello bot",
        "user": "U123456",
        "ts": "1600000000.000100",
        "channel_type": "im",
    }
    
    replies = []
    
    def dummy_say(text: str, thread_ts: str = None):
        replies.append({"text": text, "thread_ts": thread_ts})
        
    res = handle_slack_message(event=mock_event, say=dummy_say)
    
    assert "OpsAgent Assistant" in res
    assert len(replies) == 1
    assert "OpsAgent Assistant" in replies[0]["text"]
    assert replies[0]["thread_ts"] == "1600000000.000100"


def test_download_slack_file_success(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.content = b"header,content\n1,2"
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    data = download_slack_file("https://slack.com/files/123", filename="test.docx")
    assert data == b"header,content\n1,2"


def test_download_slack_file_http_error(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.raise_for_status.side_effect = requests.HTTPError("403 Client Error: Forbidden")
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    with pytest.raises(requests.HTTPError):
        download_slack_file("https://slack.com/files/123", filename="test.docx")


def test_download_slack_file_empty_body(monkeypatch):
    mock_resp = MagicMock()
    mock_resp.content = b""
    mock_resp.raise_for_status.return_value = None
    monkeypatch.setattr(requests, "get", lambda *args, **kwargs: mock_resp)

    with pytest.raises(ValueError, match="empty \\(0 bytes\\)"):
        download_slack_file("https://slack.com/files/123", filename="test.docx")


def test_document_processing_step_failed_or_empty_download():
    state_empty = {
        "message_text": "Process spec",
        "channel_id": "C123",
        "user_id": "U123",
        "file_bytes": b"",
        "file_name": "sample.docx",
    }
    result_state = document_processing_step(state_empty)
    assert "❌ Error processing document `sample.docx`" in result_state["result_text"]
    assert "Processing Complete" not in result_state["result_text"]

