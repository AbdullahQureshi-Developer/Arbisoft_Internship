from research_agent.agent import SYSTEM_PROMPT, extract_text


def test_extract_text_plain_string():
    assert extract_text("hello world") == "hello world"


def test_extract_text_list_of_dicts():
    content = [{"text": "hello"}, {"text": "world"}]
    assert extract_text(content) == "hello\nworld"


def test_extract_text_empty_list_does_not_raise():
    # Previously: IndexError
    assert extract_text([]) == ""


def test_extract_text_list_of_plain_strings_does_not_raise():
    # Previously: AttributeError ('str' object has no attribute 'get')
    assert extract_text(["hello", "world"]) == "hello\nworld"


def test_extract_text_mixed_list():
    content = [{"text": "hello"}, "world"]
    assert extract_text(content) == "hello\nworld"


def test_extract_text_dict_missing_text_key_falls_back_to_str():
    content = [{"type": "tool_use", "input": {}}]
    result = extract_text(content)
    assert "tool_use" in result


def test_extract_text_other_type_falls_back_to_str():
    assert extract_text(42) == "42"


def test_system_prompt_has_no_missing_space():
    # Regression test for the adjacent-string-literal concatenation bug:
    # "...local files." + "Be concise..." used to glue together with no
    # space in between.
    assert "files.Be concise" not in SYSTEM_PROMPT
    assert "files. Be concise" in SYSTEM_PROMPT
