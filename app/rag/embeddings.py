"""Embeddings abstraction supporting TF-IDF, HuggingFace, and Azure OpenAI."""

from abc import ABC, abstractmethod
from typing import List
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from app.core.config import settings


class BaseEmbeddings(ABC):
    """Abstract base class for text embedding engines."""

    @abstractmethod
    def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Compute embeddings for a list of document texts."""
        pass

    @abstractmethod
    def embed_query(self, text: str) -> np.ndarray:
        """Compute embedding for a single user query."""
        pass


class TfidfEmbeddings(BaseEmbeddings):
    """Deterministic TF-IDF embedding engine with sublinear term frequency and n-grams."""

    def __init__(self, max_features: int = 2048):
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=max_features,
            sublinear_tf=True,
            norm="l2",
            stop_words="english",
        )
        self.is_fitted = False

    def fit(self, texts: List[str]) -> "TfidfEmbeddings":
        """Fit the vectorizer vocabulary on document texts."""
        if texts:
            self.vectorizer.fit(texts)
            self.is_fitted = True
        return self

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Compute TF-IDF vectors for documents."""
        if not self.is_fitted:
            self.fit(texts)
        matrix = self.vectorizer.transform(texts).toarray()
        return matrix.astype(np.float32)

    def embed_query(self, text: str) -> np.ndarray:
        """Compute TF-IDF vector for a query."""
        if not self.is_fitted:
            # Fallback fit on query if unfitted
            self.fit([text])
        vec = self.vectorizer.transform([text]).toarray()[0]
        return vec.astype(np.float32)


class AzureOpenAIEmbeddings(BaseEmbeddings):
    """Azure OpenAI text-embedding-3-small / text-embedding-ada-002 provider."""

    def __init__(
        self,
        endpoint: str = settings.azure_openai_endpoint,
        api_key: str = settings.azure_openai_api_key,
        deployment: str = settings.embedding_deployment,
        api_version: str = settings.azure_openai_api_version,
    ):
        self.endpoint = endpoint
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version

    def embed_documents(self, texts: List[str]) -> np.ndarray:
        """Embed document batch via Azure OpenAI API."""
        import httpx

        url = f"{self.endpoint.rstrip('/')}/openai/deployments/{self.deployment}/embeddings?api-version={self.api_version}"
        headers = {"api-key": self.api_key, "Content-Type": "application/json"}
        payload = {"input": texts}

        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()["data"]
            embeddings = [item["embedding"] for item in data]
            arr = np.array(embeddings, dtype=np.float32)
            # L2 normalize
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return arr / norms

    def embed_query(self, text: str) -> np.ndarray:
        """Embed single query via Azure OpenAI API."""
        return self.embed_documents([text])[0]


def get_embedding_provider() -> BaseEmbeddings:
    """Factory creating the configured embedding provider."""
    provider = settings.embedding_provider.lower()
    if provider == "azure_openai" and settings.azure_openai_api_key:
        return AzureOpenAIEmbeddings()
    # Default to high-performance deterministic TF-IDF
    return TfidfEmbeddings()
