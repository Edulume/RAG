"""Common utility functions for document processing."""

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}


def get_supported_documents(directory: Path) -> List[Path]:
    """
    Get all supported document files from a directory recursively.
    
    Args:
        directory: Directory to search
        
    Returns:
        List of supported document file paths
    """
    if not directory.exists():
        return []
    
    all_files = list(directory.glob("**/*"))
    return [
        f for f in all_files
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]


def validate_file_extension(filename: str) -> bool:
    """
    Check if file extension is supported.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if supported, False otherwise
    """
    return Path(filename).suffix.lower() in SUPPORTED_EXTENSIONS


async def ingest_documents_to_vector_store(doc_loader, vector_store, source_path: Path, clear_existing: bool = False):
    """
    Ingest documents from a path into the vector store.
    
    Args:
        doc_loader: Document loader instance
        vector_store: Vector store instance
        source_path: Path to file or directory
        clear_existing: Whether to clear existing vector store first
        
    Returns:
        Number of chunks created
    """
    if clear_existing:
        logger.info("Clearing existing vector store...")
        vector_store.clear()
    
    # Process documents
    if source_path.is_file():
        chunks = doc_loader.process_file(source_path)
    else:
        chunks = doc_loader.process_directory(source_path)
    
    if chunks:
        vector_store.add_documents(chunks)
        vector_store.save()
        logger.info(f"Ingested {len(chunks)} chunks")
    
    return len(chunks) if chunks else 0

