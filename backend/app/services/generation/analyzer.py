"""Structured document analysis via OpenAI structured outputs."""

from openai import AsyncAzureOpenAI

from app.schemas.analysis import DocumentAnalysis

ANALYSIS_SYSTEM_PROMPT = (
    "Jesteś analitykiem dokumentów. Na podstawie dostarczonych fragmentów wypełnij "
    "ustrukturyzowaną analizę dokumentu po polsku. Opieraj się wyłącznie na treści "
    "fragmentów — nie dodawaj informacji spoza nich."
)

# First chunks carry the gist; capping prevents blowing the prompt window.
_MAX_CHUNKS = 30


async def analyze_document(
    client: AsyncAzureOpenAI,
    deployment: str,
    filename: str,
    content_blocks: list[str],
) -> DocumentAnalysis:
    context = "\n\n".join(content_blocks[:_MAX_CHUNKS])
    completion = await client.beta.chat.completions.parse(
        model=deployment,
        messages=[
            {"role": "system", "content": ANALYSIS_SYSTEM_PROMPT},
            {"role": "user", "content": f"Dokument: {filename}\n\nFragmenty:\n{context}"},
        ],
        response_format=DocumentAnalysis,
        temperature=0.1,
        max_tokens=4096,
    )
    parsed = completion.choices[0].message.parsed
    if parsed is None:  # model refused structured output
        raise ValueError("Model nie zwrócił ustrukturyzowanej analizy.")
    return parsed
