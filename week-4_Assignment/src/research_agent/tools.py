import os

import serpapi
from langchain_core.tools import tool
from pypdf import PdfReader


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
    Provide the relative or absolute path to the file.
    """
    if not os.path.exists(filepath):
        return f"Error: File '{filepath}' does not exist."

    try:
        if filepath.lower().endswith(".pdf"):
            reader = PdfReader(filepath)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            return text.strip()
        else:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
    except Exception as e:
        return f"Error reading file '{filepath}': {e}"
