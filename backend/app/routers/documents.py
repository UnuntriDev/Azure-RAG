import asyncio
import logging
import uuid

from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fastapi import Request
from app.auth import auth_deps, get_current_user
from app.config import Settings, get_settings
from app.rate_limit import ANALYZE_LIMIT, UPLOAD_LIMIT, limiter
from app.db.models import Document
from app.db.session import get_db
from app.dependencies import get_blob_service, get_openai_client, get_search_client
from app.schemas.analysis import DocumentAnalysis
from app.pagination import apply_cursor, encode_cursor
from app.schemas.documents import DocumentRead, DocumentUploadResponse
from app.schemas.pagination import CursorPage
from app.services.generation.analyzer import analyze_document
from openai import AsyncAzureOpenAI
from app.services.ingestion.indexer import ingest_document
from app.worker import enqueue_ingestion
from app.services.ingestion.parsers import validate_upload
from app.services.storage.blob import blob_name_for, delete_pdf, upload_pdf
from app.services.cache import invalidate_search_cache
from app.services.storage.search import delete_document_chunks, fetch_document_chunks

router = APIRouter(prefix="/api/documents", tags=["documents"], dependencies=auth_deps())


def _own(doc: Document, user_id: str | None) -> bool:
    """True when caller owns the document (or auth is off / row predates auth)."""
    if not user_id or not doc.user_id:
        return True
    return doc.user_id == user_id


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
@limiter.limit(UPLOAD_LIMIT)
async def upload_document(
    request: Request,
    background: BackgroundTasks,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    blob: BlobServiceClient = Depends(get_blob_service),
    settings: Settings = Depends(get_settings),
    user_id: str | None = Depends(get_current_user),
) -> DocumentUploadResponse:
    filename = file.filename or ""

    max_bytes = settings.max_upload_mb * 1024 * 1024
    too_large = f"File exceeds {settings.max_upload_mb} MB limit"
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(status_code=413, detail=too_large)

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail=too_large)
    error = validate_upload(filename, data)
    if error:
        raise HTTPException(status_code=400, detail=error)

    # id up-front so blob name and DB row share the same uuid
    doc_id = uuid.uuid4()
    url = await upload_pdf(blob, settings.azure_storage_container, blob_name_for(doc_id, filename), data)

    db.add(Document(id=doc_id, filename=filename, blob_url=url, status="pending", user_id=user_id))
    await db.commit()

    enqueued = await enqueue_ingestion(doc_id)
    if not enqueued:
        background.add_task(ingest_document, doc_id)
    return DocumentUploadResponse(id=doc_id, filename=filename, status="pending")


@router.get("", response_model=CursorPage[DocumentRead])
async def list_documents(
    cursor: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
) -> dict:
    q = select(Document)
    if user_id:
        q = q.where(Document.user_id == user_id)
    q = apply_cursor(q, cursor=cursor, sort_column=Document.created_at, id_column=Document.id, limit=limit + 1)
    result = await db.execute(q)
    rows = list(result.scalars().all())

    next_cursor = None
    if len(rows) > limit:
        rows = rows[:limit]
        last = rows[-1]
        next_cursor = encode_cursor(last.created_at, last.id)
    return {"items": rows, "next_cursor": next_cursor}


@router.get("/{document_id}", response_model=DocumentRead)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    user_id: str | None = Depends(get_current_user),
) -> Document:
    doc = await db.get(Document, document_id)
    if doc is None or not _own(doc, user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.post("/{document_id}/analyze", response_model=DocumentAnalysis)
@limiter.limit(ANALYZE_LIMIT)
async def analyze(
    request: Request,
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    search: SearchClient = Depends(get_search_client),
    openai_client: AsyncAzureOpenAI = Depends(get_openai_client),
    settings: Settings = Depends(get_settings),
    user_id: str | None = Depends(get_current_user),
) -> DocumentAnalysis:
    """Structured-output analysis of one document (summary, key points, entities, questions)."""
    doc = await db.get(Document, document_id)
    if doc is None or not _own(doc, user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    if doc.status != "indexed":
        raise HTTPException(status_code=409, detail="Dokument nie jest jeszcze zaindeksowany.")

    chunks = await fetch_document_chunks(search, str(document_id))
    if not chunks:
        raise HTTPException(status_code=404, detail="Brak treści dokumentu w indeksie.")

    return await analyze_document(
        openai_client,
        settings.azure_openai_chat_deployment,
        doc.filename,
        [c["content"] for c in chunks],
    )


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    blob: BlobServiceClient = Depends(get_blob_service),
    search: SearchClient = Depends(get_search_client),
    settings: Settings = Depends(get_settings),
    user_id: str | None = Depends(get_current_user),
) -> None:
    doc = await db.get(Document, document_id)
    if doc is None or not _own(doc, user_id):
        raise HTTPException(status_code=404, detail="Document not found")
    # Blocks race: deleting during ingest would orphan chunks in AI Search.
    if doc.status in ("pending", "processing"):
        raise HTTPException(
            status_code=409,
            detail="Document is still being processed. Try again once it is indexed or failed.",
        )
    chunk_result, blob_result = await asyncio.gather(
        delete_document_chunks(search, str(document_id), doc.chunk_count),
        delete_pdf(blob, settings.azure_storage_container, blob_name_for(document_id, doc.filename)),
        return_exceptions=True,
    )
    errors = [r for r in (chunk_result, blob_result) if isinstance(r, Exception)]
    if errors:
        logging.getLogger(__name__).error("Partial delete failure for %s: %s", document_id, errors)
        raise HTTPException(status_code=502, detail="Nie udało się w pełni usunąć zasobów — spróbuj ponownie.")
    await db.delete(doc)
    await db.commit()
    await invalidate_search_cache()
