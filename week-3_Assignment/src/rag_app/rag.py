import argparse

from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

console = Console()


def load_and_split_documents(data_dir: str):
    loader = PyPDFDirectoryLoader(data_dir)
    documents = loader.load()
    if not documents:
        console.print("[yellow]No PDFs found in the data directory.[/yellow]")
        return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(documents)
    console.print(
        f"[green]Loaded {len(documents)} documents and split into "
        f"{len(splits)} chunks.[/green]"
    )
    return splits


def create_or_load_vectorstore(
    splits, persist_directory: str = "./chroma_db", collection_name: str = "rag_demo"
):
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    if splits:
        console.print("[cyan]Creating new vector store from splits...[/cyan]")
        vectorstore = Chroma.from_documents(
            documents=splits,
            embedding=embeddings,
            persist_directory=persist_directory,
            collection_name=collection_name,
        )
    else:
        console.print("[cyan]Loading existing vector store...[/cyan]")
        vectorstore = Chroma(
            persist_directory=persist_directory,
            embedding_function=embeddings,
            collection_name=collection_name,
        )
    return vectorstore


def main():
    parser = argparse.ArgumentParser(description="RAG Demo with ChromaDB")
    parser.add_argument(
        "--ingest", action="store_true", help="Ingest PDFs from data/ into ChromaDB"
    )
    parser.add_argument("--query", type=str, help="Query the RAG system")
    args = parser.parse_args()

    persist_dir = "./chroma_db"

    if args.ingest:
        splits = load_and_split_documents("data")
        create_or_load_vectorstore(splits, persist_directory=persist_dir)
        console.print("[green]Ingestion complete![/green]")
    elif args.query:
        vectorstore = create_or_load_vectorstore([], persist_directory=persist_dir)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

        # Retrieve docs
        docs = retriever.invoke(args.query)
        context = "\n\n".join(doc.page_content for doc in docs)

        console.print(f"\n[bold blue]Retrieved {len(docs)} documents[/bold blue]")

        # Generation
        llm = ChatOllama(model="llama3", temperature=0)
        prompt_template = PromptTemplate.from_template(
            "Use the following pieces of retrieved context to answer the user's "
            "question.\n"
            "If you don't know the answer, just say that you don't know.\n\n"
            "Context: {context}\n\n"
            "Question: {question}\n\n"
            "Answer:"
        )
        prompt = prompt_template.invoke({"context": context, "question": args.query})

        console.print("\n[bold magenta]Generating Answer...[/bold magenta]")
        response = llm.invoke(prompt)
        console.print(f"\n[green]{response.content}[/green]")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
