"""FAISS vector store management."""

import logging
import pickle
from pathlib import Path
from typing import List, Optional, Tuple

import faiss
import numpy as np
from langchain_core.documents import Document

from keiz.config import settings
from keiz.rag.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class VectorStore:
    """FAISS-based vector store for document retrieval."""

    def __init__(self):
        """Initialize the vector store."""
        self.embedding_service = get_embedding_service()
        self.dimension = self.embedding_service.dimension
        self.index: Optional[faiss.Index] = None
        self.documents: List[Document] = []
        self.index_path = settings.faiss_index_path
        self.index_file = self.index_path / "index.faiss"
        self.docs_file = self.index_path / "documents.pkl"

        # Ensure directory exists
        settings.ensure_directories()

        # Try to load existing index
        self.load()

    def _create_index(self) -> faiss.Index:
        """Create a new FAISS index."""
        logger.info(f"Creating new FAISS index with dimension {self.dimension}")
        index = faiss.IndexFlatL2(self.dimension)
        return index

    def add_documents(self, documents: List[Document]) -> None:
        """
        Add documents to the vector store.

        Args:
            documents: List of documents to add
        """
        if not documents:
            logger.warning("No documents to add")
            return

        logger.info(f"Adding {len(documents)} documents to vector store")

        # Extract text from documents
        texts = [doc.page_content for doc in documents]

        # Generate embeddings
        embeddings = self.embedding_service.embed_documents(texts)

        # Convert to numpy array
        embeddings_array = np.array(embeddings, dtype=np.float32)

        # Create index if it doesn't exist
        if self.index is None:
            self.index = self._create_index()

        # Add to index
        self.index.add(embeddings_array)

        # Store documents
        self.documents.extend(documents)

        logger.info(f"Vector store now contains {len(self.documents)} documents")

    def similarity_search(
        self, query: str, k: Optional[int] = None
    ) -> List[Tuple[Document, float]]:
        """
        Search for similar documents.

        Args:
            query: Query text
            k: Number of results to return (default from settings)

        Returns:
            List of (document, score) tuples
        """
        if self.index is None or len(self.documents) == 0:
            logger.warning("Vector store is empty")
            return []

        k = k or settings.top_k_results
        k = min(k, len(self.documents))

        logger.info(f"Searching for top {k} similar documents")

        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(query)
        query_array = np.array([query_embedding], dtype=np.float32)

        # Search
        distances, indices = self.index.search(query_array, k)

        # Prepare results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                results.append((self.documents[idx], float(distance)))

        logger.info(f"Found {len(results)} results")
        return results

    def save(self) -> None:
        """Save the index and documents to disk."""
        if self.index is None:
            logger.warning("No index to save")
            return

        logger.info(f"Saving vector store to {self.index_path}")

        # Save FAISS index
        faiss.write_index(self.index, str(self.index_file))

        # Save documents
        with open(self.docs_file, "wb") as f:
            pickle.dump(self.documents, f)

        logger.info("Vector store saved successfully")

    def load(self) -> bool:
        """
        Load the index and documents from disk.

        Returns:
            True if loaded successfully, False otherwise
        """
        if not self.index_file.exists() or not self.docs_file.exists():
            logger.info("No existing vector store found")
            return False

        try:
            logger.info(f"Loading vector store from {self.index_path}")

            # Load FAISS index
            self.index = faiss.read_index(str(self.index_file))

            # Load documents
            with open(self.docs_file, "rb") as f:
                self.documents = pickle.load(f)

            logger.info(f"Loaded vector store with {len(self.documents)} documents")
            return True

        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    def clear(self) -> None:
        """Clear the vector store."""
        logger.info("Clearing vector store")
        self.index = None
        self.documents = []

        if self.index_file.exists():
            self.index_file.unlink()
        if self.docs_file.exists():
            self.docs_file.unlink()

    def get_stats(self) -> dict:
        """Get statistics about the vector store."""
        return {
            "total_documents": len(self.documents),
            "index_size": self.index.ntotal if self.index else 0,
            "dimension": self.dimension,
        }


# Global vector store instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create the global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
