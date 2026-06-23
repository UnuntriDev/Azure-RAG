"""Token-based chunking (tiktoken, 600 / 80 overlap). Per-segment so each chunk maps to one citation.

Polish is token-expensive — character-based splitting would blow the model's budget.
"""

import functools
from dataclasses import dataclass

import tiktoken

from app.services.ingestion.parsers import ParsedSegment

CHUNK_TOKENS = 600
OVERLAP_TOKENS = 80


@dataclass
class Chunk:
    content: str
    page: int  # 1-based source ordinal (sort key)
    location: str  # human-readable citation label inherited from the source segment
    chunk_index: int  # 0-based, global across the document


@functools.cache
def _get_encoding() -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model("gpt-4o-mini")
    except KeyError:  # older tiktoken without the alias
        return tiktoken.get_encoding("o200k_base")


def chunk_segments(
    segments: list[ParsedSegment],
    chunk_tokens: int = CHUNK_TOKENS,
    overlap_tokens: int = OVERLAP_TOKENS,
) -> list[Chunk]:
    enc = _get_encoding()
    step = chunk_tokens - overlap_tokens
    chunks: list[Chunk] = []
    idx = 0

    for seg in segments:
        text = seg.text.strip()
        if not text:
            continue
        tokens = enc.encode(text)

        start = 0
        while start < len(tokens):
            window = tokens[start : start + chunk_tokens]
            content = enc.decode(window).strip()
            if content:
                chunks.append(
                    Chunk(
                        content=content,
                        page=seg.page,
                        location=seg.location,
                        chunk_index=idx,
                    )
                )
                idx += 1
            if start + chunk_tokens >= len(tokens):
                break
            start += step

    return chunks
