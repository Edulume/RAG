#!/usr/bin/env python3
"""
Edulume RAG API Server
Simple FastAPI server for NCERT content search and question queries.

Usage:
    python api/server.py
    # or
    uvicorn api.server:app --reload --port 6969
"""

import csv
import logging
import os
import pickle
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Document class must match the one used during indexing
class Document:
    """Simple document class to hold content and metadata."""
    def __init__(self, content: str, metadata: Dict):
        self.content = content
        self.metadata = metadata

# Patch the module so pickle can find Document class
import sys
sys.modules['__main__'].Document = Document

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# Configuration
# ============================================

CONFIG = {
    "embedding_model": "all-MiniLM-L6-v2",
    "ncert_index_path": PROJECT_ROOT / "indexes" / "ncert-content",
    "questions_csv_path": PROJECT_ROOT / "data" / "question-bank.csv",
}

# ============================================
# Pydantic Models
# ============================================

class SearchRequest(BaseModel):
    query: str = Field(..., description="Search query", min_length=2)
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Optional filters (class, subject)")
    limit: int = Field(default=5, ge=1, le=20, description="Number of results")

class SearchResult(BaseModel):
    content: str
    metadata: Dict[str, Any]
    score: float

class SearchResponse(BaseModel):
    query: str
    results: List[SearchResult]
    total_found: int

class QuestionFilters(BaseModel):
    class_level: Optional[int] = Field(default=None, alias="class", ge=6, le=12)
    subject: Optional[str] = None
    chapter: Optional[str] = None
    topic: Optional[str] = None
    vertical_level: Optional[List[int]] = Field(default=None, description="V levels 0-8")
    horizontal_level: Optional[List[int]] = Field(default=None, description="H levels 1-8")
    question_type: Optional[List[str]] = Field(default=None, description="MCQ, Short, Long, etc.")

    class Config:
        populate_by_name = True

class QuestionsRequest(BaseModel):
    filters: QuestionFilters
    limit: int = Field(default=10, ge=1, le=50)
    offset: int = Field(default=0, ge=0)

class Question(BaseModel):
    question_id: str
    question_text: str
    correct_answer: Optional[str] = None
    solution: Optional[str] = None
    metadata: Dict[str, Any]

class QuestionsResponse(BaseModel):
    questions: List[Question]
    total_found: int
    limit: int
    offset: int

class StatsResponse(BaseModel):
    ncert_documents: int
    questions_count: int
    by_class: Dict[str, int]
    by_subject: Dict[str, int]

# ============================================
# RAG Service
# ============================================

class RAGService:
    """Service for RAG operations."""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        logger.info("Initializing RAG Service...")

        # Load embedding model
        logger.info(f"Loading embedding model: {CONFIG['embedding_model']}")
        self.model = SentenceTransformer(CONFIG["embedding_model"])

        # Load NCERT index
        self.ncert_index = None
        self.ncert_documents = []
        self._load_ncert_index()

        # Load questions CSV
        self.questions = []
        self._load_questions()

        self._initialized = True
        logger.info("RAG Service initialized")

    def _load_ncert_index(self):
        """Load FAISS index and documents."""
        index_path = CONFIG["ncert_index_path"]
        index_file = index_path / "index.faiss"
        docs_file = index_path / "documents.pkl"

        if not index_file.exists() or not docs_file.exists():
            logger.warning("NCERT index not found. Run indexing first.")
            return

        logger.info(f"Loading NCERT index from {index_path}")
        self.ncert_index = faiss.read_index(str(index_file))

        with open(docs_file, "rb") as f:
            self.ncert_documents = pickle.load(f)

        logger.info(f"Loaded {len(self.ncert_documents)} NCERT documents")

    def _load_questions(self):
        """Load questions from CSV."""
        csv_path = CONFIG["questions_csv_path"]

        if not csv_path.exists():
            logger.warning(f"Questions CSV not found at {csv_path}")
            return

        logger.info(f"Loading questions from {csv_path}")

        with open(csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            self.questions = list(reader)

        logger.info(f"Loaded {len(self.questions)} questions")

    def search_ncert(self, query: str, filters: Dict = None, limit: int = 5) -> List[Dict]:
        """Search NCERT content."""
        if self.ncert_index is None or len(self.ncert_documents) == 0:
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query])
        query_array = np.array(query_embedding, dtype=np.float32)

        # Search more than needed for filtering
        search_k = min(limit * 3, len(self.ncert_documents))
        distances, indices = self.ncert_index.search(query_array, search_k)

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.ncert_documents):
                doc = self.ncert_documents[idx]

                # Apply filters
                if filters:
                    if "class" in filters and filters["class"]:
                        if doc.metadata.get("class") != filters["class"]:
                            continue
                    if "subject" in filters and filters["subject"]:
                        if filters["subject"].lower() not in doc.metadata.get("subject", "").lower():
                            continue

                results.append({
                    "content": doc.content,
                    "metadata": doc.metadata,
                    "score": float(distance),
                })

                if len(results) >= limit:
                    break

        return results

    def query_questions(self, filters: QuestionFilters, limit: int = 10, offset: int = 0) -> tuple:
        """Query questions with filters."""
        filtered = self.questions

        # Apply filters
        if filters.class_level:
            filtered = [q for q in filtered if str(q.get("class", "")) == str(filters.class_level)]

        if filters.subject:
            filtered = [q for q in filtered if filters.subject.lower() in q.get("subject", "").lower()]

        if filters.chapter:
            filtered = [q for q in filtered if filters.chapter.lower() in q.get("chapter", "").lower()]

        if filters.topic:
            filtered = [q for q in filtered if filters.topic.lower() in q.get("topic", "").lower()]

        if filters.vertical_level:
            filtered = [q for q in filtered if q.get("vertical_level", "") and int(q.get("vertical_level", -1)) in filters.vertical_level]

        if filters.horizontal_level:
            filtered = [q for q in filtered if q.get("horizontal_level", "") and int(q.get("horizontal_level", -1)) in filters.horizontal_level]

        if filters.question_type:
            types_lower = [t.lower() for t in filters.question_type]
            filtered = [q for q in filtered if q.get("question_type", "").lower() in types_lower]

        total = len(filtered)

        # Apply pagination
        filtered = filtered[offset:offset + limit]

        # Format results
        results = []
        for q in filtered:
            results.append({
                "question_id": q.get("question_id", ""),
                "question_text": q.get("question_text", ""),
                "correct_answer": q.get("correct_answer", ""),
                "solution": q.get("solution", ""),
                "metadata": {
                    "source_book": q.get("source_book", ""),
                    "class": q.get("class", ""),
                    "subject": q.get("subject", ""),
                    "chapter": q.get("chapter", ""),
                    "topic": q.get("topic", ""),
                    "skill": q.get("skill", ""),
                    "question_type": q.get("question_type", ""),
                    "vertical_level": q.get("vertical_level", ""),
                    "horizontal_level": q.get("horizontal_level", ""),
                    "cognitive_type": q.get("cognitive_type", ""),
                    "marks": q.get("marks", ""),
                    "time_expected": q.get("time_expected", ""),
                }
            })

        return results, total

    def get_stats(self) -> Dict:
        """Get index statistics."""
        stats = {
            "ncert_documents": len(self.ncert_documents),
            "questions_count": len(self.questions),
            "by_class": {},
            "by_subject": {},
        }

        # NCERT stats
        for doc in self.ncert_documents:
            cls = str(doc.metadata.get("class", "unknown"))
            subj = doc.metadata.get("subject", "unknown")
            stats["by_class"][cls] = stats["by_class"].get(cls, 0) + 1
            stats["by_subject"][subj] = stats["by_subject"].get(subj, 0) + 1

        return stats

# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Edulume RAG API",
    description="NCERT Content Search & Question Bank API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global service instance
rag_service: Optional[RAGService] = None

@app.on_event("startup")
async def startup():
    global rag_service
    rag_service = RAGService()

# ============================================
# Routes
# ============================================

@app.get("/")
async def root():
    """API info."""
    return {
        "name": "Edulume RAG API",
        "version": "1.0.0",
        "endpoints": {
            "search": "POST /search",
            "questions": "POST /questions",
            "stats": "GET /stats",
            "health": "GET /health",
        }
    }

@app.get("/health")
async def health():
    """Health check."""
    return {
        "status": "healthy",
        "ncert_indexed": rag_service.ncert_index is not None if rag_service else False,
        "questions_loaded": len(rag_service.questions) > 0 if rag_service else False,
    }

@app.get("/stats", response_model=StatsResponse)
async def get_stats():
    """Get index statistics."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return rag_service.get_stats()

@app.post("/search", response_model=SearchResponse)
async def search_ncert(request: SearchRequest):
    """
    Search NCERT content.

    Example:
    ```json
    {
        "query": "photosynthesis in plants",
        "filters": {"class": 10, "subject": "Science"},
        "limit": 5
    }
    ```
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    results = rag_service.search_ncert(
        query=request.query,
        filters=request.filters,
        limit=request.limit
    )

    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results],
        total_found=len(results)
    )

@app.post("/questions", response_model=QuestionsResponse)
async def get_questions(request: QuestionsRequest):
    """
    Query questions from question bank.

    Example:
    ```json
    {
        "filters": {
            "class": 10,
            "subject": "Mathematics",
            "topic": "Quadratic",
            "vertical_level": [2, 3, 4],
            "question_type": ["MCQ"]
        },
        "limit": 10
    }
    ```
    """
    if not rag_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    questions, total = rag_service.query_questions(
        filters=request.filters,
        limit=request.limit,
        offset=request.offset
    )

    return QuestionsResponse(
        questions=[Question(**q) for q in questions],
        total_found=total,
        limit=request.limit,
        offset=request.offset
    )

@app.get("/questions/subjects")
async def get_subjects():
    """Get available subjects in question bank."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    subjects = set()
    for q in rag_service.questions:
        if q.get("subject"):
            subjects.add(q["subject"])

    return {"subjects": sorted(list(subjects))}

@app.get("/questions/topics")
async def get_topics(subject: Optional[str] = None):
    """Get available topics, optionally filtered by subject."""
    if not rag_service:
        raise HTTPException(status_code=503, detail="Service not initialized")

    topics = set()
    for q in rag_service.questions:
        if subject and subject.lower() not in q.get("subject", "").lower():
            continue
        if q.get("topic"):
            topics.add(q["topic"])

    return {"topics": sorted(list(topics)), "count": len(topics)}

# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 6969))

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║           Edulume RAG API Server                          ║
╠═══════════════════════════════════════════════════════════╣
║  Endpoints:                                               ║
║    POST /search      - Search NCERT content               ║
║    POST /questions   - Query question bank                ║
║    GET  /stats       - Index statistics                   ║
║    GET  /health      - Health check                       ║
╠═══════════════════════════════════════════════════════════╣
║  Server: http://localhost:{port}                            ║
║  Docs:   http://localhost:{port}/docs                       ║
╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host="0.0.0.0", port=port)
