"""Azure OpenAI embeddings (text-embedding-3-small, 1536-dim). Stateless."""

from openai import AsyncAzureOpenAI

from app.config import Settings


def make_openai_client(settings: Settings) -> AsyncAzureOpenAI:
    kwargs: dict = {
        "azure_endpoint": settings.azure_openai_endpoint,
        "api_version": settings.azure_openai_api_version,
        "timeout": 60.0,
        "max_retries": 2,
    }
    if settings.azure_openai_api_key:
        kwargs["api_key"] = settings.azure_openai_api_key
    else:
        from azure.identity.aio import get_bearer_token_provider

        from app.azure_credential import get_azure_credential

        kwargs["azure_ad_token_provider"] = get_bearer_token_provider(
            get_azure_credential(), "https://cognitiveservices.azure.com/.default"
        )
    return AsyncAzureOpenAI(**kwargs)


async def embed_texts(
    client: AsyncAzureOpenAI, deployment: str, texts: list[str]
) -> list[list[float]]:
    """Embed a batch in one request. Order of the result matches the input order."""
    if not texts:
        return []
    response = await client.embeddings.create(model=deployment, input=texts)
    return [item.embedding for item in response.data]
