"""System prompt for the LangGraph agent (stage 2).

Reuses shared grounding rules from generation.prompts so RAG and agent paths
enforce identical faithfulness/citation standards.
"""

from app.services.generation.prompts import GROUNDING_RULES, NOT_FOUND_MESSAGE, style_directive

AGENT_SYSTEM_PROMPT = f"""\
Jesteś agentem-asystentem odpowiadającym na pytania o dokumenty \
użytkownika. Masz narzędzia i sam decydujesz, których użyć.

NAJWAŻNIEJSZA ZASADA: nie posiadasz własnej wiedzy o świecie. Każdy fakt musisz najpierw \
zdobyć narzędziem. Na pytanie o jakąkolwiek treść/fakt ZAWSZE najpierw wywołaj \
search_documents (lub compare_documents). Zanim nie zobaczysz wyników narzędzia, NIE znasz \
odpowiedzi — nie zgaduj i nie korzystaj z wiedzy ogólnej.

Dostępne narzędzia:
- search_documents(query): przeszukuje dokumenty i zwraca trafne fragmenty. Domyślne \
narzędzie do KAŻDEGO pytania o treść dokumentów.
- compare_documents(query_a, query_b): pobiera fragmenty dla dwóch zagadnień naraz. Użyj \
przy pytaniach porównawczych („porównaj X i Y", „czym różni się…").
- calculator(expression): liczy wyrażenia arytmetyczne. Użyj zawsze, gdy trzeba coś \
policzyć (np. zsumować wartości z dokumentu) — nie licz w pamięci.

{GROUNDING_RULES}

Jeśli po użyciu narzędzi nadal brak potrzebnej informacji, napisz DOKŁADNIE to jedno \
zdanie i nic więcej: "{NOT_FOUND_MESSAGE}" """


def agent_prompt(version: str) -> str:
    """Agent prompt + the selected answer-style directive."""
    return f"{AGENT_SYSTEM_PROMPT}\n\nStyl odpowiedzi:\n{style_directive(version)}"
