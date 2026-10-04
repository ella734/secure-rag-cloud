"""Pydantic request and response schemas for REST API."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Incoming user query payload."""
    query: str = Field(
        ...,
        min_length=3,
        max_length=1000,
        description="User question in French or English",
        examples=["Quelles sont les exigences de sécurité pour Azure Container Apps ?"],
    )
    top_k: Optional[int] = Field(
        default=None,
        ge=1,
        le=10,
        description="Override top-K retrieved context documents",
    )
    threshold: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Override minimum cosine similarity threshold",
    )


class CitationItem(BaseModel):
    """Source document citation reference."""
    citation_id: str
    source_file: str
    section: str
    similarity_score: float
    snippet: str


class QueryResponse(BaseModel):
    """Complete RAG response payload with grounded citations and observability metadata."""
    answer: str
    citations: List[CitationItem]
    refusal: bool
    correlation_id: str
    retrieval_latency_ms: float
    generation_latency_ms: float
    total_latency_ms: float
    security_status: str


class SecurityScanRequest(BaseModel):
    """Payload to test prompt injection or jailbreak detection."""
    prompt: str = Field(..., min_length=1, max_length=5000)


class SecurityScanResponse(BaseModel):
    """Security firewall evaluation result."""
    is_safe: bool
    risk_score: float
    threat_category: str
    mitigation_action: str
    detected_patterns: List[str]
    explanation: Optional[str] = None


class HealthResponse(BaseModel):
    """Service health and readiness status."""
    status: str
    version: str
    environment: str
    indexed_chunks: int
    security_enabled: bool
    embedding_provider: str
    llm_provider: str
