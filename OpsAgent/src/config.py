import os
from dotenv import load_dotenv

load_dotenv()

# Centralized default Claude model configuration.
# Can be overridden via DEFAULT_MODEL_NAME or ANTHROPIC_MODEL environment variables.
DEFAULT_MODEL_NAME = os.getenv("DEFAULT_MODEL_NAME", os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"))
