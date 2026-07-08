import os

from research_agent.tools import read_file


def test_read_file_txt():
    # Setup
    test_content = "Hello from test file"
    test_file = "test_sample.txt"
    with open(test_file, "w", encoding="utf-8") as f:
        f.write(test_content)

    try:
        # Act
        result = read_file.invoke({"filepath": test_file})

        # Assert
        assert result == test_content
    finally:
        # Cleanup
        if os.path.exists(test_file):
            os.remove(test_file)


def test_read_file_not_found():
    result = read_file.invoke({"filepath": "non_existent_file.txt"})
    assert "Error: File 'non_existent_file.txt' does not exist." in result
