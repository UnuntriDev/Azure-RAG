"""Tests for chat router helper functions."""

import json
import uuid
from types import SimpleNamespace

from app.routers.chat import _dedupe_sources, _history_from_messages, _own_conv, _sse


class TestSse:
    def test_format(self):
        result = _sse("delta", {"content": "tok"})
        assert result.startswith("event: delta\n")
        assert "data: " in result
        assert result.endswith("\n\n")
        data = json.loads(result.split("data: ")[1].strip())
        assert data == {"content": "tok"}

    def test_unicode(self):
        result = _sse("delta", {"content": "żółć"})
        assert "żółć" in result

    def test_string_data(self):
        result = _sse("error", "plain string")
        assert 'data: plain string\n' in result

    def test_list_data(self):
        result = _sse("sources", [{"a": 1}])
        data = json.loads(result.split("data: ")[1].strip())
        assert isinstance(data, list)


class TestHistoryFromMessages:
    def _msg(self, role: str, content: str):
        return SimpleNamespace(role=role, content=content)

    def test_basic(self):
        msgs = [self._msg("user", "Cześć"), self._msg("assistant", "Witaj")]
        result = _history_from_messages(msgs)
        assert result == [
            {"role": "user", "content": "Cześć"},
            {"role": "assistant", "content": "Witaj"},
        ]

    def test_truncation_to_max_turns(self):
        msgs = [self._msg("user" if i % 2 == 0 else "assistant", f"msg{i}") for i in range(30)]
        result = _history_from_messages(msgs)
        assert len(result) == 20  # MAX_HISTORY_TURNS=10 × 2 roles

    def test_empty(self):
        assert _history_from_messages([]) == []

    def test_token_budget_truncation(self):
        long_text = "słowo " * 2000
        msgs = [
            self._msg("user", "krótkie pytanie"),
            self._msg("assistant", long_text),
            self._msg("user", "drugie pytanie"),
            self._msg("assistant", "krótka odpowiedź"),
        ]
        result = _history_from_messages(msgs)
        assert len(result) < 4
        assert result[-1]["content"] == "krótka odpowiedź"

    def test_short_messages_within_budget(self):
        msgs = [self._msg("user", f"q{i}") for i in range(6)]
        result = _history_from_messages(msgs)
        assert len(result) == 6


class TestDedupeSources:
    _ID_A = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
    _ID_B = "bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"

    def _chunk(self, doc_id: str, chunk_index: int, score: float = 1.0):
        return {
            "document_id": doc_id,
            "filename": "test.pdf",
            "page": 1,
            "location": "s. 1",
            "chunk_index": chunk_index,
            "content": "text",
            "score": score,
        }

    def test_no_duplicates(self):
        chunks = [self._chunk(self._ID_A, 0), self._chunk(self._ID_A, 1), self._chunk(self._ID_B, 0)]
        result = _dedupe_sources(chunks)
        assert len(result) == 3

    def test_duplicates_removed(self):
        chunks = [self._chunk(self._ID_A, 0), self._chunk(self._ID_A, 0), self._chunk(self._ID_A, 0)]
        result = _dedupe_sources(chunks)
        assert len(result) == 1

    def test_empty(self):
        assert _dedupe_sources([]) == []


class TestOwnConv:
    def _conv(self, user_id: str | None):
        return SimpleNamespace(user_id=user_id)

    def test_no_auth(self):
        assert _own_conv(self._conv("owner"), None) is True

    def test_no_conv_user(self):
        assert _own_conv(self._conv(None), "user123") is True

    def test_owner_match(self):
        assert _own_conv(self._conv("user123"), "user123") is True

    def test_owner_mismatch(self):
        assert _own_conv(self._conv("owner"), "other") is False
