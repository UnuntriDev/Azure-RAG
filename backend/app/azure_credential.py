"""Shared Azure credential factory.

Uses DefaultAzureCredential which auto-detects the environment:
- Managed Identity on Azure Container Apps / App Service
- Azure CLI login on developer machines
- Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)

Only instantiated when API keys are not configured — local dev with keys works unchanged.
"""

import functools

from azure.identity.aio import DefaultAzureCredential


@functools.cache
def get_azure_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential()
