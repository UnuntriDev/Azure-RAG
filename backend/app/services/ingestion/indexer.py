"""Ingestion orchestration: parse → chunk → embed → index."""

import uuid
from itertools import batched

import structlog

from app.config import get_settings
from app.services.cache import invalidate_search_cache
from app.db.models import Document
from app.db.session import SessionLocal
from app.services.ingestion.chunker import chunk_segments
from app.services.ingestion.embedder import embed_texts, make_openai_client
from app.services.ingestion.parsers import parse_document
from app.services.storage.blob import blob_name_for, download_pdf, make_blob_service_client
from app.services.storage.search import (
    ensure_index,
    make_index_client,
    make_search_client,
    upload_chunks,
)

logger = structlog.get_logger()

_EMBED_BATCH = 64  # chunks per embeddings request


async def _set_status(document_id: uuid.UUID, status: str, **fields: object) -> None:
    async with SessionLocal() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            return
        doc.status = status
        for key, value in fields.items():
            setattr(doc, key, value)
        await db.commit()


async def ingest_document(document_id: uuid.UUID) -> None:
    settings = get_settings()

    async with SessionLocal() as db:
        doc = await db.get(Document, document_id)
        if doc is None:
            logger.warning("ingest_missing_document", document_id=str(document_id))
            return
        filename = doc.filename
        doc.status = "processing"
        await db.commit()

    log = logger.bind(document_id=str(document_id), filename=filename)
    try:
        blob_client = make_blob_service_client(settings)
        try:
            data = await download_pdf(
                blob_client, settings.azure_storage_container, blob_name_for(document_id, filename)
            )
        finally:
            await blob_client.close()

        chunks = chunk_segments(parse_document(filename, data))
        if not chunks:
            raise ValueError("No extractable text in document (scanned, empty, or unreadable?)")

        openai_client = make_openai_client(settings)
        try:
            embeddings: list[list[float]] = []
            for batch in batched(chunks, _EMBED_BATCH):
                embeddings.extend(
                    await embed_texts(
                        openai_client,
                        settings.azure_openai_embedding_deployment,
                        [c.content for c in batch],
                    )
                )
        finally:
            await openai_client.close()

        index_client = make_index_client(settings)
        try:
            await ensure_index(index_client, settings.azure_search_index_name)
        finally:
            await index_client.close()

        search_client = make_search_client(settings)
        try:
            await upload_chunks(
                search_client,
                [
                    {
                        "id": f"{document_id}_{c.chunk_index}",
                        "document_id": str(document_id),
                        "filename": filename,
                        "page": c.page,
                        "location": c.location,
                        "chunk_index": c.chunk_index,
                        "content": c.content,
                        "embedding": emb,
                    }
                    for c, emb in zip(chunks, embeddings, strict=True)
                ],
            )
        finally:
            await search_client.close()

        await _set_status(document_id, "indexed", chunk_count=len(chunks), error_message=None)
        await invalidate_search_cache()
        log.info("ingest_done", chunks=len(chunks))
    except Exception as exc:  # noqa: BLE001 — top of the job: record failure, don't crash worker
        log.exception("ingest_failed")
        await _set_status(
            document_id, "failed", error_message=f"{type(exc).__name__}: {exc}"[:1000]
        )
