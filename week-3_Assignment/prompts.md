# Prompts for Week 3 Assignment

## 1. Retrieval-Augmented Generation (RAG) Prompt

Used in `rag_app.rag` to generate answers grounded in retrieved documents.

**Template:**
```text
Use the following pieces of retrieved context to answer the user's question.
If you don't know the answer, just say that you don't know.

Context: {context}

Question: {question}

Answer:
```

*Role*: System / Generator
*Purpose*: Ensures the LLM restricts its knowledge to the provided context and avoids hallucinations about topics not in the PDFs.

---

## 2. Structured Output Prompt

Used in `rag_app.structured` to force the LLM to output a JSON object matching our Pydantic schema.

**Template:**
```text
Extract the requested information from the text below.
{format_instructions}

Text: {text}
```

*Role*: System / Extractor
*Purpose*: Instructs the LLM to parse the provided text and strictly output JSON according to the LangChain Pydantic Output Parser's instructions.
