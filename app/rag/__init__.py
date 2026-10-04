"""RAG package exports."""

from app.rag.ingestion import DocumentChunk, DocumentIngestor, RecursiveTextSplitter
from app.rag.embeddings import BaseEmbeddings, TfidfEmbeddings, AzureOpenAIEmbeddings, get_embedding_provider
from app.rag.retriever import VectorRetriever, ScoredChunk, RetrievalResult
from app.rag.generation import RAGGenerator, GenerationResult, SYSTEM_PROMPT, STANDARD_REFUSAL_FR

__all__ = [
    "DocumentChunk",
    "DocumentIngestor",
    "RecursiveTextSplitter",
    "BaseEmbeddings",
    "TfidfEmbeddings",
    "AzureOpenAIEmbeddings",
    "get_embedding_provider",
    "VectorRetriever",
    "ScoredChunk",
    "RetrievalResult",
    "RAGGenerator",
    "GenerationResult",
    "SYSTEM_PROMPT",
    "STANDARD_REFUSAL_FR",
]
