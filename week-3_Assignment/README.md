# Week 3 Assignment - RAG Demo

This project demonstrates a Retrieval-Augmented Generation (RAG) system using ChromaDB, Embedding Comparisons, and a Structured-Output Pipeline with LangChain and Pydantic.

## Setup

Ensure you have `uv` installed, then run:

```bash
uv sync
```

To generate the mock PDFs in the `data/` folder:

```bash
uv run --with fpdf2 generate_pdfs.py
```

## Running the Demo

1. **RAG Pipeline**: `uv run rag-demo`
2. **Embedding Comparison**: `uv run rag-compare`
3. **Structured Output**: `uv run rag-structured`

## Hallucinations Caught

See **[hallucinations.md](hallucinations.md)** for a full report covering:

- **Type hallucination** — LLM returned `"High"` (string) for an integer field, caught by Pydantic `int_parsing`.
- **Missing field hallucination** — LLM invented `"entities"` instead of `"key_entities"`, caught by Pydantic `field_missing`.
- **Semantic miscalibration** — LLM gave `confidence_score: 5` for a trivially simple extraction (soft hallucination, caught via human review).

Each case includes the raw bad JSON, the exact `ValidationError` raised, and the automated pytest that reproduces it.
