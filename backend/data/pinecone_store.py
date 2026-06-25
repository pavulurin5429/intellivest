"""
Pinecone vector store wrapper.
Stores document embeddings (EDGAR filings, news) for semantic retrieval by agents.
Uses free Pinecone tier (1 index, 100K vectors).
"""

from pinecone import Pinecone, ServerlessSpec
from transformers import AutoTokenizer, AutoModel
import torch
import numpy as np
from typing import Optional
from loguru import logger
from ..utils.config import get_settings


_pc: Optional[Pinecone] = None
_index = None
_tokenizer = None
_model = None

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIM = 384


def get_pinecone_index():
    global _pc, _index
    if _index is not None:
        return _index

    settings = get_settings()
    _pc = Pinecone(api_key=settings.pinecone_api_key)

    existing = [i.name for i in _pc.list_indexes()]
    if settings.pinecone_index_name not in existing:
        logger.info(f"Creating Pinecone index: {settings.pinecone_index_name}")
        _pc.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )

    _index = _pc.Index(settings.pinecone_index_name)
    logger.info(f"Connected to Pinecone index: {settings.pinecone_index_name}")
    return _index


def get_embedding_model():
    global _tokenizer, _model
    if _model is None:
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        _tokenizer = AutoTokenizer.from_pretrained(EMBEDDING_MODEL)
        _model = AutoModel.from_pretrained(EMBEDDING_MODEL)
        _model.eval()
    return _tokenizer, _model


def embed_text(text: str) -> list[float]:
    """Generate a 384-dim embedding for a text chunk."""
    tokenizer, model = get_embedding_model()
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    # Mean pooling over token embeddings
    embeddings = outputs.last_hidden_state.mean(dim=1).squeeze().numpy()
    return embeddings.tolist()


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    """Split long text into overlapping chunks for embedding."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        start += chunk_size - overlap
    return chunks


def upsert_filing(ticker: str, form: str, date: str, text: str) -> int:
    """Chunk a filing document and upsert all chunks into Pinecone."""
    index = get_pinecone_index()
    chunks = chunk_text(text, chunk_size=800, overlap=80)

    vectors = []
    for i, chunk in enumerate(chunks):
        vector_id = f"{ticker}_{form}_{date}_{i}"
        embedding = embed_text(chunk)
        vectors.append({
            "id": vector_id,
            "values": embedding,
            "metadata": {
                "ticker": ticker,
                "form": form,
                "date": date,
                "chunk_index": i,
                "text": chunk,
            },
        })

    # Upsert in batches of 100
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        index.upsert(vectors=vectors[i:i + batch_size])

    logger.info(f"Upserted {len(vectors)} chunks for {ticker} {form} {date}")
    return len(vectors)


def query_filings(query: str, ticker: Optional[str] = None, top_k: int = 5) -> list[dict]:
    """Semantic search over stored filings. Optionally filter by ticker."""
    index = get_pinecone_index()
    embedding = embed_text(query)

    filter_dict = {"ticker": ticker} if ticker else None
    results = index.query(
        vector=embedding,
        top_k=top_k,
        include_metadata=True,
        filter=filter_dict,
    )

    return [
        {
            "score": match.score,
            "ticker": match.metadata.get("ticker"),
            "form": match.metadata.get("form"),
            "date": match.metadata.get("date"),
            "text": match.metadata.get("text"),
        }
        for match in results.matches
    ]
