# Prompts for Week 3 Assignment

This file documents two distinct categories of prompts, kept separate per review feedback:

- **Part 1 — AI Coding Assistant Prompts**: prompts typed into an AI coding assistant (Claude/ChatGPT) to help design, write, and fix this codebase.
- **Part 2 — Runtime LLM Prompts**: prompts the application itself sends to `llama3` via Ollama at runtime.

---

## Part 1 — AI Coding Assistant Prompts

### A. Initial Build

#### prompt:1

Tell me about Retrieval-Augmented Generation (RAG): what problem it solves, how it
differs from pure LLM generation, and why grounding answers in retrieved documents
reduces hallucinations.

#### prompt:2

Explain ChromaDB as a vector store: how documents are chunked, embedded, and indexed,
and how similarity search retrieves the top-k most relevant chunks for a given query.

#### prompt:3

Build a RAG pipeline in Python using LangChain, ChromaDB, and Ollama that loads PDFs
from a data/ folder, splits them into chunks with RecursiveCharacterTextSplitter,
embeds them with nomic-embed-text, stores them in a persistent ChromaDB collection,
and answers queries using llama3 with a grounding prompt. Expose it as a CLI with
--ingest and --query flags.

#### prompt:4

Build a Structured Output pipeline in Python using LangChain's PydanticOutputParser
and a Pydantic BaseModel (ExtractedInfo) with fields title, summary,
key_entities, and confidence_score, so the LLM is forced to return valid JSON
matching the schema. Save the result to a JSON file.

#### prompt:5

Compare two Ollama embedding models (nomic-embed-text vs all-minilm) on the same
document corpus by indexing into separate ChromaDB collections and running
similarity_search_with_score on a shared query, then display the top-1 chunk
snippet and distance score for each model side-by-side in a Rich table.

#### prompt:6

Catch and document LLM hallucinations that break a Pydantic schema — a type
hallucination (string instead of int for confidence_score), a missing-field
hallucination, and out-of-range integer values on both ends (e.g. 999 and 0) — and
write pytest cases that reproduce each ValidationError.

---

### prompt:7 — Fix duplicate ingestion on repeated runs

Make chunk ingestion idempotent: generate a deterministic id for each chunk from its
source file and index, use add_documents with those ids so re-running --ingest just
updates existing chunks instead of duplicating them, and delete any chunks whose
source PDF no longer exists in data/.

### prompt:8 — Normalize LLM response content before parsing

Some providers return a list of content blocks instead of a plain string. Normalize
raw_response.content to a string before passing it to parser.parse() so this doesn't
crash with a TypeError.

### prompt:9 — Add a bounded retry loop around schema validation

Wrap the parse step in a retry loop that tries up to 2 more times if a
ValidationError is raised, and only re-raise once all retries are exhausted.

### prompt:10 — Harden the structured-extraction prompt

Add a short few-shot JSON example to the structured-extraction prompt, tell the model
to return only the JSON object with no markdown or explanations, and give
confidence_score a calibration rubric like 1 = pure guess, 5 = partial evidence,
10 = explicit in the text.

### prompt:11 — Harden the RAG grounding prompt

Update the RAG prompt to tell the model to answer using only the retrieved context,
treat that context as untrusted data rather than instructions, and cite which
chunk(s) it used in its answer.

### prompt:12 — Get the project passing mypy --strict

Add the missing return type and parameter annotations across the codebase so
mypy --strict src/ passes cleanly.

### prompt:13 — Extract shared ingestion logic and rename modules for clarity

Pull the duplicated PDF-loading and chunking code out of rag.py and compare.py into
a shared ingestion.py, and rename rag.py, compare.py, and structured.py to
rag_demo.py, embedding_compare.py, and structured_extraction.py — update
pyproject.toml entry points to match.

### prompt:14 — Build a Streamlit UI for the RAG pipeline

Build a small Streamlit app where I can type a query, see the retrieved chunks in an
expander, see the generated answer, and click thumbs up/down on it.

### prompt:15 — Add query/answer logging for observability

Log every query, its retrieved chunks, and the generated answer with a timestamp to
logs/rag_queries.log.

### prompt:16 — Generate a realistic multi-page PDF dataset

Write a script that pulls the full Wikipedia articles for Machine Learning, NLP, and
RAG and saves each as a multi-page PDF in data/, so the text splitter actually has
enough content to chunk.

### prompt:17 — Remove unused dependencies

Remove httpx and python-dotenv from pyproject.toml since nothing under src/ uses them.
