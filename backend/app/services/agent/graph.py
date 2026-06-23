"""ReAct agent wiring via LangGraph's prebuilt create_react_agent (reason→act→observe)."""

from langchain_core.language_models import BaseChatModel
from langchain_core.tools import BaseTool
from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import create_react_agent

from app.config import Settings
from app.services.agent.prompts import AGENT_SYSTEM_PROMPT


def make_chat_model(settings: Settings) -> AzureChatOpenAI:
    """LangChain chat model bound to our Azure OpenAI chat deployment."""
    kwargs: dict = {
        "azure_endpoint": settings.azure_openai_endpoint,
        "api_version": settings.azure_openai_api_version,
        "azure_deployment": settings.azure_openai_chat_deployment,
        "temperature": 0.1,
        "timeout": 60,
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
    return AzureChatOpenAI(**kwargs)


def build_agent(model: BaseChatModel, tools: list[BaseTool], prompt: str | None = None):
    """ReAct agent with our system prompt. Returns a compiled LangGraph runnable."""
    return create_react_agent(model, tools, prompt=prompt or AGENT_SYSTEM_PROMPT)
