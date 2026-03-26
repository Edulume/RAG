"""Query endpoints for RAG."""

import logging
from fastapi import APIRouter, HTTPException

from keiz.api.models import QueryRequest, QueryResponse
from keiz.rag import get_rag_chain

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query_rag(request: QueryRequest):
    """
    Query the RAG system with a question.

    Args:
        request: Query request with question and parameters

    Returns:
        Answer with optional source documents
    """
    try:
        rag_chain = get_rag_chain()
        result = await rag_chain.aquery(
            question=request.query,
            k=request.k,
            return_sources=request.return_sources,
        )

        return QueryResponse(**result)

    except Exception as e:
        logger.error(f"Error processing query: {e}")
        raise HTTPException(status_code=500, detail=str(e))
