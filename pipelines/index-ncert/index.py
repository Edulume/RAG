#!/usr/bin/env python3
"""
NCERT Book Indexing Pipeline
Indexes PDF books into FAISS for semantic search.

Usage:
    python pipelines/index-ncert/index.py
    python pipelines/index-ncert/index.py --source data/ncert-books/Class-10
    python pipelines/index-ncert/index.py --clear  # Clear and rebuild index
"""

import argparse
import logging
import os
import pickle
import re
import sys
from pathlib import Path
from typing import List, Dict, Optional

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from pypdf import PdfReader

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
CONFIG = {
    "embedding_model": "all-MiniLM-L6-v2",  # Fast & good quality
    "chunk_size": 1000,  # Characters per chunk
    "chunk_overlap": 200,  # Overlap between chunks
    "index_path": PROJECT_ROOT / "indexes" / "ncert-content",
    "data_path": PROJECT_ROOT / "data" / "ncert-books",
}


class Document:
    """Simple document class to hold content and metadata."""

    def __init__(self, content: str, metadata: Dict):
        self.content = content
        self.metadata = metadata

    def __repr__(self):
        return f"Document(class={self.metadata.get('class')}, subject={self.metadata.get('subject')}, chapter={self.metadata.get('chapter')})"


class PDFLoader:
    """Load and extract text from PDF files."""

    @staticmethod
    def load(file_path: Path) -> str:
        """Extract text from a PDF file."""
        try:
            reader = PdfReader(str(file_path))
            text = ""
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
            return text.strip()
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return ""

    @staticmethod
    def extract_metadata(file_path: Path) -> Dict:
        """Extract metadata from file path."""
        # Path structure: data/ncert-books/Class-10/X-Mathematics/Chapter 1.pdf
        parts = file_path.parts

        metadata = {
            "source": str(file_path),
            "filename": file_path.name,
        }

        # Try to extract class
        for part in parts:
            if "Class" in part or "class" in part:
                # Extract class number
                match = re.search(r'(\d+)', part)
                if match:
                    metadata["class"] = int(match.group(1))
                break

        # Try to extract subject from parent folder
        parent = file_path.parent.name
        if parent.startswith("X-") or parent.startswith("x-"):
            subject = parent[2:]  # Remove "X-" prefix
            # Clean up subject name
            subject = re.sub(r'-?\d+$', '', subject)  # Remove trailing numbers
            metadata["subject"] = subject.replace("-", " ").strip()
        else:
            metadata["subject"] = parent

        # Extract chapter from filename
        chapter_match = re.search(r'Chapter\s*(\d+)', file_path.stem, re.IGNORECASE)
        if chapter_match:
            metadata["chapter"] = int(chapter_match.group(1))
            metadata["chapter_name"] = file_path.stem
        else:
            metadata["chapter_name"] = file_path.stem

        return metadata


class TextChunker:
    """Split text into overlapping chunks."""

    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> List[str]:
        """Split text into chunks with overlap."""
        if not text:
            return []

        # Clean text
        text = self._clean_text(text)

        if len(text) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(text):
            end = start + self.chunk_size

            # Try to break at sentence boundary
            if end < len(text):
                # Look for sentence end within last 100 chars
                search_start = max(end - 100, start)
                last_period = text.rfind('. ', search_start, end)
                last_newline = text.rfind('\n', search_start, end)

                break_point = max(last_period, last_newline)
                if break_point > start:
                    end = break_point + 1

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.overlap

        return chunks

    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove page numbers and headers (common patterns)
        text = re.sub(r'\n\d+\n', '\n', text)
        return text.strip()


class EmbeddingService:
    """Generate embeddings using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")

    def embed(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts."""
        embeddings = self.model.encode(texts, show_progress_bar=True)
        return np.array(embeddings, dtype=np.float32)

    def embed_query(self, query: str) -> np.ndarray:
        """Generate embedding for a single query."""
        embedding = self.model.encode([query])
        return np.array(embedding, dtype=np.float32)


class NCERTIndexer:
    """Main indexer class that ties everything together."""

    def __init__(self, config: Dict = None):
        self.config = config or CONFIG
        self.index_path = Path(self.config["index_path"])
        self.data_path = Path(self.config["data_path"])

        # Initialize components
        self.pdf_loader = PDFLoader()
        self.chunker = TextChunker(
            chunk_size=self.config["chunk_size"],
            overlap=self.config["chunk_overlap"]
        )
        self.embedding_service = EmbeddingService(self.config["embedding_model"])

        # Index storage
        self.index: Optional[faiss.Index] = None
        self.documents: List[Document] = []

        # Ensure directories exist
        self.index_path.mkdir(parents=True, exist_ok=True)

    def index_directory(self, source_path: Path = None, clear: bool = False) -> int:
        """
        Index all PDFs in a directory.

        Args:
            source_path: Path to directory with PDFs (default: data/ncert-books)
            clear: If True, clear existing index first

        Returns:
            Number of documents indexed
        """
        source = source_path or self.data_path

        if clear:
            self.clear_index()
        else:
            self.load_index()

        logger.info(f"Indexing PDFs from: {source}")

        # Find all PDFs
        pdf_files = list(source.rglob("*.pdf"))
        logger.info(f"Found {len(pdf_files)} PDF files")

        if not pdf_files:
            logger.warning("No PDF files found!")
            return 0

        all_documents = []

        for i, pdf_path in enumerate(pdf_files):
            logger.info(f"Processing [{i+1}/{len(pdf_files)}]: {pdf_path.name}")

            # Extract text
            text = self.pdf_loader.load(pdf_path)
            if not text:
                logger.warning(f"No text extracted from {pdf_path.name}")
                continue

            # Get metadata
            metadata = self.pdf_loader.extract_metadata(pdf_path)

            # Chunk text
            chunks = self.chunker.chunk(text)
            logger.info(f"  → {len(chunks)} chunks created")

            # Create documents
            for j, chunk in enumerate(chunks):
                doc_metadata = {
                    **metadata,
                    "chunk_index": j,
                    "total_chunks": len(chunks),
                }
                doc = Document(content=chunk, metadata=doc_metadata)
                all_documents.append(doc)

        if not all_documents:
            logger.warning("No documents to index!")
            return 0

        logger.info(f"Total documents to index: {len(all_documents)}")

        # Generate embeddings
        logger.info("Generating embeddings...")
        texts = [doc.content for doc in all_documents]
        embeddings = self.embedding_service.embed(texts)

        # Create/update FAISS index
        if self.index is None:
            logger.info(f"Creating new FAISS index (dimension: {self.embedding_service.dimension})")
            self.index = faiss.IndexFlatL2(self.embedding_service.dimension)

        # Add to index
        self.index.add(embeddings)
        self.documents.extend(all_documents)

        # Save
        self.save_index()

        logger.info(f"✓ Indexed {len(all_documents)} documents")
        logger.info(f"✓ Total documents in index: {len(self.documents)}")

        return len(all_documents)

    def search(self, query: str, k: int = 5) -> List[Dict]:
        """
        Search the index for relevant documents.

        Args:
            query: Search query
            k: Number of results to return

        Returns:
            List of matching documents with scores
        """
        if self.index is None:
            self.load_index()

        if self.index is None or len(self.documents) == 0:
            logger.warning("Index is empty!")
            return []

        k = min(k, len(self.documents))

        # Generate query embedding
        query_embedding = self.embedding_service.embed_query(query)

        # Search
        distances, indices = self.index.search(query_embedding, k)

        # Prepare results
        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]
                results.append({
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "score": float(distance),  # Lower is better for L2
                })

        return results

    def save_index(self):
        """Save index to disk."""
        index_file = self.index_path / "index.faiss"
        docs_file = self.index_path / "documents.pkl"

        logger.info(f"Saving index to {self.index_path}")

        faiss.write_index(self.index, str(index_file))

        with open(docs_file, "wb") as f:
            pickle.dump(self.documents, f)

        logger.info("✓ Index saved")

    def load_index(self) -> bool:
        """Load index from disk."""
        index_file = self.index_path / "index.faiss"
        docs_file = self.index_path / "documents.pkl"

        if not index_file.exists() or not docs_file.exists():
            logger.info("No existing index found")
            return False

        logger.info(f"Loading index from {self.index_path}")

        self.index = faiss.read_index(str(index_file))

        with open(docs_file, "rb") as f:
            self.documents = pickle.load(f)

        logger.info(f"✓ Loaded index with {len(self.documents)} documents")
        return True

    def clear_index(self):
        """Clear the index."""
        logger.info("Clearing index...")
        self.index = None
        self.documents = []

        index_file = self.index_path / "index.faiss"
        docs_file = self.index_path / "documents.pkl"

        if index_file.exists():
            index_file.unlink()
        if docs_file.exists():
            docs_file.unlink()

        logger.info("✓ Index cleared")

    def get_stats(self) -> Dict:
        """Get index statistics."""
        if self.index is None:
            self.load_index()

        stats = {
            "total_documents": len(self.documents) if self.documents else 0,
            "index_size": self.index.ntotal if self.index else 0,
        }

        # Count by class and subject
        if self.documents:
            by_class = {}
            by_subject = {}

            for doc in self.documents:
                cls = doc.metadata.get("class", "unknown")
                subj = doc.metadata.get("subject", "unknown")

                by_class[cls] = by_class.get(cls, 0) + 1
                by_subject[subj] = by_subject.get(subj, 0) + 1

            stats["by_class"] = by_class
            stats["by_subject"] = by_subject

        return stats


def main():
    parser = argparse.ArgumentParser(description="Index NCERT books into FAISS")
    parser.add_argument("--source", type=str, help="Source directory with PDFs")
    parser.add_argument("--clear", action="store_true", help="Clear existing index")
    parser.add_argument("--search", type=str, help="Test search query")
    parser.add_argument("--stats", action="store_true", help="Show index statistics")

    args = parser.parse_args()

    indexer = NCERTIndexer()

    if args.stats:
        stats = indexer.get_stats()
        print("\n📊 Index Statistics:")
        print(f"  Total documents: {stats['total_documents']}")
        print(f"  Index size: {stats['index_size']}")
        if "by_class" in stats:
            print(f"  By class: {stats['by_class']}")
        if "by_subject" in stats:
            print(f"  By subject: {stats['by_subject']}")
        return

    if args.search:
        results = indexer.search(args.search, k=3)
        print(f"\n🔍 Search results for: '{args.search}'\n")
        for i, result in enumerate(results):
            print(f"Result {i+1} (score: {result['score']:.4f}):")
            print(f"  Class: {result['metadata'].get('class')}")
            print(f"  Subject: {result['metadata'].get('subject')}")
            print(f"  Chapter: {result['metadata'].get('chapter_name')}")
            print(f"  Content: {result['content'][:200]}...")
            print()
        return

    # Index documents
    source = Path(args.source) if args.source else None
    count = indexer.index_directory(source_path=source, clear=args.clear)

    if count > 0:
        print(f"\n✅ Successfully indexed {count} documents!")
        print(f"   Index saved to: {indexer.index_path}")
        print("\n🔍 Test search:")
        results = indexer.search("quadratic equations", k=2)
        for r in results:
            print(f"  → {r['metadata'].get('subject')} Ch.{r['metadata'].get('chapter')}: {r['content'][:100]}...")


if __name__ == "__main__":
    main()
