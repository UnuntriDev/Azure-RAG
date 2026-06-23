"""Azure Blob Storage — store/fetch/delete uploaded documents. Stateless; client built from Settings."""

import mimetypes
import uuid

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import ContentSettings
from azure.storage.blob.aio import BlobServiceClient

from app.config import Settings

_OP_TIMEOUT = 60  # seconds — every external call gets a timeout (convention)


def blob_name_for(document_id: uuid.UUID, filename: str = "") -> str:
    """Deterministic blob name from the document id, preserving the original extension."""
    ext = ""
    if filename:
        parts = filename.rsplit(".", 1)
        if len(parts) == 2:
            ext = f".{parts[1].lower()}"
    return f"{document_id}{ext or '.bin'}"


def make_blob_service_client(settings: Settings) -> BlobServiceClient:
    if settings.azure_storage_connection_string:
        return BlobServiceClient.from_connection_string(settings.azure_storage_connection_string)

    from app.azure_credential import get_azure_credential

    return BlobServiceClient(settings.azure_storage_account_url, credential=get_azure_credential())


async def ensure_container(client: BlobServiceClient, container: str) -> None:
    try:
        await client.create_container(container, timeout=_OP_TIMEOUT)
    except ResourceExistsError:
        pass


async def upload_pdf(client: BlobServiceClient, container: str, blob_name: str, data: bytes) -> str:
    """Upload bytes, return the blob URL. Overwrites if the name already exists."""
    await ensure_container(client, container)
    content_type = mimetypes.guess_type(blob_name)[0] or "application/octet-stream"
    blob = client.get_blob_client(container=container, blob=blob_name)
    await blob.upload_blob(
        data,
        overwrite=True,
        content_settings=ContentSettings(content_type=content_type),
        timeout=_OP_TIMEOUT,
    )
    return blob.url


async def download_pdf(client: BlobServiceClient, container: str, blob_name: str) -> bytes:
    blob = client.get_blob_client(container=container, blob=blob_name)
    stream = await blob.download_blob(timeout=_OP_TIMEOUT)
    return await stream.readall()


async def delete_pdf(client: BlobServiceClient, container: str, blob_name: str) -> None:
    blob = client.get_blob_client(container=container, blob=blob_name)
    try:
        await blob.delete_blob(timeout=_OP_TIMEOUT)
    except ResourceNotFoundError:
        pass  # already gone — deletion is idempotent
