import json
import os
import ssl
import urllib.parse
import urllib.request

from fpdf import FPDF

ssl._create_default_https_context = ssl._create_unverified_context


def create_pdf(filename: str, title: str, content: str) -> None:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt=title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    # Ensure text is encoded properly for FPDF to prevent character errors
    content = content.encode("latin-1", "replace").decode("latin-1")
    pdf.multi_cell(0, 10, txt=content)
    pdf.output(filename)


def fetch_wikipedia_article(title: str) -> str:
    # URL encode the title just in case
    encoded_title = urllib.parse.quote(title)
    url = f"https://en.wikipedia.org/w/api.php?format=json&action=query&prop=extracts&explaintext=1&titles={encoded_title}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req) as response:
        data = json.loads(response.read().decode())
    pages = data["query"]["pages"]
    for page_id in pages:
        return str(pages[page_id].get("extract", ""))
    return ""


def main() -> None:
    os.makedirs("data", exist_ok=True)

    print("Fetching 'Machine Learning' from Wikipedia...")
    ml_content = fetch_wikipedia_article("Machine_learning")
    if ml_content:
        # Take a sizable chunk (e.g., 5000 chars) to ensure multi-page and chunking
        create_pdf("data/ml_basics.pdf", "Machine Learning Basics", ml_content[:5000])

    print("Fetching 'Natural Language Processing' from Wikipedia...")
    nlp_content = fetch_wikipedia_article("Natural_language_processing")
    if nlp_content:
        create_pdf(
            "data/nlp_overview.pdf", "Natural Language Processing", nlp_content[:5000]
        )

    print("Fetching 'Retrieval-augmented generation' from Wikipedia...")
    rag_content = fetch_wikipedia_article("Retrieval-augmented_generation")
    if rag_content:
        create_pdf(
            "data/rag_technique.pdf",
            "Retrieval-Augmented Generation (RAG)",
            rag_content[:5000],
        )

    print("Created multi-page mock PDFs in data/ directory.")


if __name__ == "__main__":
    main()
