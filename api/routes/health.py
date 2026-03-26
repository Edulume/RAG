"""Health check endpoints."""

import logging
from fastapi import APIRouter

from keiz.api.models import HealthResponse
from keiz.rag import get_vector_store

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """Basic health check endpoint."""
    try:
        vector_store = get_vector_store()
        stats = vector_store.get_stats()

        return HealthResponse(
            status="healthy",
            vector_store_loaded=stats["index_size"] > 0,
            total_documents=stats["total_documents"],
        )

    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="unhealthy",
            vector_store_loaded=False,
            total_documents=0,
        )
