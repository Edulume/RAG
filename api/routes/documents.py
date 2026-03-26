"""Document management endpoints."""

import logging
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException
import aiofiles

from keiz.api.models import UploadResponse
from keiz.config import settings
from keiz.rag import get_document_loader, get_vector_store
from keiz.utils import validate_file_extension, ingest_documents_to_vector_store, SUPPORTED_EXTENSIONS

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and ingest a document into the RAG system.

    Args:
        file: Document file to upload

    Returns:
        Upload confirmation with chunk count
    """
    try:
        # Validate file type
        if not validate_file_extension(file.filename):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Allowed: {SUPPORTED_EXTENSIONS}",
            )

        # Save file
        settings.ensure_directories()
        file_path = settings.documents_path / file.filename

        async with aiofiles.open(file_path, "wb") as f:
            content = await file.read()
            await f.write(content)

        logger.info(f"Saved file: {file_path}")

        # Process and ingest document
        doc_loader = get_document_loader()
        vector_store = get_vector_store()
        chunks_created = await ingest_documents_to_vector_store(
            doc_loader, vector_store, file_path, clear_existing=False
        )

        logger.info(f"Processed {chunks_created} chunks from {file.filename}")

        return UploadResponse(
            message="Document uploaded and processed successfully",
            filename=file.filename,
            chunks_created=chunks_created,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ingest-dataset")
async def ingest_dataset():
    """
    Ingest all documents from the dataset directory.

    Returns:
        Summary of ingestion
    """
    try:
        settings.ensure_directories()

        if not settings.dataset_path.exists():
            raise HTTPException(
                status_code=404,
                detail="Dataset directory not found",
            )

        # Process and ingest all documents
        doc_loader = get_document_loader()
        vector_store = get_vector_store()
        chunks_created = await ingest_documents_to_vector_store(
            doc_loader, vector_store, settings.dataset_path, clear_existing=True
        )

        if chunks_created == 0:
            return {
                "message": "No documents found in dataset directory",
                "chunks_created": 0,
            }

        logger.info(f"Ingested {chunks_created} chunks from dataset directory")

        return {
            "message": "Dataset ingested successfully",
            "chunks_created": chunks_created,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting dataset: {e}")
        raise HTTPException(status_code=500, detail=str(e))
