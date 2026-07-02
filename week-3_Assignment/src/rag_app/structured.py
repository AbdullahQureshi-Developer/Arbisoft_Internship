import argparse
import json

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
        description="An integer from 1 to 10 indicating confidence in the extraction",
    )


def extract_structured_data(text: str, output_file: str = "results.json"):
    llm = ChatOllama(model="llama3", temperature=0)
    parser = PydanticOutputParser(pydantic_object=ExtractedInfo)
    prompt = PromptTemplate(
        template=(
            "Extract the requested information from the text below.\n"
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
    raw_response = chain.invoke({"text": text})
    try:
        # LLM might return reasoning along with JSON.
        # The parser tries to extract the JSON block.
        parsed_result = parser.parse(raw_response.content)
        console.print(
            "[green]Successfully parsed and validated structured output![/green]"
        )
        console.print(parsed_result.model_dump())
        # Save to JSON
        with open(output_file, "w") as f:
            json.dump(parsed_result.model_dump(), f, indent=4)
        console.print(f"[green]Saved results to {output_file}[/green]")
    except ValidationError as e:
        console.print(
            "[bold red]Validation Error (LLM Hallucination or Schema Break):[/bold red]"
        )
        console.print(e)
        raise
    except Exception as e:
        console.print(f"[bold red]Failed to parse output:[/bold red]\n{e}")
        console.print(f"Raw Output was:\n{raw_response.content}")
        raise


def main():
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
