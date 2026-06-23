"""Tests for build_messages (pure function — no Azure calls)."""

from app.services.generation.generator import build_messages
from app.services.generation.prompts import NOT_FOUND_MESSAGE, SYSTEM_PROMPT, get_prompt


class TestBuildMessages:
    CHUNKS = [
        {"filename": "doc.pdf", "location": "s. 1", "content": "Warszawa jest stolicą Polski."},
        {"filename": "doc.pdf", "location": "s. 2", "content": "Kraków to drugie miasto."},
    ]

    def test_basic_structure(self):
        msgs = build_messages("Jaka jest stolica?", self.CHUNKS)
        assert len(msgs) == 2
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"

    def test_system_prompt_default(self):
        msgs = build_messages("test", self.CHUNKS)
        assert msgs[0]["content"] == SYSTEM_PROMPT

    def test_custom_system_prompt(self):
        custom = "Custom prompt here"
        msgs = build_messages("test", self.CHUNKS, system_prompt=custom)
        assert msgs[0]["content"] == custom

    def test_context_in_user_message(self):
        msgs = build_messages("test", self.CHUNKS)
        user_msg = msgs[1]["content"]
        assert "Fragmenty:" in user_msg
        assert "[1]" in user_msg
        assert "[2]" in user_msg
        assert "doc.pdf" in user_msg
        assert "s. 1" in user_msg
        assert "Warszawa" in user_msg
        assert "Pytanie: test" in user_msg

    def test_history_inserted_between_system_and_user(self):
        history = [
            {"role": "user", "content": "Cześć"},
            {"role": "assistant", "content": "Witaj!"},
        ]
        msgs = build_messages("Nowe pytanie", self.CHUNKS, history=history)
        assert len(msgs) == 4
        assert msgs[0]["role"] == "system"
        assert msgs[1]["role"] == "user"
        assert msgs[1]["content"] == "Cześć"
        assert msgs[2]["role"] == "assistant"
        assert msgs[3]["role"] == "user"
        assert "Nowe pytanie" in msgs[3]["content"]

    def test_empty_history_same_as_none(self):
        msgs_none = build_messages("q", self.CHUNKS, history=None)
        msgs_empty = build_messages("q", self.CHUNKS, history=[])
        assert len(msgs_none) == len(msgs_empty)

    def test_context_token_budget_drops_excess_chunks(self):
        big_chunks = [
            {"filename": f"doc{i}.pdf", "location": f"s. {i}", "content": "word " * 300}
            for i in range(10)
        ]
        msgs = build_messages("q", big_chunks, max_context_tokens=2000)
        user_msg = msgs[-1]["content"]
        assert "[1]" in user_msg
        assert "[10]" not in user_msg

    def test_all_chunks_fit_when_small(self):
        msgs = build_messages("q", self.CHUNKS, max_context_tokens=4000)
        user_msg = msgs[-1]["content"]
        assert "[1]" in user_msg
        assert "[2]" in user_msg


class TestPrompts:
    def test_v1_prompt_contains_grounding_rules(self):
        prompt = get_prompt("v1")
        assert NOT_FOUND_MESSAGE in prompt
        assert "cytowanie" in prompt.lower() or "cytowani" in prompt.lower()

    def test_v2_prompt_differs_from_v1(self):
        assert get_prompt("v1") != get_prompt("v2")

    def test_unknown_version_raises(self):
        import pytest

        with pytest.raises(KeyError):
            get_prompt("nonexistent")

    def test_not_found_message_is_polish(self):
        assert "znalazłem" in NOT_FOUND_MESSAGE
