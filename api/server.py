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
    "indexes_root": PROJECT_ROOT / "indexes",
    "questions_csv_path": PROJECT_ROOT / "data" / "question-bank.csv",
    "default_board": "cbse",
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
# RAG Service (per-board)
# ============================================

class RAGService:
    """Service for RAG operations on a specific board."""

    def __init__(self, board: str, index_path: Path, model: SentenceTransformer):
        self.board = board.lower()
        self.index_path = index_path
        self.model = model

        self.index = None
        self.documents = []
        self._load_index()

    def _load_index(self):
        """Load FAISS index and documents for this board."""
        index_file = self.index_path / "index.faiss"
        docs_file = self.index_path / "documents.pkl"

        if not index_file.exists() or not docs_file.exists():
            logger.warning(f"Index not found for board '{self.board}' at {self.index_path}")
            return

        logger.info(f"Loading index for {self.board.upper()} from {self.index_path}")
        self.index = faiss.read_index(str(index_file))

        with open(docs_file, "rb") as f:
            self.documents = pickle.load(f)

        logger.info(f"Loaded {len(self.documents)} documents for {self.board.upper()}")

    def is_loaded(self) -> bool:
        """Check if index is loaded."""
        return self.index is not None and len(self.documents) > 0

    def search(self, query: str, filters: Dict = None, limit: int = 5) -> List[Dict]:
        """Search content for this board."""
        if not self.is_loaded():
            return []

        # Generate query embedding
        query_embedding = self.model.encode([query])
        query_array = np.array(query_embedding, dtype=np.float32)

        # Search more than needed for filtering
        search_k = min(limit * 3, len(self.documents))
        distances, indices = self.index.search(query_array, search_k)

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx < len(self.documents):
                doc = self.documents[idx]

                # Apply filters
                if filters:
                    if "class" in filters and filters["class"]:
                        doc_class = doc.metadata.get("class")
                        filter_class = filters["class"]
                        # Compare as integers to handle type mismatches
                        if doc_class is not None and int(doc_class) != int(filter_class):
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

    def get_stats(self) -> Dict:
        """Get index statistics for this board."""
        stats = {
            "board": self.board.upper(),
            "documents": len(self.documents),
            "indexed": self.is_loaded(),
            "by_class": {},
            "by_subject": {},
        }

        for doc in self.documents:
            cls = str(doc.metadata.get("class", "unknown"))
            subj = doc.metadata.get("subject", "unknown")
            stats["by_class"][cls] = stats["by_class"].get(cls, 0) + 1
            stats["by_subject"][subj] = stats["by_subject"].get(subj, 0) + 1

        return stats


# ============================================
# Board Registry
# ============================================

class BoardRegistry:
    """Registry that manages multiple board services."""

    def __init__(self):
        self.boards: Dict[str, RAGService] = {}
        self.model: Optional[SentenceTransformer] = None
        self.questions: List[Dict] = []
        self._initialized = False

    def initialize(self):
        """Initialize the registry (load embedding model and questions)."""
        if self._initialized:
            return

        logger.info("Initializing Board Registry...")

        # Load embedding model (shared across all boards)
        logger.info(f"Loading embedding model: {CONFIG['embedding_model']}")
        self.model = SentenceTransformer(CONFIG["embedding_model"])

        # Load questions
        self._load_questions()

        # Pre-load default board
        self.get_board(CONFIG["default_board"])

        self._initialized = True
        logger.info("Board Registry initialized")

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

    def get_board(self, board: str) -> RAGService:
        """Get or create a RAGService for the specified board."""
        board = board.lower()

        if board not in self.boards:
            index_path = CONFIG["indexes_root"] / board
            if not index_path.exists():
                raise HTTPException(status_code=404, detail=f"Board '{board}' not found")

            self.boards[board] = RAGService(board, index_path, self.model)

        return self.boards[board]

    def list_boards(self) -> List[str]:
        """List all available boards."""
        indexes_root = CONFIG["indexes_root"]
        if not indexes_root.exists():
            return []

        return [p.name for p in indexes_root.iterdir()
                if p.is_dir() and (p / "index.faiss").exists()]

    def query_questions(self, board: str, filters: QuestionFilters, limit: int = 10, offset: int = 0) -> tuple:
        """Query questions with filters, optionally filtered by board."""
        filtered = self.questions

        # Filter by board if specified
        board = board.lower()
        filtered = [q for q in filtered if q.get("board", "cbse").lower() == board]

        # Apply other filters
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
                    "board": q.get("board", "cbse"),
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

    def get_all_stats(self) -> Dict:
        """Get combined statistics."""
        stats = {
            "boards": self.list_boards(),
            "total_questions": len(self.questions),
            "loaded_boards": list(self.boards.keys()),
        }
        return stats

# ============================================
# FastAPI App
# ============================================

app = FastAPI(
    title="Edulume RAG API",
    description="Multi-Board NCERT Content Search & Question Bank API",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global registry instance
registry: Optional[BoardRegistry] = None

@app.on_event("startup")
async def startup():
    global registry
    registry = BoardRegistry()
    registry.initialize()

# ============================================
# Routes - Board Specific
# ============================================

@app.get("/boards")
async def list_boards():
    """List all available boards."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {
        "boards": registry.list_boards(),
        "default": CONFIG["default_board"],
    }

@app.get("/{board}/health")
async def board_health(board: str):
    """Health check for specific board."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        service = registry.get_board(board)
        return {
            "status": "healthy",
            "board": board.upper(),
            "indexed": service.is_loaded(),
            "documents": len(service.documents),
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/{board}/stats")
async def board_stats(board: str):
    """Get statistics for specific board."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    service = registry.get_board(board)
    stats = service.get_stats()
    stats["questions_count"] = len([q for q in registry.questions if q.get("board", "cbse").lower() == board.lower()])
    return stats

@app.post("/{board}/search", response_model=SearchResponse)
async def board_search(board: str, request: SearchRequest):
    """
    Search content for specific board.

    Example:
    ```json
    {
        "query": "photosynthesis in plants",
        "filters": {"class": 10, "subject": "Science"},
        "limit": 5
    }
    ```
    """
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    service = registry.get_board(board)
    results = service.search(
        query=request.query,
        filters=request.filters,
        limit=request.limit
    )

    return SearchResponse(
        query=request.query,
        results=[SearchResult(**r) for r in results],
        total_found=len(results)
    )

@app.post("/{board}/questions", response_model=QuestionsResponse)
async def board_questions(board: str, request: QuestionsRequest):
    """
    Query questions for specific board.

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
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    questions, total = registry.query_questions(
        board=board,
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

# ============================================
# Routes - Legacy (backward compatibility)
# ============================================

@app.get("/")
async def root():
    """API info."""
    return {
        "name": "Edulume RAG API",
        "version": "2.0.0",
        "boards": registry.list_boards() if registry else [],
        "default_board": CONFIG["default_board"],
        "endpoints": {
            "boards": "GET /boards",
            "board_health": "GET /{board}/health",
            "board_stats": "GET /{board}/stats",
            "board_search": "POST /{board}/search",
            "board_questions": "POST /{board}/questions",
            "legacy_search": "POST /search (defaults to cbse)",
            "legacy_questions": "POST /questions (defaults to cbse)",
            "legacy_health": "GET /health",
            "legacy_stats": "GET /stats",
        }
    }

@app.get("/health")
async def health():
    """Health check (legacy - uses default board)."""
    if not registry:
        return {"status": "unhealthy", "error": "Service not initialized"}

    default_board = CONFIG["default_board"]
    try:
        service = registry.get_board(default_board)
        return {
            "status": "healthy",
            "board": default_board.upper(),
            "indexed": service.is_loaded(),
            "questions_loaded": len(registry.questions) > 0,
        }
    except Exception:
        return {
            "status": "healthy",
            "board": default_board.upper(),
            "indexed": False,
            "questions_loaded": len(registry.questions) > 0,
        }

@app.get("/stats")
async def get_stats():
    """Get statistics (legacy - uses default board)."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    default_board = CONFIG["default_board"]
    service = registry.get_board(default_board)
    stats = service.get_stats()

    return {
        "ncert_documents": stats["documents"],
        "questions_count": len(registry.questions),
        "by_class": stats["by_class"],
        "by_subject": stats["by_subject"],
    }

@app.post("/search", response_model=SearchResponse)
async def search_ncert(request: SearchRequest):
    """Search NCERT content (legacy - uses default board)."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    default_board = CONFIG["default_board"]
    service = registry.get_board(default_board)
    results = service.search(
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
    """Query questions (legacy - uses default board)."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    default_board = CONFIG["default_board"]
    questions, total = registry.query_questions(
        board=default_board,
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
async def get_subjects(board: Optional[str] = None):
    """Get available subjects in question bank."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    board = board or CONFIG["default_board"]
    subjects = set()
    for q in registry.questions:
        if q.get("board", "cbse").lower() != board.lower():
            continue
        if q.get("subject"):
            subjects.add(q["subject"])

    return {"board": board.upper(), "subjects": sorted(list(subjects))}

@app.get("/questions/topics")
async def get_topics(subject: Optional[str] = None, board: Optional[str] = None):
    """Get available topics, optionally filtered by subject and board."""
    if not registry:
        raise HTTPException(status_code=503, detail="Service not initialized")

    board = board or CONFIG["default_board"]
    topics = set()
    for q in registry.questions:
        if q.get("board", "cbse").lower() != board.lower():
            continue
        if subject and subject.lower() not in q.get("subject", "").lower():
            continue
        if q.get("topic"):
            topics.add(q["topic"])

    return {"board": board.upper(), "topics": sorted(list(topics)), "count": len(topics)}

# ============================================
# Main
# ============================================

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 6969))

    print(f"""
╔═══════════════════════════════════════════════════════════╗
║           Edulume RAG API Server v2.0                     ║
╠═══════════════════════════════════════════════════════════╣
║  Board-Specific Endpoints:                                ║
║    GET  /boards               - List available boards     ║
║    GET  /{{board}}/health       - Board health check        ║
║    GET  /{{board}}/stats        - Board statistics          ║
║    POST /{{board}}/search       - Search board content      ║
║    POST /{{board}}/questions    - Query board questions     ║
╠═══════════════════════════════════════════════════════════╣
║  Legacy Endpoints (defaults to CBSE):                     ║
║    POST /search, /questions   GET /health, /stats         ║
╠═══════════════════════════════════════════════════════════╣
║  Server: http://localhost:{port}                            ║
║  Docs:   http://localhost:{port}/docs                       ║
╚═══════════════════════════════════════════════════════════╝
    """)

    uvicorn.run(app, host="0.0.0.0", port=port)
