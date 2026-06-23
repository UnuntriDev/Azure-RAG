"""Agent tools: search_documents, compare_documents, calculator.
Retrieved chunks are pushed into sources_sink for citation rendering.
"""

import ast
import operator

from azure.search.documents.aio import SearchClient
from langchain_core.tools import StructuredTool
from openai import AsyncAzureOpenAI

from app.config import Settings
from app.services.retrieval.retriever import hybrid_search

# Whitelist — rejects function calls, identifiers, and attribute access.
_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _safe_eval(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("Niedozwolone wyrażenie.")


def calculate(expression: str) -> str:
    """Oblicz wyrażenie arytmetyczne, np. "1234 * 0.23" lub "(50+70)/2".
    Dozwolone tylko liczby, operatory + - * / ** % i nawiasy."""
    try:
        tree = ast.parse(expression, mode="eval")
        return str(_safe_eval(tree.body))
    except Exception:
        return f"Nie udało się obliczyć wyrażenia: {expression!r}"


def _format_chunks(chunks: list[dict]) -> str:
    if not chunks:
        return "Brak pasujących fragmentów."
    return "\n\n".join(f"({c['filename']}, {c['location']})\n{c['content']}" for c in chunks)


def build_tools(
    search_client: SearchClient,
    openai_client: AsyncAzureOpenAI,
    settings: Settings,
    sources_sink: list[dict],
    document_ids: list[str] | None = None,
) -> list[StructuredTool]:
    embedding_deployment = settings.azure_openai_embedding_deployment
    semantic_config = settings.azure_search_semantic_config or None

    async def search_documents(query: str) -> str:
        """Przeszukaj dokumenty użytkownika i zwróć najtrafniejsze fragmenty z cytowaniami.
        Podaj zwięzłe zapytanie opisujące szukaną informację."""
        chunks = await hybrid_search(
            search_client, openai_client, embedding_deployment, query,
            document_ids=document_ids, semantic_config=semantic_config,
        )
        sources_sink.extend(chunks)
        return _format_chunks(chunks)

    async def compare_documents(query_a: str, query_b: str) -> str:
        """Porównaj dwa zagadnienia: pobiera fragmenty dla query_a i query_b osobno
        i zwraca je obok siebie, byś mógł je zestawić."""
        chunks_a = await hybrid_search(
            search_client, openai_client, embedding_deployment, query_a,
            document_ids=document_ids, semantic_config=semantic_config,
        )
        chunks_b = await hybrid_search(
            search_client, openai_client, embedding_deployment, query_b,
            document_ids=document_ids, semantic_config=semantic_config,
        )
        sources_sink.extend(chunks_a)
        sources_sink.extend(chunks_b)
        return (
            f"=== A: {query_a} ===\n{_format_chunks(chunks_a)}\n\n"
            f"=== B: {query_b} ===\n{_format_chunks(chunks_b)}"
        )

    return [
        StructuredTool.from_function(coroutine=search_documents, name="search_documents"),
        StructuredTool.from_function(coroutine=compare_documents, name="compare_documents"),
        StructuredTool.from_function(func=calculate, name="calculator"),
    ]
