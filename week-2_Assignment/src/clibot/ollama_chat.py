import time
from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate
from langchain_ollama import OllamaLLM

MODELS = [
    "phi3",
    "llama3",
    "mistral",
]

QUESTION = "Explain embeddings and RAG with a simple example."

TEMPLATE = """
You are a helpful AI assistant.

Answer the following question clearly and simply.

Question:
{question}

Answer:
"""

RESULTS_DIR = Path("results")
RESULTS_DIR.mkdir(exist_ok=True)

prompt = ChatPromptTemplate.from_template(TEMPLATE)


def ask_model(model_name: str, question: str) -> tuple[str, float]:
    """Run one model and return its response and execution time."""

    model = OllamaLLM(model=model_name)
    chain = prompt | model

    start = time.perf_counter()

    response = chain.invoke(
        {
            "question": question,
        }
    )

    elapsed = time.perf_counter() - start

    return response, elapsed


def save_response(
    model_name: str,
    question: str,
    response: str,
    elapsed: float,
) -> None:
    """Save one model's response into a text file."""

    file_path = RESULTS_DIR / f"{model_name}.txt"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write(f"Model: {model_name}\n")
        file.write(f"Question: {question}\n")
        file.write(f"Time: {elapsed:.2f} seconds\n")
        file.write("-" * 80 + "\n\n")
        file.write(response)


def save_summary(summary: list[tuple[str, float]]) -> None:
    """Save response times for all models."""

    file_path = RESULTS_DIR / "summary.txt"

    with open(file_path, "w", encoding="utf-8") as file:
        file.write("Model Comparison Summary\n")
        file.write("=" * 40 + "\n\n")

        for model_name, elapsed in summary:
            file.write(f"{model_name:<10} : {elapsed:.2f} seconds\n")


def print_result(model_name: str, response: str, elapsed: float) -> None:
    """Print results to the terminal."""

    print("=" * 80)
    print(f"Model : {model_name}")
    print(f"Time  : {elapsed:.2f} seconds")
    print("-" * 80)
    print(response)
    print()


def main() -> None:
    summary = []

    for model_name in MODELS:
        try:
            response, elapsed = ask_model(model_name, QUESTION)

            print_result(model_name, response, elapsed)

            save_response(
                model_name=model_name,
                question=QUESTION,
                response=response,
                elapsed=elapsed,
            )

            summary.append((model_name, elapsed))

        except Exception as error:
            print(f"{model_name}: {error}")

    save_summary(summary)

    print("=" * 80)
    print("✅ All responses saved inside the 'results' folder.")


if __name__ == "__main__":
    main()
