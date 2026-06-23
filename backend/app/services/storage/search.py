"""Azure AI Search — index definition + chunk upsert/delete.

Index schema:
  id (key) | document_id (filterable) | filename (filterable) | page int32 (filterable)
  | chunk_index int32 | content (searchable, BM25) | embedding 1536-dim hnsw/cosine
"""

from azure.core.exceptions import ResourceNotFoundError
from azure.search.documents.aio import SearchClient
from azure.search.documents.indexes.aio import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    HnswParameters,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SimpleField,
    VectorSearch,
    VectorSearchAlgorithmMetric,
    VectorSearchProfile,
)

from app.config import Settings

EMBEDDING_DIM = 1536
_VECTOR_PROFILE = "default"
_HNSW_CONFIG = "default-hnsw"
_OP_TIMEOUT = 30  # seconds


def _search_credential(settings: Settings):
    if settings.azure_search_api_key:
        from azure.core.credentials import AzureKeyCredential

        return AzureKeyCredential(settings.azure_search_api_key)

    from app.azure_credential import get_azure_credential

    return get_azure_credential()


def make_index_client(settings: Settings) -> SearchIndexClient:
    return SearchIndexClient(settings.azure_search_endpoint, _search_credential(settings))


def make_search_client(settings: Settings) -> SearchClient:
    return SearchClient(
        settings.azure_search_endpoint,
        settings.azure_search_index_name,
        _search_credential(settings),
    )


def build_index(name: str) -> SearchIndex:
    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SimpleField(name="document_id", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="filename", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="page", type=SearchFieldDataType.Int32, filterable=True),
        SimpleField(name="location", type=SearchFieldDataType.String),
        SimpleField(name="chunk_index", type=SearchFieldDataType.Int32),
        SearchableField(name="content", type=SearchFieldDataType.String),
        SearchField(
            name="embedding",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=EMBEDDING_DIM,
            vector_search_profile_name=_VECTOR_PROFILE,
        ),
    ]
    vector_search = VectorSearch(
        algorithms=[
            HnswAlgorithmConfiguration(
                name=_HNSW_CONFIG,
                parameters=HnswParameters(
                    m=4, ef_construction=400, metric=VectorSearchAlgorithmMetric.COSINE
                ),
            )
        ],
        profiles=[
            VectorSearchProfile(name=_VECTOR_PROFILE, algorithm_configuration_name=_HNSW_CONFIG)
        ],
    )
    return SearchIndex(name=name, fields=fields, vector_search=vector_search)


async def ensure_index(index_client: SearchIndexClient, name: str) -> None:
    """Create the index if it doesn't exist (idempotent — safe to call before every ingest)."""
    try:
        await index_client.get_index(name)
    except ResourceNotFoundError:
        await index_client.create_index(build_index(name))


async def upload_chunks(search_client: SearchClient, documents: list[dict]) -> None:
    if not documents:
        return
    results = await search_client.upload_documents(documents=documents, timeout=_OP_TIMEOUT)
    failed = [r.key for r in results if not r.succeeded]
    if failed:
        raise RuntimeError(f"AI Search rejected {len(failed)} chunk(s): {failed[:5]}")


async def fetch_document_chunks(
    search_client: SearchClient, document_id: str, limit: int = 50
) -> list[dict]:
    """Return a single document's chunks ordered by chunk_index (for whole-doc analysis)."""
    results = await search_client.search(
        search_text="*",
        filter=f"document_id eq '{document_id}'",
        select=["chunk_index", "content", "location"],
        top=limit,
        timeout=_OP_TIMEOUT,
    )
    chunks = [doc async for doc in results]
    chunks.sort(key=lambda c: c["chunk_index"])
    return chunks


async def delete_document_chunks(
    search_client: SearchClient, document_id: str, chunk_count: int | None = None
) -> int:
    """Delete a document's chunks. Prefers deterministic key lookup — search is racy after ingest."""
    if chunk_count and chunk_count > 0:
        ids = [{"id": f"{document_id}_{i}"} for i in range(chunk_count)]
    else:
        # Fallback when chunk_count is unknown (e.g. a failed/partial ingest).
        results = await search_client.search(
            search_text="*",
            filter=f"document_id eq '{document_id}'",
            select=["id"],
            top=1000,
            timeout=_OP_TIMEOUT,
        )
        ids = [{"id": doc["id"]} async for doc in results]

    if ids:
        await search_client.delete_documents(documents=ids, timeout=_OP_TIMEOUT)
    return len(ids)
