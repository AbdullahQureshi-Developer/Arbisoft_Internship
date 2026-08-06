from src.config import DEFAULT_MODEL_NAME


def test_default_model_name_value():
    assert isinstance(DEFAULT_MODEL_NAME, str)
    assert len(DEFAULT_MODEL_NAME) > 0


def test_model_name_environment_override(monkeypatch):
    monkeypatch.setenv("DEFAULT_MODEL_NAME", "claude-3-5-sonnet-20241022")
    import importlib
    import src.config

    importlib.reload(src.config)
    assert src.config.DEFAULT_MODEL_NAME == "claude-3-5-sonnet-20241022"
