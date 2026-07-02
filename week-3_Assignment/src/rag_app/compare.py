import argparse

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console
from rich.table import Table

console = Console()


def load_documents(data_dir: str):
    loader = PyPDFDirectoryLoader(data_dir)
    documents = loader.load()
    if not documents:
        return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    return text_splitter.split_documents(documents)


def create_store(splits, model_name: str, collection_name: str):
    embeddings = OllamaEmbeddings(model=model_name)
    vectorstore = Chroma.from_documents(
        documents=splits,
        embedding=embeddings,
        persist_directory="./chroma_db_compare",
        collection_name=collection_name,
    )
    return vectorstore


def main():
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

    splits = load_documents("data")
    if not splits:
        console.print("[red]No documents to index![/red]")
        return

    console.print(f"[cyan]Indexing documents with {args.model1}...[/cyan]")
    store1 = create_store(splits, args.model1, "model1_collection")

    console.print(f"[cyan]Indexing documents with {args.model2}...[/cyan]")
    store2 = create_store(splits, args.model2, "model2_collection")

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
