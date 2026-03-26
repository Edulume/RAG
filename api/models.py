"""Pydantic models for API requests and responses."""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for RAG queries."""

    query: str = Field(..., description="The question to ask")
    k: Optional[int] = Field(None, description="Number of documents to retrieve")
    return_sources: bool = Field(True, description="Whether to return source documents")


class Source(BaseModel):
    """Source document information."""

    content: str
    metadata: Dict[str, Any]
    score: float


class QueryResponse(BaseModel):
    """Response model for RAG queries."""

    answer: str
    sources: List[Source] = []


class UploadResponse(BaseModel):
    """Response model for document uploads."""

    message: str
    filename: str
    chunks_created: int


class HealthResponse(BaseModel):
    """Response model for health checks."""

    status: str
    vector_store_loaded: bool
    total_documents: int


class ErrorResponse(BaseModel):
    """Response model for errors."""

    error: str
    detail: Optional[str] = None
