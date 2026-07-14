import os
from pathlib import Path

import serpapi
from langchain_core.tools import tool
from pypdf import PdfReader

# Only files inside this directory may be read by the read_file tool.
# Resolved once at import time so it reflects the real project layout
# regardless of the process's current working directory.
ALLOWED_DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def _resolve_safe_path(filepath: str) -> Path:
    """
    Resolve `filepath` against ALLOWED_DATA_DIR and ensure the result does
    not escape it via '..' segments, an absolute path, or a symlink.

    Accepts paths given either as "sample.txt" or "data/sample.txt" (the
    latter matches how the agent's system prompt refers to files).

    Raises ValueError if the resolved path falls outside ALLOWED_DATA_DIR.
    """
    parts = Path(filepath).parts
    if parts and parts[0] == ALLOWED_DATA_DIR.name:
        parts = parts[1:]

    candidate = (ALLOWED_DATA_DIR / Path(*parts)) if parts else ALLOWED_DATA_DIR
    candidate = candidate.resolve()

    if not candidate.is_relative_to(ALLOWED_DATA_DIR):
        raise ValueError(
            f"Access to '{filepath}' is not allowed. Only files inside the "
            f"'{ALLOWED_DATA_DIR.name}/' directory can be read."
        )
    return candidate


@tool
def web_search(query: str) -> str:
    """
    Search the web for information using SerpAPI.
    Use this to look up current events, facts, or other information on the internet.
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        return "Error: SERPAPI_API_KEY environment variable not set."

    try:
        client = serpapi.Client(api_key=api_key)
        results = client.search(
            {
                "engine": "google",
                "q": query,
                "google_domain": "google.com",
                "hl": "en",
                "gl": "us",
            }
        )

        # Extract organic results or answer box
        output = []
        if "answer_box" in results and "snippet" in results["answer_box"]:
            output.append(f"Answer Box: {results['answer_box']['snippet']}")
        elif "answer_box" in results and "answer" in results["answer_box"]:
            output.append(f"Answer Box: {results['answer_box']['answer']}")

        if "organic_results" in results:
            for item in results["organic_results"][:3]:  # Take top 3
                output.append(
                    f"Title: {item.get('title')}\nSnippet: {item.get('snippet')}"
                )

        if not output:
            return "No good results found."

        return "\n\n".join(output)
    except Exception as e:
        return f"Error performing web search: {e}"


@tool
def read_file(filepath: str) -> str:
    """
    Read the contents of a local file (.txt or .pdf).
    Only files inside the project's 'data/' directory can be read.
    Provide a path relative to that directory, e.g. 'sample.txt' or
    'data/sample.txt'.
    """
    try:
        safe_path = _resolve_safe_path(filepath)
    except ValueError as e:
        return f"Error: {e}"

    if not safe_path.exists():
        return f"Error: File '{filepath}' does not exist."

    try:
        if safe_path.suffix.lower() == ".pdf":
            reader = PdfReader(str(safe_path))
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        else:
            with open(safe_path, encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"
