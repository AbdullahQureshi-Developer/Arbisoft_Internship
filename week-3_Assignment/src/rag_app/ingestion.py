import hashlib

from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from rich.console import Console

console = Console()


def load_and_split_documents(data_dir: str) -> list[Document]:
    loader = PyPDFDirectoryLoader(data_dir)
    documents = loader.load()
    if not documents:
        console.print("[yellow]No PDFs found in the data directory.[/yellow]")
        return []

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    splits = text_splitter.split_documents(documents)

    # Assign deterministic chunk IDs
    # Using source filename + chunk index to generate a stable ID
    for i, doc in enumerate(splits):
        source = doc.metadata.get("source", "unknown")
        # Ensure we have a unique and valid string ID
        # Hashing provides a nice clean ID
        doc_id_raw = f"{source}_{i}"
        doc_id = hashlib.md5(doc_id_raw.encode("utf-8")).hexdigest()
        doc.metadata["id"] = doc_id

    console.print(
        f"[green]Loaded {len(documents)} documents and split into "
        f"{len(splits)} chunks.[/green]"
    )
    return splits
