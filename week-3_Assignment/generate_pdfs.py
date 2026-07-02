import os

from fpdf import FPDF


def create_pdf(filename: str, title: str, content: str):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", size=12)
    pdf.cell(200, 10, txt=title, new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(10)
    pdf.multi_cell(0, 10, txt=content)
    pdf.output(filename)


def main():
    os.makedirs("data", exist_ok=True)

    # Document 1: Machine Learning Basics
    doc1_content = """Machine learning is a subfield of artificial intelligence (AI).
It focuses on the development of algorithms that allow computers to learn from
and make predictions based on data.
The three main types of machine learning are supervised learning, unsupervised
learning, and reinforcement learning.
Supervised learning uses labeled data to train models, such as predicting
house prices based on historical data.
"""
    create_pdf("data/ml_basics.pdf", "Machine Learning Basics", doc1_content)

    # Document 2: Natural Language Processing
    doc2_content = """Natural Language Processing (NLP) is a branch of AI that helps
computers understand, interpret and manipulate human language.
NLP draws from many disciplines, including computer science and computational
linguistics.
Recent advances in NLP use Large Language Models (LLMs) based on the
Transformer architecture.
Transformers use a self-attention mechanism to weigh the importance of
different words in a sequence.
"""
    create_pdf(
        "data/nlp_overview.pdf", "Natural Language Processing Overview", doc2_content
    )

    # Document 3: Retrieval-Augmented Generation
    doc3_content = """Retrieval-Augmented Generation (RAG) is a technique that combines
information retrieval with a text generator model.
RAG systems first retrieve relevant documents from a knowledge base (often
using vector databases like ChromaDB or pgvector) based on a user's query.
The retrieved context is then passed to a Large Language Model (LLM)
alongside the original query.
This allows the LLM to generate answers that are more accurate, up-to-date,
and grounded in specific facts, reducing hallucinations.
"""
    create_pdf(
        "data/rag_technique.pdf", "Retrieval-Augmented Generation (RAG)", doc3_content
    )

    print("Created mock PDFs in data/ directory.")


if __name__ == "__main__":
    main()
