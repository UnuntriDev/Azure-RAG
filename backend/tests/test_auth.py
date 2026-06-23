"""Tests for auth helpers."""

from app.routers.documents import _own
from types import SimpleNamespace


class TestOwn:
    def _doc(self, user_id: str | None):
        return SimpleNamespace(user_id=user_id)

    def test_no_auth(self):
        assert _own(self._doc("owner"), None) is True

    def test_no_doc_user(self):
        assert _own(self._doc(None), "caller") is True

    def test_match(self):
        assert _own(self._doc("user1"), "user1") is True

    def test_mismatch(self):
        assert _own(self._doc("user1"), "user2") is False
