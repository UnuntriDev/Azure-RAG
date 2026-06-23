"""LLM-as-judge RAG metrics, each returning float in [0, 1]:
  faithfulness      — fraction of answer claims supported by retrieved context
  answer_relevancy  — cosine sim between question and questions generated from the answer
  context_precision — average precision: are relevant chunks ranked near the top?
  context_recall    — fraction of ground-truth claims covered by context
"""

import math

from openai import AsyncAzureOpenAI
from pydantic import BaseModel, Field

from app.services.ingestion.embedder import embed_texts


class _Statements(BaseModel):
    statements: list[str] = Field(description="Lista atomowych, samodzielnych twierdzeń")


class _Verdict(BaseModel):
    statement: str
    supported: bool = Field(description="true, jeśli twierdzenie wynika z kontekstu")


class _Verdicts(BaseModel):
    verdicts: list[_Verdict]


class _ContextVerdicts(BaseModel):
    # one bool per fragment, in order
    relevant: list[bool] = Field(
        description="Dla każdego fragmentu po kolei: czy jest przydatny do odpowiedzi (true/false)"
    )


class _GeneratedQuestions(BaseModel):
    questions: list[str] = Field(description="Pytania, na które ta odpowiedź jest odpowiedzią")


async def _parse(client: AsyncAzureOpenAI, deployment: str, system: str, user: str, schema):
    completion = await client.beta.chat.completions.parse(
        model=deployment,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        response_format=schema,
        temperature=0,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:
        raise ValueError("Judge nie zwrócił ustrukturyzowanej odpowiedzi.")
    return parsed


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb) if na and nb else 0.0


async def faithfulness(
    client: AsyncAzureOpenAI, deployment: str, answer: str, contexts: list[str]
) -> float:
    """Fraction of answer claims that are supported by the retrieved context."""
    stmts = await _parse(
        client,
        deployment,
        "Rozbij podaną odpowiedź na listę atomowych twierdzeń (każde to jedno proste zdanie).",
        f"Odpowiedź:\n{answer}",
        _Statements,
    )
    if not stmts.statements:
        return 0.0

    context = "\n".join(contexts)
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(stmts.statements, 1))
    verds = await _parse(
        client,
        deployment,
        "Dla każdego twierdzenia oceń, czy MOŻNA je wywnioskować WYŁĄCZNIE z podanego "
        "kontekstu. Zwróć werdykt true/false dla każdego.",
        f"Kontekst:\n{context}\n\nTwierdzenia:\n{numbered}",
        _Verdicts,
    )
    if not verds.verdicts:
        return 0.0
    return sum(1 for v in verds.verdicts if v.supported) / len(verds.verdicts)


async def context_recall(
    client: AsyncAzureOpenAI, deployment: str, ground_truth: str, contexts: list[str]
) -> float:
    """Fraction of ground-truth claims that can be attributed to the retrieved context."""
    stmts = await _parse(
        client,
        deployment,
        "Rozbij wzorcową odpowiedź na listę atomowych twierdzeń.",
        f"Wzorcowa odpowiedź:\n{ground_truth}",
        _Statements,
    )
    if not stmts.statements:
        return 0.0

    context = "\n".join(contexts)
    numbered = "\n".join(f"{i}. {s}" for i, s in enumerate(stmts.statements, 1))
    verds = await _parse(
        client,
        deployment,
        "Dla każdego twierdzenia oceń, czy znajduje potwierdzenie w podanym kontekście.",
        f"Kontekst:\n{context}\n\nTwierdzenia:\n{numbered}",
        _Verdicts,
    )
    if not verds.verdicts:
        return 0.0
    return sum(1 for v in verds.verdicts if v.supported) / len(verds.verdicts)


async def context_precision(
    client: AsyncAzureOpenAI,
    deployment: str,
    question: str,
    ground_truth: str,
    contexts: list[str],
) -> float:
    """Average precision: are the relevant fragments ranked near the top?"""
    if not contexts:
        return 0.0
    numbered = "\n\n".join(f"[{i}]\n{c}" for i, c in enumerate(contexts, 1))
    verds = await _parse(
        client,
        deployment,
        "Oceń każdy fragment po kolei: czy jest przydatny do udzielenia wzorcowej odpowiedzi "
        "na pytanie? Zwróć listę true/false w tej samej kolejności co fragmenty.",
        f"Pytanie: {question}\nWzorcowa odpowiedź: {ground_truth}\n\nFragmenty:\n{numbered}",
        _ContextVerdicts,
    )
    rel = [1 if r else 0 for r in verds.relevant][: len(contexts)]
    total_relevant = sum(rel)
    if total_relevant == 0:
        return 0.0
    hits = 0
    ap = 0.0
    for i, r in enumerate(rel, 1):
        if r:
            hits += 1
            ap += hits / i
    return ap / total_relevant


async def answer_relevancy(
    client: AsyncAzureOpenAI,
    embedding_deployment: str,
    judge_deployment: str,
    question: str,
    answer: str,
) -> float:
    """Mean cosine similarity between the question and questions generated from the answer."""
    gen = await _parse(
        client,
        judge_deployment,
        "Wygeneruj 3 pytania, na które poniższa odpowiedź byłaby trafną odpowiedzią.",
        f"Odpowiedź:\n{answer}",
        _GeneratedQuestions,
    )
    if not gen.questions:
        return 0.0
    embeddings = await embed_texts(client, embedding_deployment, [question, *gen.questions])
    base, generated = embeddings[0], embeddings[1:]
    return sum(_cosine(base, e) for e in generated) / len(generated)
