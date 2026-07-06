"""
PDF Evidence Agent
------------------
Tools  : ChromaDB (vector store) + PDF Loader (pypdf) + sentence-transformers
Purpose: Ingests a small library of reference PDFs (AI Safety, Company Policy,
         WHO Guidelines, Government AI Rules, NIST AI RMF, ...) once, then lets
         the crew query that library with RAG to find grounded evidence for a
         claim.
"""

import os
import glob
import hashlib

import chromadb
from chromadb.utils import embedding_functions
from pypdf import PdfReader
from crewai import Agent
from crewai.tools import tool

CHROMA_DIR = os.getenv("CHROMA_PERSIST_DIR", "./vector_db")
PDF_FOLDER = os.getenv("PDF_FOLDER", "./pdfs")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")
COLLECTION_NAME = "truthshield_docs"

_client = None
_collection = None


def _get_collection():
    """Lazily create (or reopen) the persistent Chroma collection."""
    global _client, _collection
    if _collection is not None:
        return _collection

    _client = chromadb.PersistentClient(path=CHROMA_DIR)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBEDDING_MODEL
    )
    _collection = _client.get_or_create_collection(
        name=COLLECTION_NAME, embedding_function=embed_fn
    )
    return _collection


def _chunk_text(text: str, chunk_size: int = 800, overlap: int = 100):
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return [c for c in chunks if c.strip()]


def ingest_pdfs(pdf_folder: str = PDF_FOLDER) -> int:
    """
    Reads every PDF in `pdf_folder`, chunks it, embeds it, and stores it in
    ChromaDB. Safe to call repeatedly -- chunks are keyed by content hash so
    duplicates are skipped. Returns the number of new chunks added.
    """
    collection = _get_collection()
    added = 0

    for path in glob.glob(os.path.join(pdf_folder, "*.pdf")):
        try:
            reader = PdfReader(path)
            full_text = "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception as e:  # noqa: BLE001
            print(f"[RAG ingest] Failed to read {path}: {e}")
            continue

        for chunk in _chunk_text(full_text):
            chunk_id = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
            existing = collection.get(ids=[chunk_id])
            if existing["ids"]:
                continue
            collection.add(
                ids=[chunk_id],
                documents=[chunk],
                metadatas=[{"source": os.path.basename(path)}],
            )
            added += 1

    return added


@tool("PDF Knowledge Base Search")
def pdf_search_tool(query: str) -> str:
    """
    Search the ingested PDF knowledge base (AI Safety / Policy / WHO / NIST /
    government AI guideline documents) for passages relevant to `query`.
    Returns the top matching passages with their source filename.
    """
    collection = _get_collection()
    if collection.count() == 0:
        return (
            "[No PDFs ingested yet] Drop reference PDFs into the /pdfs folder "
            "and call ingest_pdfs() on startup, then re-run this query."
        )

    results = collection.query(query_texts=[query], n_results=4)
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]

    if not docs:
        return "No relevant passages found in the PDF knowledge base."

    formatted = []
    for i, (doc, meta) in enumerate(zip(docs, metas), start=1):
        formatted.append(f"{i}. [{meta.get('source')}] {doc.strip()[:500]}")
    return "\n\n".join(formatted)


def build_rag_agent(llm=None) -> Agent:
    return Agent(
        role="PDF Evidence Agent",
        goal=(
            "Retrieve the most relevant passages from the trusted PDF "
            "knowledge base (AI safety, policy, WHO, and government "
            "guidelines) to ground the fact-check in authoritative documents."
        ),
        backstory=(
            "You are a librarian-researcher who has read every AI governance "
            "and safety document in the library and can instantly recall the "
            "exact passage relevant to any claim."
        ),
        tools=[pdf_search_tool],
        llm=llm,
        verbose=True,
        allow_delegation=False,
    )
