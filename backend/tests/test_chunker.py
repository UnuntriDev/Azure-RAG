"""Tests for token-based chunker."""

from app.services.ingestion.chunker import Chunk, chunk_segments
from app.services.ingestion.parsers import ParsedSegment


class TestChunkSegments:
    def test_short_segment_single_chunk(self):
        segments = [ParsedSegment(text="Krótki tekst.", page=1, location="s. 1")]
        chunks = chunk_segments(segments)
        assert len(chunks) == 1
        assert chunks[0].content == "Krótki tekst."
        assert chunks[0].page == 1
        assert chunks[0].location == "s. 1"
        assert chunks[0].chunk_index == 0

    def test_empty_segments(self):
        assert chunk_segments([]) == []

    def test_whitespace_only_segment_skipped(self):
        segments = [ParsedSegment(text="   \n  ", page=1, location="s. 1")]
        assert chunk_segments(segments) == []

    def test_long_segment_produces_multiple_chunks(self):
        long_text = "Oto długi tekst. " * 500
        segments = [ParsedSegment(text=long_text, page=1, location="s. 1")]
        chunks = chunk_segments(segments)
        assert len(chunks) > 1
        assert all(c.page == 1 for c in chunks)
        assert all(c.location == "s. 1" for c in chunks)
        assert [c.chunk_index for c in chunks] == list(range(len(chunks)))

    def test_multiple_segments_continuous_index(self):
        segments = [
            ParsedSegment(text="Pierwszy segment.", page=1, location="s. 1"),
            ParsedSegment(text="Drugi segment.", page=2, location="s. 2"),
        ]
        chunks = chunk_segments(segments)
        assert len(chunks) == 2
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[0].page == 1
        assert chunks[1].page == 2

    def test_custom_chunk_size(self):
        text = "Słowo " * 100
        segments = [ParsedSegment(text=text, page=1, location="s. 1")]
        small_chunks = chunk_segments(segments, chunk_tokens=20, overlap_tokens=5)
        large_chunks = chunk_segments(segments, chunk_tokens=200, overlap_tokens=10)
        assert len(small_chunks) > len(large_chunks)

    def test_overlap_content(self):
        """Overlapping chunks should share some text."""
        text = "Jeden dwa trzy cztery pięć sześć siedem osiem dziewięć dziesięć. " * 50
        segments = [ParsedSegment(text=text, page=1, location="s. 1")]
        chunks = chunk_segments(segments, chunk_tokens=30, overlap_tokens=10)
        if len(chunks) >= 2:
            words_0 = set(chunks[0].content.split())
            words_1 = set(chunks[1].content.split())
            assert words_0 & words_1, "Adjacent chunks should share overlapping words"
