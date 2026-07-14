import pytest

from research_agent.tools import ALLOWED_DATA_DIR, read_file


@pytest.fixture
def sample_file():
    ALLOWED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    test_content = "Hello from test file"
    test_path = ALLOWED_DATA_DIR / "test_sample.txt"
    test_path.write_text(test_content, encoding="utf-8")
    yield test_path.name, test_content
    if test_path.exists():
        test_path.unlink()


def test_read_file_txt(sample_file):
    filename, test_content = sample_file
    result = read_file.invoke({"filepath": filename})
    assert result == test_content


def test_read_file_with_data_prefix(sample_file):
    # Agent's system prompt refers to files as "data/<name>", so that
    # form must resolve to the same location as the bare filename.
    filename, test_content = sample_file
    result = read_file.invoke({"filepath": f"data/{filename}"})
    assert result == test_content


def test_read_file_not_found():
    result = read_file.invoke({"filepath": "non_existent_file.txt"})
    assert "does not exist" in result


def test_read_file_blocks_parent_traversal():
    result = read_file.invoke({"filepath": "../.env"})
    assert "not allowed" in result.lower()


def test_read_file_blocks_absolute_path():
    result = read_file.invoke({"filepath": "/etc/passwd"})
    assert "not allowed" in result.lower()
