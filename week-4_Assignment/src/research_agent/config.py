"""Shared configuration values for the research agent.

Centralizing these means a value like the model name only needs to change
in one place, instead of the various entry points (agent.py, app.py,
demo.py) drifting out of sync with each other.
"""

import os

# gemini-2.5-flash is being retired ahead of its Oct 16, 2026 shutdown date
# (Google has already cut off access for new API users/projects, returning
# a 404 NOT_FOUND). gemini-3.5-flash is Google's designated replacement --
# update this if Google announces a further migration.
# Can be overridden with an env var (e.g. in .env) without touching code.
DEFAULT_MODEL_NAME = os.getenv("RESEARCH_AGENT_MODEL", "gemini-3.5-flash")
