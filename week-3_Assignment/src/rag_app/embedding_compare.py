import argparse

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_ollama import OllamaEmbeddings
from rich.console import Console
from rich.table import Table

from rag_app.ingestion import load_and_split_documents, sync_vectorstore

console = Console()


def get_or_create_store(model_name: str, collection_name: str) -> Chroma:
    embeddings = OllamaEmbeddings(model=model_name)
    vectorstore = Chroma(
        embedding_function=embeddings,
        persist_directory="./chroma_db_compare",
        collection_name=collection_name,
    )
    return vectorstore


def ingest_incrementally(vectorstore: Chroma, splits: list[Document]) -> None:
    sync_vectorstore(vectorstore, splits)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare Embedding Models")
    parser.add_argument(
        "--model1", type=str, default="nomic-embed-text", help="First embedding model"
    )
    parser.add_argument(
        "--model2", type=str, default="all-minilm", help="Second embedding model"
    )
    parser.add_argument(
        "--query",
        type=str,
        default="What are the three types of machine learning?",
        help="Query to test",
    )
    args = parser.parse_args()

    splits = load_and_split_documents("data")
    if not splits:
        console.print("[red]No documents to index![/red]")
        return

    console.print(f"[cyan]Indexing documents with {args.model1}...[/cyan]")
    store1 = get_or_create_store(args.model1, "model1_collection")
    ingest_incrementally(store1, splits)

    console.print(f"[cyan]Indexing documents with {args.model2}...[/cyan]")
    store2 = get_or_create_store(args.model2, "model2_collection")
    ingest_incrementally(store2, splits)

    console.print(f"\n[bold green]Query:[/bold green] {args.query}\n")

    docs1 = store1.similarity_search_with_score(args.query, k=2)
    docs2 = store2.similarity_search_with_score(args.query, k=2)

    table = Table(title="Embedding Model Comparison")
    table.add_column("Model", style="cyan")
    table.add_column("Top 1 Chunk Content Snippet", style="magenta")
    table.add_column("Top 1 Score (Distance)", justify="right", style="green")

    snippet1 = (
        docs1[0][0].page_content[:100].replace("\n", " ") + "..." if docs1 else "N/A"
    )
    score1 = f"{docs1[0][1]:.4f}" if docs1 else "N/A"

    snippet2 = (
        docs2[0][0].page_content[:100].replace("\n", " ") + "..." if docs2 else "N/A"
    )
    score2 = f"{docs2[0][1]:.4f}" if docs2 else "N/A"

    table.add_row(args.model1, snippet1, score1)
    table.add_row(args.model2, snippet2, score2)

    console.print(table)


if __name__ == "__main__":
    main()
