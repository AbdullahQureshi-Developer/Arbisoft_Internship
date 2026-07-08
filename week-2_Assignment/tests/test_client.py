import json

from clibot.client import OpenRouterClient


def test_parse_stream_chunk_valid():
    payload = json.dumps({"choices": [{"delta": {"content": "Hello"}}]})
    result = OpenRouterClient._parse_stream_chunk(payload)
    assert result == "Hello"


def test_parse_stream_chunk_empty_choices():
    payload = json.dumps({"choices": []})
    result = OpenRouterClient._parse_stream_chunk(payload)
    assert result == ""


def test_parse_stream_chunk_no_delta():
    payload = json.dumps({"choices": [{}]})
    result = OpenRouterClient._parse_stream_chunk(payload)
    assert result == ""


def test_parse_stream_chunk_invalid_json():
    payload = "{"
    result = OpenRouterClient._parse_stream_chunk(payload)
    assert result == ""
