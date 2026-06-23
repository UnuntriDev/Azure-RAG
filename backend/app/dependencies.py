"""FastAPI dependencies — long-lived Azure clients from app.state (created in lifespan)."""

from azure.search.documents.aio import SearchClient
from azure.storage.blob.aio import BlobServiceClient
from fastapi import Request
from openai import AsyncAzureOpenAI


def get_blob_service(request: Request) -> BlobServiceClient:
    return request.app.state.blob_client


def get_search_client(request: Request) -> SearchClient:
    return request.app.state.search_client


def get_openai_client(request: Request) -> AsyncAzureOpenAI:
    return request.app.state.openai_client
