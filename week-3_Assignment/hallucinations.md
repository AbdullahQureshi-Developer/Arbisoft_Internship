# Hallucination Report: Where the LLM Failed and How We Caught It

This document tracks real and reproducible hallucinations observed during the
development and testing of the structured-output pipeline (`rag_app.structured`).

The guardrail is a **Pydantic v2 schema** (`ExtractedInfo`) enforced by
LangChain's `PydanticOutputParser`. Every JSON the LLM emits is validated before
being saved to disk. Any deviation from the schema raises a `ValidationError` —
surfacing the hallucination instead of silently propagating bad data.

---

## Schema Under Test

```python
class ExtractedInfo(BaseModel):
    title: str
    summary: str
    key_entities: list[str]
    confidence_score: int = Field(ge=1, le=10)   # enforced, not just documented
```

> **Update:** `confidence_score` originally had no `ge`/`le` bounds — only a
> description saying "1 to 10." A correctly-typed but out-of-range value
> (e.g. `999`) passed validation silently. This has been fixed (see
> Hallucination 3 below) and is now a hard-enforced constraint, not just a
> prompt instruction.

---

## Hallucination 1 — Wrong Type for `confidence_score`

### What happened
The LLM was asked to extract information from a short NLP text.
When the schema instructions were less explicit, `llama3` returned:

```json
{
  "title": "Natural Language Processing",
  "summary": "A branch of AI that helps computers understand human language.",
  "key_entities": ["NLP", "AI", "computers"],
  "confidence_score": "High"
}
```

`"High"` is a **string**, but the schema demands an **integer**.

### How it was caught
`PydanticOutputParser` feeds the JSON to Pydantic's validator, which raises:

```
ValidationError: 1 validation error for ExtractedInfo
confidence_score
  Input should be a valid integer, unable to parse string as an integer
  [type=int_parsing, input_value='High', input_url=...]
```

### Automated test
```python
# tests/test_validation.py :: test_wrong_type_hallucination
def test_wrong_type_hallucination():
    data = {
        "title": "Wrong Type",
        "summary": "Score is a string.",
        "key_entities": ["Test"],
        "confidence_score": "High",   # ← hallucinated string
    }
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "confidence_score" in str(exc_info.value)
    assert "Input should be a valid integer" in str(exc_info.value)
```

### Fix applied
The system prompt (see `prompts.md`) was tightened to explicitly state:
> `confidence_score` must be a JSON integer between 1 and 10, e.g. `7`.

---

## Hallucination 2 — Missing Required Field (`key_entities`)

### What happened
On a more complex input text, the model omitted the `key_entities` field entirely
and instead invented a field called `"entities"` (wrong name):

```json
{
  "title": "RAG Overview",
  "summary": "RAG combines retrieval with generation to reduce hallucinations.",
  "entities": ["ChromaDB", "LLM", "retrieval"],
  "confidence_score": 8
}
```

The required field `key_entities` is **absent**; `entities` is an unknown extra field.

### How it was caught
Pydantic raised two errors simultaneously:

```
ValidationError: 1 validation error for ExtractedInfo
key_entities
  Field required [type=missing, ...]
```

(Extra fields are silently ignored by default, but the missing required field is
fatal.)

### Automated test
```python
# tests/test_validation.py :: test_missing_field_hallucination
def test_missing_field_hallucination():
    data = {
        "title": "Incomplete Data",
        "summary": "Missing entities and score.",
    }
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "key_entities" in str(exc_info.value)
    assert "confidence_score" in str(exc_info.value)
```

### Fix applied
The format instructions injected by `PydanticOutputParser.get_format_instructions()`
already lists every required field by name. The issue was traced to the model
applying its own naming conventions. No prompt change was needed — the validator
already catches and blocks this reliably.

---

## Hallucination 3 — Out-of-Range `confidence_score`

### What happened
The original schema only *described* `confidence_score` as "1 to 10" in the
field docstring — it didn't enforce it. A correctly-typed but semantically
invalid score (e.g. the model returning `999` or `0` instead of a value in
range) passed validation silently and would have been written to
`results.json` as if it were valid.

This was caught during review, not by a live LLM run — it's a gap in the
*schema*, not a one-off bad generation, which is arguably worse: a type error
happens once per hallucination, but an unbounded field lets bad values through
every time, forever.

### How it was caught
`ExtractedInfo.confidence_score` now uses `Field(ge=1, le=10, ...)`. Out-of-range
integers raise:

```
ValidationError: 1 validation error for ExtractedInfo
confidence_score
  Input should be less than or equal to 10
  [type=less_than_equal, input_value=999, input_url=...]
```

### Automated test
```python
# test_validation.py :: test_confidence_score_out_of_range_hallucination
def test_confidence_score_out_of_range_hallucination():
    data = {
        "title": "Out of Range",
        "summary": "Score is a valid int but outside the allowed 1-10 range.",
        "key_entities": ["Test"],
        "confidence_score": 999,
    }
    with pytest.raises(ValidationError) as exc_info:
        ExtractedInfo(**data)

    assert "confidence_score" in str(exc_info.value)
    assert "less than or equal to 10" in str(exc_info.value)
```

A companion test, `test_confidence_score_below_range_hallucination`, checks
the lower bound (`confidence_score=0`) the same way.

### Fix applied
Added `ge=1, le=10` to the `confidence_score` field. This is now a hard
constraint enforced on every validation, not just a hope encoded in a prompt.

---

## Real LLM Output Observed (Pass Case)

When the pipeline ran successfully against the NLP text, `results.json` was saved
with:

```json
{
    "title": "Natural Language Processing",
    "summary": "A branch of AI that helps computers understand human language.",
    "key_entities": ["computers", "language", "AI"],
    "confidence_score": 5
}
```

**Observation**: The `confidence_score` of `5` is on the low side for a clean
extraction from a short, unambiguous sentence — a soft signal that the model
may be expressing uncertainty about the *task* rather than the *content*.
This is a calibration concern rather than a schema violation (5 is validly in
range), so it isn't something Pydantic can catch; it's noted here as a
limitation of scoring without a calibration rubric, not as a caught
hallucination.

---

## Summary Table

| # | Field             | Hallucination Type       | Caught By                    | Test Function                                 |
|---|-------------------|---------------------------|-------------------------------|------------------------------------------------|
| 1 | `confidence_score`| Wrong type (`str`)        | Pydantic `int_parsing`        | `test_wrong_type_hallucination`               |
| 2 | `key_entities`    | Missing required field    | Pydantic `field_missing`      | `test_missing_field_hallucination`            |
| 3 | `confidence_score`| Out-of-range value (`999`)| Pydantic `less_than_equal`    | `test_confidence_score_out_of_range_hallucination` |
| 4 | `confidence_score`| Below-range value (`0`)   | Pydantic `greater_than_equal` | `test_confidence_score_below_range_hallucination`  |

*Calibration concern (low-but-in-range score) remains a noted limitation, not
a hard-caught hallucination — see "Real LLM Output Observed" above.*

---

## How to Reproduce

Run the validation test suite — all tests will **pass** (meaning Pydantic correctly
*caught* the hallucinations):

```bash
uv run pytest test_validation.py -v
```

To observe the live pipeline run successfully:

```bash
uv run rag-structured
```

To trigger a real failure, you can temporarily patch `structured.py` to return a
bad JSON string and observe the `ValidationError` printed in the terminal.
