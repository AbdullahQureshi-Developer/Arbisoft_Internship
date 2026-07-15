# Week 3 Assignment - RAG Pipeline & Structured Output

This project demonstrates a fully functional Retrieval-Augmented Generation (RAG) system using **ChromaDB**, **LangChain**, **Ollama**, and **Streamlit**. It features incremental ingestion, embedding model comparison, structured LLM extraction (with Pydantic), and observability logging.

## Setup

Ensure you have `uv` installed, then synchronize the environment:

```bash
uv sync
```

To generate the mock PDFs in the `data/` folder (if you haven't already):

```bash
uv run --with fpdf2 generate_pdfs.py
```

## Running the Project

This project defines several entry points via `pyproject.toml`. You can run them using `uv run`.

### 1. Interactive UI (Streamlit)
Launch the graphical interface to chat with your RAG system and submit feedback:
```bash
uv run rag-ui
```
*(Note: Be sure to ingest documents first so the vector store is populated.)*

### 2. Command-Line Demo (`rag_demo.py`)
**Ingest documents into ChromaDB:**
```bash
uv run rag-demo --ingest
```
*Features incremental sync logic: it intelligently adds new documents and deletes stale ones without re-indexing everything.*

**Query the system:**
```bash
uv run rag-demo --query "What is machine learning?"
```

### 3. Compare Embedding Models (`embedding_compare.py`)
Ingest data into two distinct models (`nomic-embed-text` and `all-minilm`) and compare their top retrieved chunks side-by-side.
```bash
uv run rag-compare --query "Your question here"
```

### 4. Structured Output Extraction (`structured_extraction.py`)
Run the pipeline that extracts structured JSON data (Title, Summary, Entities, Score) from the retrieved documents:
```bash
uv run rag-structured
```

## Observability & Feedback
- Queries, retrieved chunks, and generated answers are automatically logged to `logs/rag_queries.log`.
- Using the 👍 / 👎 buttons in the Streamlit UI writes user feedback directly into the logs to close the feedback loop.

## Testing
Run the automated test suite (which covers Pydantic validation edge-cases):
```bash
uv run pytest
```

## Hallucinations Caught

See **[hallucinations.md](hallucinations.md)** for a full report covering:
- **Type hallucination** — LLM returned `"High"` (string) for an integer field, caught by Pydantic `int_parsing`.
- **Missing field hallucination** — LLM invented `"entities"` instead of `"key_entities"`, caught by Pydantic `field_missing`.
- **Semantic miscalibration** — LLM gave `confidence_score: 5` for a trivially simple extraction.
