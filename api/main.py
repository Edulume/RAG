"""FastAPI application setup."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from keiz.config import settings
from keiz.api.routes import query, documents, health, lume_test, lume, assignment, assessment

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("Starting Slayubs RAG Backend")
    settings.ensure_directories()
    logger.info(f"Using LLM endpoint: {settings.llm_base_url}")
    logger.info(f"Using model: {settings.llm_model}")
    logger.info(f"Dataset directory: {settings.dataset_path}")
    
    # Auto-ingest dataset on startup if enabled
    if settings.auto_ingest_on_startup:
        logger.info("Auto-ingestion enabled, syncing with dataset directory...")
        try:
            from keiz.rag import get_document_loader, get_vector_store
            from keiz.utils import get_supported_documents, ingest_documents_to_vector_store
            
            # Check if dataset has documents
            dataset_docs = get_supported_documents(settings.dataset_path)
            
            if dataset_docs:
                logger.info(f"Found {len(dataset_docs)} documents in dataset/")
                
                # Ingest all documents (clears existing to stay in sync)
                doc_loader = get_document_loader()
                vector_store = get_vector_store()
                chunks_created = await ingest_documents_to_vector_store(
                    doc_loader, vector_store, settings.dataset_path, clear_existing=True
                )
                
                if chunks_created > 0:
                    logger.info(f"✓ Successfully ingested {chunks_created} chunks from {len(dataset_docs)} documents")
                    logger.info("✓ Vector store is now in sync with dataset/")
                else:
                    logger.warning("No chunks created from dataset")
            else:
                logger.info("No documents found in dataset/ directory")
                logger.info("Add PDFs to dataset/ and restart to ingest them")
                
        except Exception as e:
            logger.error(f"Auto-ingestion failed: {e}")
            logger.info("Server will continue without auto-ingestion")

    yield

    # Shutdown
    logger.info("Shutting down Slayubs RAG Backend")


# Create FastAPI app
app = FastAPI(
    title="Lume",
    description="RAG backend using LangChain, FAISS, and Ollama",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"],
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=settings.cors_allow_methods.split(",") if settings.cors_allow_methods != "*" else ["*"],
    allow_headers=settings.cors_allow_headers.split(",") if settings.cors_allow_headers != "*" else ["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(query.router, prefix="/api/v1", tags=["query"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])
app.include_router(lume_test.router, tags=["lume-test"])
app.include_router(lume.router, tags=["lume"])
app.include_router(assignment.router, tags=["lume-assignment"])
app.include_router(assessment.router, tags=["lume-assessment"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Slayubs RAG Backend",
        "version": "0.1.0",
        "docs": "/docs",
    }
