"""Application configuration module using Pydantic Settings."""

from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """SecureRAG Cloud configuration settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # Core Application
    app_name: str = "SecureRAG Cloud"
    environment: Literal["development", "staging", "production", "test"] = "development"
    log_level: str = "INFO"
    app_host: str = "0.0.0.0"
    app_port: int = 8000

    # LLM Settings
    llm_provider: Literal["mock", "azure_openai", "openai"] = "mock"
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = "https://your-resource.openai.azure.com/"
    azure_openai_deployment: str = "gpt-4o-mini"
    azure_openai_api_version: str = "2024-06-01-preview"
    openai_api_key: str = ""

    # Embedding Provider
    embedding_provider: Literal["tfidf", "azure_openai", "sentence_transformers"] = "tfidf"
    embedding_deployment: str = "text-embedding-3-small"

    # RAG Engine Parameters
    rag_chunk_size: int = Field(default=500, ge=100, le=4000)
    rag_chunk_overlap: int = Field(default=100, ge=0, le=500)
    rag_top_k: int = Field(default=4, ge=1, le=20)
    rag_similarity_threshold: float = Field(default=0.15, ge=0.0, le=1.0)

    # Security Guardrails
    security_enabled: bool = True
    max_query_length: int = Field(default=1000, ge=10, le=10000)
    block_indirect_injections: bool = True
    output_guard_enabled: bool = True
    strict_refusal_mode: bool = True

    # Azure Monitor & Observability
    applicationinsights_connection_string: str = ""
    otel_service_name: str = "secure-rag-cloud"


settings = Settings()
