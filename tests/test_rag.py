"""Unit tests for RAG pipeline: chunking, embedding, retrieval, and grounding."""

import pytest
from pathlib import Path
from app.rag import (
    RecursiveTextSplitter,
    DocumentIngestor,
    VectorRetriever,
    RAGGenerator,
    DocumentChunk,
    STANDARD_REFUSAL_FR,
)


def test_text_splitter_basic():
    splitter = RecursiveTextSplitter(chunk_size=100, chunk_overlap=20)
    text = (
        "Azure Container Apps is a serverless environment built on Kubernetes. "
        "It supports automatic scaling with KEDA and traffic routing with Envoy. "
        "Workloads can be securely isolated in custom virtual networks."
    )
    chunks = splitter.split_text(text)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 120  # respects size budget reasonably


def test_document_ingestor_corpus(tmp_path):
    doc_path = tmp_path / "test_doc.md"
    doc_path.write_text(
        "# Section 1: Security\nContainer Apps must use Managed Identities.\n\n"
        "## Section 2: Ingress\nEnforce TLS 1.3 for all public endpoints.",
        encoding="utf-8",
    )
    ingestor = DocumentIngestor(chunk_size=150, chunk_overlap=30)
    chunks = ingestor.load_file(doc_path)
    assert len(chunks) >= 2
    sections = [c.section for c in chunks]
    assert any("Section 1" in s for s in sections)
    assert any("Section 2" in s for s in sections)


def test_retriever_indexing_and_similarity():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            text="Azure Managed Identity eliminates credentials in code for ACA containers.",
            source_file="auth.md",
            section="Identity",
        ),
        DocumentChunk(
            chunk_id="c2",
            text="Cooking pasta requires boiling water and a pinch of salt.",
            source_file="recipes.md",
            section="Kitchen",
        ),
    ]

    retriever = VectorRetriever(top_k=2, similarity_threshold=0.10)
    count = retriever.index_documents(chunks)
    assert count == 2

    # Query related to identity
    result = retriever.retrieve("Comment fonctionne Managed Identity pour les conteneurs ?")
    assert len(result.candidates) > 0
    assert result.candidates[0].chunk.chunk_id == "c1"
    assert result.retrieval_latency_ms >= 0.0


def test_anti_hallucination_refusal():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            text="Azure Container Apps supports KEDA autoscaling.",
            source_file="aca.md",
            section="Scaling",
        ),
    ]
    retriever = VectorRetriever(top_k=2, similarity_threshold=0.30)
    retriever.index_documents(chunks)
    generator = RAGGenerator()

    # Query about completely unrelated domain
    result = retriever.retrieve("Quelle est la vitesse maximale d'un avion Rafale ?")
    assert len(result.candidates) == 0

    # Generator must strictly refuse
    gen_result = generator.generate("Quelle est la vitesse maximale d'un avion Rafale ?", result.candidates)
    assert gen_result.refusal is True
    assert STANDARD_REFUSAL_FR in gen_result.answer
    assert len(gen_result.citations) == 0


def test_grounded_answer_with_citations():
    chunks = [
        DocumentChunk(
            chunk_id="c1",
            text="Workloads running in Container Apps must use Azure Managed Identities to authenticate.",
            source_file="azure_container_apps_security.md",
            section="Identity",
        ),
    ]
    retriever = VectorRetriever(top_k=1, similarity_threshold=0.10)
    retriever.index_documents(chunks)
    generator = RAGGenerator()

    res = retriever.retrieve("Comment s'authentifier dans Container Apps ?")
    gen_res = generator.generate("Comment s'authentifier dans Container Apps ?", res.candidates)

    assert gen_res.refusal is False
    assert len(gen_res.citations) > 0
    assert "[Doc 1]" in gen_res.answer
