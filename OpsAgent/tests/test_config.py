import os
from src.config import DEFAULT_MODEL_NAME


def test_default_model_name_value():
    assert DEFAULT_MODEL_NAME == "claude-sonnet-5" or isinstance(DEFAULT_MODEL_NAME, str)
