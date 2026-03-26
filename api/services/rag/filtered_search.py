"""
Filtered RAG Search for Lume
Enables querying specific board/class/subject combinations
"""

from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def query_filtered_rag(
    board: str,
    class_num: int,
    subject: str,
    query: str,
    k: int = 10,
    vector_store=None
) -> Dict[str, Any]:
    """
    Query RAG with board/class/subject filtering

    Args:
        board: Board name (e.g., "CBSE", "ICSE")
        class_num: Class number (e.g., 9, 10, 11)
        subject: Subject name (e.g., "English", "Mathematics", "Science")
        query: User's query text
        k: Number of chunks to retrieve
        vector_store: Vector store instance (if None, will import and use global)

    Returns:
        dict with 'context', 'sources', and 'filtered_count'

    Example:
        >>> result = query_filtered_rag("CBSE", 9, "English", "The Fun They Had summary", k=5)
        >>> print(result['context'])
    """
    if vector_store is None:
        from keiz.rag.vector_store import get_vector_store
        vector_store = get_vector_store()

    # Build filter path
    filter_path = f"dataset/{board}/Class_{class_num}/{subject}/"

    logger.info(
        f"Filtered RAG query: board={board}, class={class_num}, "
        f"subject={subject}, filter_path={filter_path}"
    )

    # Retrieve all matching documents (no filter yet - FAISS limitation)
    # We'll filter in post-processing
    all_results = vector_store.similarity_search(
        query=query,
        k=k * 3  # Get more results to account for filtering
    )

    # Filter results by path
    filtered_results = []
    for doc, score in all_results:
        source_path = doc.metadata.get('source', '')

        # Check if source matches our filter path
        if source_path.startswith(filter_path):
            filtered_results.append((doc, score))

            # Stop once we have enough results
            if len(filtered_results) >= k:
                break

    logger.info(
        f"Retrieved {len(filtered_results)} chunks from {filter_path} "
        f"(queried {len(all_results)} total)"
    )

    if not filtered_results:
        logger.warning(f"No documents found for filter path: {filter_path}")
        return {
            "context": "",
            "sources": [],
            "filtered_count": 0,
            "query": query,
            "filter_path": filter_path
        }

    # Build context string
    context_parts = []
    for i, (doc, score) in enumerate(filtered_results, 1):
        metadata = doc.metadata
        filename = metadata.get('filename', 'unknown')
        page = metadata.get('page', 'N/A')

        context_parts.append(
            f"[Source {i}: {filename} - Page {page}]\n{doc.page_content}"
        )

    context = "\n\n---\n\n".join(context_parts)

    # Format sources
    sources = [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "similarity_score": float(score),
            "rank": i
        }
        for i, (doc, score) in enumerate(filtered_results, 1)
    ]

    return {
        "context": context,
        "sources": sources,
        "filtered_count": len(filtered_results),
        "total_queried": len(all_results),
        "query": query,
        "filter_path": filter_path
    }


def get_subject_metadata(board: str, class_num: int, subject: str) -> Optional[Dict[str, Any]]:
    """
    Load metadata.json for a specific subject

    Args:
        board: Board name
        class_num: Class number
        subject: Subject name

    Returns:
        Metadata dict or None if not found
    """
    import json

    metadata_path = Path(f"dataset/{board}/Class_{class_num}/{subject}/metadata.json")

    if not metadata_path.exists():
        logger.warning(f"Metadata not found: {metadata_path}")
        return None

    try:
        with open(metadata_path, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        return metadata
    except Exception as e:
        logger.error(f"Error loading metadata from {metadata_path}: {e}")
        return None


def verify_content_availability(
    board: str,
    class_num: int,
    subject: str,
    chapter_number: Optional[int] = None
) -> Dict[str, Any]:
    """
    Verify if content is available for generation

    Args:
        board: Board name
        class_num: Class number
        subject: Subject name
        chapter_number: Optional chapter number to check

    Returns:
        dict with availability status and details
    """
    metadata = get_subject_metadata(board, class_num, subject)

    if not metadata:
        return {
            "available": False,
            "reason": "Metadata not found",
            "metadata_path": f"dataset/{board}/Class_{class_num}/{subject}/metadata.json"
        }

    # Check if chapter exists (if specified)
    if chapter_number is not None:
        books = metadata.get('books', [])
        chapter_found = False

        for book in books:
            chapters = book.get('chapters', [])
            for chapter in chapters:
                if chapter.get('number') == chapter_number:
                    chapter_found = True
                    return {
                        "available": True,
                        "book": book.get('name'),
                        "chapter": chapter,
                        "metadata": metadata
                    }

        if not chapter_found:
            return {
                "available": False,
                "reason": f"Chapter {chapter_number} not found in metadata",
                "available_chapters": [
                    ch.get('number') for book in books for ch in book.get('chapters', [])
                ]
            }

    # No specific chapter requested, just check subject exists
    return {
        "available": True,
        "metadata": metadata,
        "books": metadata.get('books', [])
    }


def test_filtered_search():
    """
    Test function to verify filtered search works
    """
    print("=" * 60)
    print("FILTERED RAG SEARCH TEST")
    print("=" * 60)
    print()

    # Test 1: English query
    print("Test 1: CBSE Class 9 English")
    print("-" * 60)
    result = query_filtered_rag(
        board="CBSE",
        class_num=9,
        subject="English",
        query="The Fun They Had story summary",
        k=3
    )
    print(f"Found {result['filtered_count']} chunks")
    print(f"Filter path: {result['filter_path']}")
    if result['sources']:
        print(f"First source: {result['sources'][0]['metadata'].get('filename')}")
    print()

    # Test 2: Mathematics query
    print("Test 2: CBSE Class 9 Mathematics")
    print("-" * 60)
    result = query_filtered_rag(
        board="CBSE",
        class_num=9,
        subject="Mathematics",
        query="Pythagoras theorem proof",
        k=3
    )
    print(f"Found {result['filtered_count']} chunks")
    print(f"Filter path: {result['filter_path']}")
    if result['sources']:
        print(f"First source: {result['sources'][0]['metadata'].get('filename')}")
    print()

    # Test 3: Science query
    print("Test 3: CBSE Class 9 Science")
    print("-" * 60)
    result = query_filtered_rag(
        board="CBSE",
        class_num=9,
        subject="Science",
        query="What is matter and its properties",
        k=3
    )
    print(f"Found {result['filtered_count']} chunks")
    print(f"Filter path: {result['filter_path']}")
    if result['sources']:
        print(f"First source: {result['sources'][0]['metadata'].get('filename')}")
    print()

    # Test 4: Metadata check
    print("Test 4: Metadata Retrieval")
    print("-" * 60)
    metadata = get_subject_metadata("CBSE", 9, "English")
    if metadata:
        print(f"Subject: {metadata['subject']}")
        print(f"Board: {metadata['board']}")
        print(f"Books: {len(metadata['books'])}")
        print(f"First book: {metadata['books'][0]['name']}")
        print(f"Chapters: {len(metadata['books'][0]['chapters'])}")
    print()

    # Test 5: Content availability
    print("Test 5: Content Availability Check")
    print("-" * 60)
    availability = verify_content_availability("CBSE", 9, "English", chapter_number=1)
    print(f"Available: {availability['available']}")
    if availability['available']:
        print(f"Chapter: {availability['chapter']['title']}")
    print()

    print("=" * 60)
    print("ALL TESTS COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    test_filtered_search()
