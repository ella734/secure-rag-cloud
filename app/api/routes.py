"""FastAPI application routes and endpoint handlers."""

import time
import uuid
from pathlib import Path
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, Depends, status

from app.core.config import settings
from app.api.schemas import (
    QueryRequest,
    QueryResponse,
    CitationItem,
    SecurityScanRequest,
    SecurityScanResponse,
    HealthResponse,
)
from app.security import (
    security_guard,
    InputValidator,
    ThreatCategory,
)
from app.rag import (
    DocumentIngestor,
    VectorRetriever,
    RAGGenerator,
    SYSTEM_PROMPT,
)
from app.monitoring import (
    logger,
    tracer,
    correlation_id_ctx,
    metrics_tracker,
)

router = APIRouter(prefix="/api/v1")

# Global singleton engine components
_retriever: VectorRetriever = VectorRetriever()
_generator: RAGGenerator = RAGGenerator()
_is_initialized: bool = False


def get_rag_engine() -> tuple[VectorRetriever, RAGGenerator]:
    """Dependency provider for RAG retriever and generator engines."""
    global _is_initialized, _retriever, _generator
    if not _is_initialized:
        corpus_dir = Path(__file__).resolve().parent.parent.parent / "data" / "corpus"
        if corpus_dir.exists():
            ingestor = DocumentIngestor(
                chunk_size=settings.rag_chunk_size,
                chunk_overlap=settings.rag_chunk_overlap,
            )
            chunks = ingestor.load_directory(corpus_dir)
            _retriever.index_documents(chunks)
            logger.info(
                f"RAG engine initialized with {len(chunks)} chunks from {corpus_dir}",
                extra={"extra_data": {"indexed_chunks": len(chunks)}},
            )
        _is_initialized = True
    return _retriever, _generator


@router.post("/query", response_model=QueryResponse, summary="Query the Technical RAG pipeline")
async def query_rag(
    payload: QueryRequest,
    engines: tuple[VectorRetriever, RAGGenerator] = Depends(get_rag_engine),
) -> QueryResponse:
    """Execute a guarded RAG search query with security inspection and citations."""
    req_start = time.perf_counter()
    cid = correlation_id_ctx.get()
    retriever, generator = engines

    with tracer.start_as_current_span("rag_request_pipeline") as span:
        span.set_attribute("correlation_id", cid)
        span.set_attribute("query_text", payload.query)

        # Step 1: Input Validation & Sanitization
        is_valid, validation_err = InputValidator.validate(payload.query)
        if not is_valid:
            logger.warning(f"Input validation rejected: {validation_err}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=validation_err,
            )

        sanitized_query = InputValidator.sanitize(payload.query)

        # Step 2: Prompt Injection & Adversarial Security Scan (OWASP LLM01)
        with tracer.start_as_current_span("security_guard_scan"):
            scan_res = security_guard.scan_query(sanitized_query)

        if not scan_res.is_safe:
            metrics_tracker.record_query(
                retrieval_ms=0.0,
                generation_ms=0.0,
                is_refusal=True,
                is_blocked=True,
            )
            logger.warning(
                f"Adversarial prompt injection blocked: {scan_res.threat_category.value}",
                extra={"extra_data": {"threat": scan_res.threat_category.value, "patterns": scan_res.detected_patterns}},
            )
            return QueryResponse(
                answer=(
                    f"⚠️ Requête bloquée par le pare-feu de sécurité SecureRAG (OWASP LLM01 - {scan_res.threat_category.value}). "
                    f"Raison : {scan_res.explanation}"
                ),
                citations=[],
                refusal=True,
                correlation_id=cid,
                retrieval_latency_ms=0.0,
                generation_latency_ms=0.0,
                total_latency_ms=round((time.perf_counter() - req_start) * 1000.0, 2),
                security_status=f"BLOCKED_{scan_res.threat_category.value}",
            )

        # Step 3: Vector Retrieval
        with tracer.start_as_current_span("vector_retrieval"):
            retrieval_res = retriever.retrieve(
                query=sanitized_query,
                top_k=payload.top_k,
                threshold=payload.threshold,
            )

        # Step 4: Grounded Generation with Strict Refusal
        with tracer.start_as_current_span("llm_generation"):
            gen_res = generator.generate(
                query=sanitized_query,
                candidates=retrieval_res.candidates,
            )

        # Step 5: Output Guardrail Scan
        if not security_guard.scan_output(gen_res.answer, SYSTEM_PROMPT):
            logger.error("Output guardrail triggered: confidential system prompt leak blocked.")
            gen_res.answer = "⚠️ Réponse censurée par le garde-fou de sortie pour motif de sécurité."
            gen_res.citations = []

        total_ms = (time.perf_counter() - req_start) * 1000.0

        # Step 6: Telemetry and SLI metrics recording
        metrics_tracker.record_query(
            retrieval_ms=retrieval_res.retrieval_latency_ms,
            generation_ms=gen_res.generation_latency_ms,
            is_refusal=gen_res.refusal,
            is_blocked=False,
        )

        citation_items = [
            CitationItem(
                citation_id=c["citation_id"],
                source_file=c["source_file"],
                section=c["section"],
                similarity_score=c["similarity_score"],
                snippet=c["snippet"],
            )
            for c in gen_res.citations
        ]

        logger.info(
            f"Query processed successfully in {total_ms:.1f}ms (Refusal: {gen_res.refusal})",
            extra={"extra_data": {
                "retrieval_ms": retrieval_res.retrieval_latency_ms,
                "generation_ms": gen_res.generation_latency_ms,
                "citations_count": len(citation_items),
            }},
        )

        return QueryResponse(
            answer=gen_res.answer,
            citations=citation_items,
            refusal=gen_res.refusal,
            correlation_id=cid,
            retrieval_latency_ms=retrieval_res.retrieval_latency_ms,
            generation_latency_ms=gen_res.generation_latency_ms,
            total_latency_ms=round(total_ms, 2),
            security_status="PASSED",
        )


@router.post("/security/scan", response_model=SecurityScanResponse, summary="Inspect prompt for adversarial threats")
async def scan_security(payload: SecurityScanRequest) -> SecurityScanResponse:
    """Analyze an arbitrary prompt against prompt injection and jailbreak signatures."""
    res = security_guard.scan_query(payload.prompt)
    return SecurityScanResponse(
        is_safe=res.is_safe,
        risk_score=res.risk_score,
        threat_category=res.threat_category.value,
        mitigation_action=res.mitigation_action,
        detected_patterns=res.detected_patterns,
        explanation=res.explanation,
    )


@router.get("/health", response_model=HealthResponse, summary="Liveness and Readiness Probe")
async def health_check(
    engines: tuple[VectorRetriever, RAGGenerator] = Depends(get_rag_engine),
) -> HealthResponse:
    """Kubernetes / Azure Container Apps liveness & readiness endpoint."""
    retriever, _ = engines
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.environment,
        indexed_chunks=len(retriever.chunks),
        security_enabled=settings.security_enabled,
        embedding_provider=settings.embedding_provider,
        llm_provider=settings.llm_provider,
    )


@router.get("/metrics", summary="Operational LLMOps telemetry metrics")
async def get_metrics() -> Dict[str, Any]:
    """Retrieve runtime operational statistics, SLIs, and latency percentiles."""
    return metrics_tracker.get_summary()
