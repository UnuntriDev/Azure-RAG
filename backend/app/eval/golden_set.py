"""Golden eval set — questions with ground-truth answers for the demo corpus.

These are the "expected answers" the brief asks for: a fixed set we score the RAG
pipeline against on every eval run. Tied to the seeded demo documents
(polska-fakty.pdf, FinPort_Prezentacja_Notatki.docx). Extend as the corpus grows.
"""

from pydantic import BaseModel


class GoldenQuestion(BaseModel):
    question: str
    ground_truth: str


GOLDEN: list[GoldenQuestion] = [
    GoldenQuestion(
        question="Jaka jest stolica Polski?",
        ground_truth="Stolicą Polski jest Warszawa.",
    ),
    GoldenQuestion(
        question="Jaki jest najwyższy szczyt Polski i ile ma metrów?",
        ground_truth="Najwyższym szczytem Polski są Rysy w Tatrach, 2499 m n.p.m.",
    ),
    GoldenQuestion(
        question="Nad jaką rzeką leży Warszawa?",
        ground_truth="Warszawa leży nad Wisłą.",
    ),
    GoldenQuestion(
        question="Czym jest FinPort?",
        ground_truth=(
            "FinPort to interaktywny dashboard finansowy napisany w Pythonie, "
            "służący do analizy portfeli inwestycyjnych i oceny ryzyka."
        ),
    ),
    GoldenQuestion(
        question="W jakim języku programowania napisano FinPort?",
        ground_truth="FinPort napisano w języku Python.",
    ),
]
