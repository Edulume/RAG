"""
Lume Test Endpoint - Verify filtered RAG works
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from keiz.rag.filtered_search import query_filtered_rag, get_subject_metadata

router = APIRouter(prefix="/api/v1/lume-test", tags=["lume-test"])


class FilteredQueryRequest(BaseModel):
    board: str = "CBSE"
    class_num: int = 9
    subject: str  # English, Mathematics, Science, etc.
    query: str
    k: Optional[int] = 5


@router.post("/filtered-query")
async def test_filtered_query(request: FilteredQueryRequest):
    """
    Test filtered RAG query

    Example:
        POST /api/v1/lume-test/filtered-query
        {
            "board": "CBSE",
            "class_num": 9,
            "subject": "English",
            "query": "The Fun They Had summary",
            "k": 3
        }
    """
    try:
        result = query_filtered_rag(
            board=request.board,
            class_num=request.class_num,
            subject=request.subject,
            query=request.query,
            k=request.k
        )

        return {
            "success": True,
            "filter_path": result['filter_path'],
            "chunks_found": result['filtered_count'],
            "total_queried": result.get('total_queried', 0),
            "sources": [
                {
                    "filename": s['metadata'].get('filename'),
                    "page": s['metadata'].get('page'),
                    "score": s.get('similarity_score'),
                    "content_preview": s['content'][:200] + "..."
                }
                for s in result['sources']
            ],
            "context_length": len(result['context'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metadata/{board}/{class_num}/{subject}")
async def get_metadata(board: str, class_num: int, subject: str):
    """
    Get metadata for a subject

    Example:
        GET /api/v1/lume-test/metadata/CBSE/9/English
    """
    metadata = get_subject_metadata(board, class_num, subject)

    if not metadata:
        raise HTTPException(
            status_code=404,
            detail=f"Metadata not found for {board}/Class_{class_num}/{subject}"
        )

    return {
        "success": True,
        "metadata": metadata
    }
