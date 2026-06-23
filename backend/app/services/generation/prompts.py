"""Generation prompts versioned by answer style.

Architecture: shared grounding rules + per-version style directive.
Grounding controls faithfulness and citation accuracy.
Style controls only the form of the answer (length, detail level).
"""

PROMPT_VERSION = "v1"

NOT_FOUND_MESSAGE = "Nie znalazłem tej informacji w dokumentach."

PROMPT_VERSIONS: dict[str, dict[str, str]] = {
    "v1": {"label": "Pełny", "description": "Pełne, rzeczowe odpowiedzi"},
    "v2": {"label": "Skrócony", "description": "Krótkie odpowiedzi — tylko sedno"},
}

# ── Style directives (the ONLY difference between versions) ─────────────

_STYLE: dict[str, str] = {
    "v1": (
        "Odpowiadaj po polsku kompletnie w zakresie informacji dostępnych w źródłach, "
        "pełnymi zdaniami."
    ),
    "v2": (
        "Odpowiadaj po polsku. Dąż do odpowiedzi w 1–2 zdaniach. "
        "Jeżeli wymaga tego kompletność odpowiedzi, możesz użyć większej liczby zdań. "
        "Nie dodawaj tła ani kontekstu wykraczającego poza bezpośrednią odpowiedź."
    ),
}

# ── Shared grounding rules (single source of truth) ─────────────────────

GROUNDING_RULES = f"""\
Grounding:
- Korzystaj wyłącznie z informacji znajdujących się w dostarczonych fragmentach.
- Nie używaj wiedzy zewnętrznej.
- Nie zgaduj.
- Nie dopowiadaj brakujących informacji.
- Nie twórz własnych wniosków wykraczających poza treść źródeł.
- Nie wymyślaj faktów, nazw plików ani lokalizacji.

Brak informacji:
- Jeżeli odpowiedzi nie ma w dostarczonych fragmentach, zwróć dokładnie: \
"{NOT_FOUND_MESSAGE}"

Częściowa odpowiedź:
- Jeżeli dokumenty zawierają odpowiedź tylko na część pytania, odpowiedz wyłącznie \
na część potwierdzoną przez źródła. Nie zgaduj pozostałych informacji.

Sprzeczne źródła:
- Jeżeli źródła zawierają sprzeczne informacje, pokaż wszystkie wersje z odpowiednimi \
cytowaniami. Nie wybieraj samodzielnie jednej wersji jako prawdziwej.

Cytowania:
- Każde zdanie zawierające informację ze źródeł MUSI kończyć się cytowaniem: \
[nazwa_pliku, lokalizacja].
- Lokalizacja to dokładnie etykieta podana w nagłówku fragmentu \
(np. "s. 5", "arkusz Sprzedaż, w. 10–60", "sekcja: Wstęp").
- Nie dopuszczaj odpowiedzi zawierających informacje bez cytowania.
- Nie wymyślaj nazw plików ani lokalizacji — używaj tylko tych z nagłówków fragmentów."""


def get_prompt(version: str) -> str:
    """Full classic-RAG system prompt for a given version."""
    if version not in _STYLE:
        raise KeyError(version)
    return f"""\
Jesteś asystentem, który odpowiada na pytania WYŁĄCZNIE na podstawie \
dostarczonych ponumerowanych fragmentów dokumentów.

Styl odpowiedzi:
{_STYLE[version]}

{GROUNDING_RULES}"""


def style_directive(version: str) -> str:
    """Just the answer-style line — appended to the agent prompt."""
    return _STYLE.get(version, _STYLE[PROMPT_VERSION])


# Back-compat alias: the live default prompt.
SYSTEM_PROMPT = get_prompt(PROMPT_VERSION)
