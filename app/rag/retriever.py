"""Vector retriever and similarity search engine."""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import numpy as np
from app.core.config import settings
from app.rag.ingestion import DocumentChunk
from app.rag.embeddings import BaseEmbeddings, TfidfEmbeddings, get_embedding_provider


@dataclass
class ScoredChunk:
    """A retrieved chunk bundled with its semantic similarity score."""
    chunk: DocumentChunk
    similarity_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "chunk_id": self.chunk.chunk_id,
            "text": self.chunk.text,
            "source_file": self.chunk.source_file,
            "section": self.chunk.section,
            "similarity_score": round(self.similarity_score, 4),
        }


@dataclass
class RetrievalResult:
    """Complete retrieval payload with candidate chunks and execution latency."""
    query: str
    candidates: List[ScoredChunk]
    retrieval_latency_ms: float
    total_indexed_chunks: int

    @property
    def has_sufficient_context(self) -> bool:
        return len(self.candidates) > 0


class VectorRetriever:
    """In-memory dense vector retriever with cosine similarity and threshold gating."""

    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddings] = None,
        similarity_threshold: float = settings.rag_similarity_threshold,
        top_k: int = settings.rag_top_k,
    ):
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.similarity_threshold = similarity_threshold
        self.top_k = top_k
        self.chunks: List[DocumentChunk] = []
        self.doc_vectors: Optional[np.ndarray] = None

    def index_documents(self, chunks: List[DocumentChunk]) -> int:
        """Embed and index document chunks."""
        if not chunks:
            self.chunks = []
            self.doc_vectors = None
            return 0

        self.chunks = chunks
        texts = [c.text for c in chunks]

        # If TF-IDF, fit vectorizer on texts
        if isinstance(self.embedding_provider, TfidfEmbeddings):
            self.embedding_provider.fit(texts)

        self.doc_vectors = self.embedding_provider.embed_documents(texts)
        return len(self.chunks)

    def retrieve(self, query: str, top_k: Optional[int] = None, threshold: Optional[float] = None) -> RetrievalResult:
        """Retrieve the most relevant chunks matching the query above similarity threshold."""
        start_time = time.perf_counter()
        k = top_k or self.top_k
        min_threshold = threshold if threshold is not None else self.similarity_threshold

        if not self.chunks or self.doc_vectors is None or len(self.chunks) == 0:
            elapsed_ms = (time.perf_counter() - start_time) * 1000.0
            return RetrievalResult(
                query=query,
                candidates=[],
                retrieval_latency_ms=round(elapsed_ms, 2),
                total_indexed_chunks=0,
            )

        query_vec = self.embedding_provider.embed_query(query)

        # Compute cosine similarities
        dot_products = np.dot(self.doc_vectors, query_vec)
        doc_norms = np.linalg.norm(self.doc_vectors, axis=1)
        query_norm = np.linalg.norm(query_vec)

        denom = doc_norms * query_norm
        denom[denom == 0] = 1e-9  # Prevent division by zero
        scores = dot_products / denom

        # Sort indices descending by score
        ranked_indices = np.argsort(scores)[::-1]

        candidates = []
        for idx in ranked_indices:
            score = float(scores[idx])
            if score < min_threshold:
                break
            candidates.append(ScoredChunk(chunk=self.chunks[idx], similarity_score=score))
            if len(candidates) >= k:
                break

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0
        return RetrievalResult(
            query=query,
            candidates=candidates,
            retrieval_latency_ms=round(elapsed_ms, 2),
            total_indexed_chunks=len(self.chunks),
        )
