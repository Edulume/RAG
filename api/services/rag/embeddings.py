"""Embedding service using self-hosted sentence-transformers."""

import logging
from typing import List

from sentence_transformers import SentenceTransformer

from keiz.config import settings

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Service for generating embeddings using self-hosted models."""

    def __init__(self):
        """Initialize the embedding service with the configured model."""
        logger.info(f"Loading embedding model: {settings.embedding_model}")
        self.model = SentenceTransformer(settings.embedding_model)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Embedding model loaded. Dimension: {self.dimension}")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for a list of documents.

        Args:
            texts: List of text strings to embed

        Returns:
            List of embedding vectors
        """
        logger.debug(f"Embedding {len(texts)} documents")
        embeddings = self.model.encode(
            texts,
            show_progress_bar=len(texts) > 10,
            convert_to_numpy=True,
        )
        return embeddings.tolist()

    def embed_query(self, text: str) -> List[float]:
        """
        Generate embedding for a single query.

        Args:
            text: Query text to embed

        Returns:
            Embedding vector
        """
        logger.debug("Embedding query")
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# Global embedding service instance
_embedding_service = None


def get_embedding_service() -> EmbeddingService:
    """Get or create the global embedding service instance."""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service
