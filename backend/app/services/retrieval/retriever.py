"""Hybrid BM25 + vector search via Azure AI Search, fused with RRF.

When semantic_config is provided the results are re-ranked by Azure AI Search's
semantic ranker (requires Standard S1+ tier and a configured semantic configuration).
"""

from azure.search.documents.aio import SearchClient
from azure.search.documents.models import QueryType, VectorizedQuery
from openai import AsyncAzureOpenAI

from app.services.cache import SEARCH_TTL, get_cached, search_key, set_cached
from app.services.ingestion.embedder import embed_texts

TOP_K = 5


async def hybrid_search(
    search_client: SearchClient,
    openai_client: AsyncAzureOpenAI,
    embedding_deployment: str,
    question: str,
    top_k: int = TOP_K,
    document_ids: list[str] | None = None,
    semantic_config: str | None = None,
) -> list[dict]:
    key = search_key(embedding_deployment, question, document_ids, bool(semantic_config))
    cached = await get_cached(key)
    if cached is not None:
        return cached

    query_vector = (await embed_texts(openai_client, embedding_deployment, [question]))[0]
    vector_query = VectorizedQuery(
        vector=query_vector, k_nearest_neighbors=top_k, fields="embedding"
    )

    odata_filter: str | None = None
    if document_ids:
        clauses = " or ".join(f"document_id eq '{did}'" for did in document_ids)
        odata_filter = f"({clauses})"

    search_kwargs: dict = dict(
        search_text=question,
        vector_queries=[vector_query],
        filter=odata_filter,
        select=["document_id", "filename", "page", "location", "chunk_index", "content"],
        top=top_k,
    )
    if semantic_config:
        search_kwargs["query_type"] = QueryType.SEMANTIC
        search_kwargs["semantic_configuration_name"] = semantic_config

    results = await search_client.search(**search_kwargs)

    chunks: list[dict] = []
    async for r in results:
        reranker = r.get("@search.reranker_score")
        score = reranker if reranker is not None else r["@search.score"]
        chunks.append(
            {
                "document_id": r["document_id"],
                "filename": r["filename"],
                "page": r["page"],
                "location": r.get("location") or f"s. {r['page']}",
                "chunk_index": r["chunk_index"],
                "content": r["content"],
                "score": score,
            }
        )

    await set_cached(key, chunks, SEARCH_TTL)
    return chunks
