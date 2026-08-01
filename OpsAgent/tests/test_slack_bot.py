from src.slack.bot import handle_slack_message


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
