import argparse
import json
from typing import Any

from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console

console = Console()


class ExtractedInfo(BaseModel):
    title: str = Field(description="The title of the document or topic being discussed")
    summary: str = Field(
        description="A brief summary of the main points, no more than 3 sentences"
    )
    key_entities: list[str] = Field(
        description="A list of important entities, concepts, or terms mentioned"
    )
    confidence_score: int = Field(
        ge=1,
        le=10,
        description="An integer from 1 to 10 indicating confidence in the extraction. "
        "1 = pure guess/hallucination, 5 = somewhat sure based on partial info, "
        "10 = absolute certainty derived explicitly from the text.",
    )


def extract_structured_data(text: str, output_file: str = "results.json") -> None:
    llm = ChatOllama(model="llama3", temperature=0)
    parser = PydanticOutputParser(pydantic_object=ExtractedInfo)
    prompt = PromptTemplate(
        template=(
            "Extract the requested information from the text below.\n"
            "Return ONLY a valid JSON object. Do not include markdown "
            "formatting or explanations.\n\n"
            "Here is an example of the desired output format:\n"
            "{{\n"
            '  "title": "Quantum Computing Basics",\n'
            '  "summary": "Quantum computers use qubits to perform calculations '
            'much faster than classical computers.",\n'
            '  "key_entities": ["Qubit", "Superposition", "Entanglement"],\n'
            '  "confidence_score": 9\n'
            "}}\n\n"
            "{format_instructions}\n\nText: {text}\n"
        ),
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm
    console.print(
        "[cyan]Sending text to LLM for extraction...[/cyan]\n"
        f"Text Snippet: {text[:100]}..."
    )

    max_retries = 2
    for attempt in range(max_retries + 1):
        raw_response = chain.invoke({"text": text})

        # Normalize response content (some providers return list of dicts)
        content: Any = raw_response.content
        if isinstance(content, list):
            # Extract first text block if it's a list
            content = next(
                (
                    b.get("text", "")
                    for b in content
                    if isinstance(b, dict) and "text" in b
                ),
                str(content),
            )
        elif not isinstance(content, str):
            content = str(content)

        try:
            parsed_result = parser.parse(content)
            console.print(
                "[green]Successfully parsed and validated structured output![/green]"
            )
            console.print(parsed_result.model_dump())
            # Save to JSON
            with open(output_file, "w") as f:
                json.dump(parsed_result.model_dump(), f, indent=4)
            console.print(f"[green]Saved results to {output_file}[/green]")
            return

        except ValidationError as e:
            if attempt < max_retries:
                console.print(
                    f"[yellow]Validation Error on attempt {attempt + 1}. "
                    "Retrying...[/yellow]"
                )
                continue
            console.print(
                "[bold red]Validation Error (LLM Hallucination or Schema Break) "
                "after retries:[/bold red]"
            )
            console.print(e)
            raise
        except Exception as e:
            console.print(f"[bold red]Failed to parse output:[/bold red]\n{e}")
            console.print(f"Raw Output was:\n{content}")
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Structured Output Pipeline")
    parser.add_argument(
        "--text",
        type=str,
        default=(
            "Natural Language Processing (NLP) is a branch of AI that helps "
            "computers understand human language. The main entities involved "
            "are computers, language, and AI."
        ),
        help="Text to process",
    )
    args = parser.parse_args()
    extract_structured_data(args.text)


if __name__ == "__main__":
    main()
