"""Structured-output schema for document analysis (stage 2).

This Pydantic model IS the contract handed to the model via OpenAI structured outputs
(`response_format=DocumentAnalysis`) — the model is forced to return exactly these fields,
so no brittle JSON-string parsing. Field descriptions guide the extraction.
"""

from pydantic import BaseModel, Field


class Entity(BaseModel):
    name: str = Field(description="Nazwa encji")
    type: str = Field(description="Typ encji: osoba, organizacja, miejsce, produkt lub inne")


class DocumentAnalysis(BaseModel):
    summary: str = Field(description="Zwięzłe streszczenie dokumentu w 2–3 zdaniach")
    key_points: list[str] = Field(description="3–6 najważniejszych punktów lub wniosków")
    entities: list[Entity] = Field(description="Kluczowe encje wymienione w dokumencie")
    suggested_questions: list[str] = Field(
        description="3 pytania, które użytkownik mógłby zadać o ten dokument"
    )
