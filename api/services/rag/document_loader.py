"""Document loading and processing utilities with dynamic chunking."""

import logging
from pathlib import Path
from typing import List

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter,
    TokenTextSplitter,
)
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    Docx2txtLoader,
)
from langchain_core.documents import Document
from langchain_experimental.text_splitter import SemanticChunker

from keiz.config import settings
from keiz.rag.embeddings import get_embedding_service

logger = logging.getLogger(__name__)


class DynamicChunker:
    """Dynamic chunking strategy that adapts to document structure."""

    def __init__(self, base_chunk_size: int = 1000, chunk_overlap: int = 200):
        """Initialize dynamic chunker."""
        self.base_chunk_size = base_chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_text(self, text: str, metadata: dict = None) -> List[str]:
        """
        Dynamically chunk text based on structure.

        Args:
            text: Text to chunk
            metadata: Document metadata

        Returns:
            List of text chunks
        """
        # Detect document structure
        has_headers = any(line.startswith("#") for line in text.split("\n"))
        has_code_blocks = "```" in text
        avg_paragraph_length = self._get_avg_paragraph_length(text)

        # Adjust chunk size based on structure
        if has_headers or has_code_blocks:
            # Use larger chunks for structured documents
            chunk_size = int(self.base_chunk_size * 1.5)
            separators = ["\n## ", "\n### ", "\n\n", "\n", " "]
        elif avg_paragraph_length > 500:
            # Use smaller chunks for dense text
            chunk_size = int(self.base_chunk_size * 0.7)
            separators = ["\n\n", "\n", ". ", " "]
        else:
            # Use default for normal text
            chunk_size = self.base_chunk_size
            separators = ["\n\n", "\n", " ", ""]

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=separators,
        )

        chunks = splitter.split_text(text)
        logger.debug(
            f"Dynamic chunking: {len(chunks)} chunks (size: {chunk_size}, "
            f"headers: {has_headers}, code: {has_code_blocks})"
        )

        return chunks

    def _get_avg_paragraph_length(self, text: str) -> float:
        """Calculate average paragraph length."""
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
        if not paragraphs:
            return 0
        return sum(len(p) for p in paragraphs) / len(paragraphs)


class SemanticChunkerWrapper:
    """Wrapper for semantic chunking using embeddings."""

    def __init__(self):
        """Initialize semantic chunker."""
        # Get embedding service for semantic similarity
        embedding_service = get_embedding_service()

        # Create a wrapper that works with LangChain's SemanticChunker
        class EmbeddingFunction:
            def embed_documents(self, texts: List[str]) -> List[List[float]]:
                return embedding_service.embed_documents(texts)

            def embed_query(self, text: str) -> List[float]:
                return embedding_service.embed_query(text)

        self.chunker = SemanticChunker(
            EmbeddingFunction(),
            breakpoint_threshold_type="percentile",
        )

    def chunk_text(self, text: str, metadata: dict = None) -> List[str]:
        """
        Semantically chunk text based on meaning.

        Args:
            text: Text to chunk
            metadata: Document metadata

        Returns:
            List of text chunks
        """
        docs = self.chunker.create_documents([text])
        chunks = [doc.page_content for doc in docs]
        logger.debug(f"Semantic chunking: {len(chunks)} chunks")
        return chunks


class DocumentLoader:
    """Service for loading and processing documents with dynamic chunking."""

    def __init__(self):
        """Initialize the document loader with appropriate chunking strategy."""
        strategy = settings.chunking_strategy.lower()

        if strategy == "semantic":
            logger.info("Using semantic chunking strategy")
            self.chunker = SemanticChunkerWrapper()
        elif strategy == "dynamic":
            logger.info("Using dynamic chunking strategy")
            self.chunker = DynamicChunker(
                base_chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
            )
        else:  # fixed
            logger.info("Using fixed chunking strategy")
            self.text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=settings.chunk_size,
                chunk_overlap=settings.chunk_overlap,
                length_function=len,
                separators=["\n\n", "\n", " ", ""],
            )
            self.chunker = None

    def load_file(self, file_path: Path) -> List[Document]:
        """
        Load a single file and return documents.

        Args:
            file_path: Path to the file to load

        Returns:
            List of Document objects

        Raises:
            ValueError: If file type is not supported
        """
        logger.info(f"Loading file: {file_path}")

        suffix = file_path.suffix.lower()

        try:
            if suffix == ".pdf":
                loader = PyPDFLoader(str(file_path))
            elif suffix == ".txt" or suffix == ".md":
                loader = TextLoader(str(file_path))
            elif suffix == ".docx":
                loader = Docx2txtLoader(str(file_path))
            else:
                raise ValueError(f"Unsupported file type: {suffix}")

            documents = loader.load()
            logger.info(f"Loaded {len(documents)} raw documents from {file_path.name}")

            # Add metadata
            for doc in documents:
                doc.metadata["source"] = str(file_path)
                doc.metadata["filename"] = file_path.name

            return documents

        except Exception as e:
            logger.error(f"Error loading file {file_path}: {e}")
            raise

    def split_documents(self, documents: List[Document]) -> List[Document]:
        """
        Split documents into chunks using the configured strategy.

        Args:
            documents: List of documents to split

        Returns:
            List of chunked documents
        """
        logger.info(
            f"Splitting {len(documents)} documents using "
            f"{settings.chunking_strategy} strategy"
        )

        if self.chunker:
            # Use dynamic or semantic chunking
            all_chunks = []
            for doc in documents:
                chunk_texts = self.chunker.chunk_text(
                    doc.page_content, doc.metadata
                )

                # Create Document objects for each chunk
                for i, chunk_text in enumerate(chunk_texts):
                    chunk_doc = Document(
                        page_content=chunk_text,
                        metadata={
                            **doc.metadata,
                            "chunk_index": i,
                            "total_chunks": len(chunk_texts),
                        },
                    )
                    all_chunks.append(chunk_doc)

            logger.info(f"Created {len(all_chunks)} chunks")
            return all_chunks
        else:
            # Use fixed chunking
            chunks = self.text_splitter.split_documents(documents)
            logger.info(f"Created {len(chunks)} chunks")
            return chunks

    def process_file(self, file_path: Path) -> List[Document]:
        """
        Load and split a file into chunks.

        Args:
            file_path: Path to the file to process

        Returns:
            List of chunked documents
        """
        documents = self.load_file(file_path)
        chunks = self.split_documents(documents)
        return chunks

    def process_directory(self, directory: Path) -> List[Document]:
        """
        Process all supported files in a directory.

        Args:
            directory: Path to the directory

        Returns:
            List of all chunked documents
        """
        logger.info(f"Processing directory: {directory}")
        all_chunks = []

        supported_extensions = {".pdf", ".txt", ".md", ".docx"}

        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in supported_extensions:
                try:
                    chunks = self.process_file(file_path)
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    continue

        logger.info(f"Processed directory with {len(all_chunks)} total chunks")
        return all_chunks


def get_document_loader() -> DocumentLoader:
    """Get a document loader instance."""
    return DocumentLoader()
