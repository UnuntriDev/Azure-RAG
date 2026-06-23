"""Answer generation."""

import functools

from openai import AsyncAzureOpenAI

from app.services.generation.prompts import SYSTEM_PROMPT

TEMPERATURE = 0.1  # low — we want grounded, repeatable answers, not creativity
MAX_CONTEXT_TOKENS = 4000


@functools.cache
def _get_encoding():
    import tiktoken

    try:
        return tiktoken.encoding_for_model("gpt-4o-mini")
    except KeyError:
        return tiktoken.get_encoding("o200k_base")


def build_messages(
    question: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    system_prompt: str | None = None,
    max_context_tokens: int = MAX_CONTEXT_TOKENS,
) -> list[dict]:
    """System prompt + optional history + user turn with numbered context fragments.

    Chunks are added until the token budget is exhausted — later chunks are dropped.
    """
    enc = _get_encoding()
    context_parts: list[str] = []
    total = 0
    for i, c in enumerate(chunks, start=1):
        part = f"[{i}] ({c['filename']}, {c['location']})\n{c['content']}"
        tokens = len(enc.encode(part))
        if total + tokens > max_context_tokens:
            break
        context_parts.append(part)
        total += tokens

    context = "\n\n".join(context_parts)
    messages: list[dict] = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": f"Fragmenty:\n{context}\n\nPytanie: {question}"})
    return messages


async def generate_answer(
    client: AsyncAzureOpenAI,
    deployment: str,
    question: str,
    chunks: list[dict],
    history: list[dict] | None = None,
    system_prompt: str | None = None,
) -> str:
    response = await client.chat.completions.create(
        model=deployment,
        messages=build_messages(question, chunks, history, system_prompt),
        temperature=TEMPERATURE,
        max_tokens=2048,
    )
    return (response.choices[0].message.content or "").strip()
