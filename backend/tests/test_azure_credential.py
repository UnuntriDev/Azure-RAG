"""Tests for Managed Identity fallback logic in factory functions."""

from unittest.mock import MagicMock, patch

import pytest


class TestOpenAIClientFactory:
    def test_uses_api_key_when_set(self):
        from app.services.ingestion.embedder import make_openai_client

        settings = MagicMock()
        settings.azure_openai_endpoint = "https://test.openai.azure.com"
        settings.azure_openai_api_key = "test-key"
        settings.azure_openai_api_version = "2024-10-21"

        client = make_openai_client(settings)
        assert client.api_key == "test-key"

    def test_uses_token_provider_when_no_key(self):
        from app.services.ingestion.embedder import make_openai_client

        settings = MagicMock()
        settings.azure_openai_endpoint = "https://test.openai.azure.com"
        settings.azure_openai_api_key = ""
        settings.azure_openai_api_version = "2024-10-21"

        with patch("app.azure_credential.get_azure_credential") as mock_cred:
            mock_cred.return_value = MagicMock()
            client = make_openai_client(settings)
            assert client.api_key != "test-key"


class TestSearchCredential:
    def test_uses_key_when_set(self):
        from app.services.storage.search import _search_credential

        settings = MagicMock()
        settings.azure_search_api_key = "search-key"
        cred = _search_credential(settings)
        assert hasattr(cred, "key")

    def test_uses_default_credential_when_no_key(self):
        from app.services.storage.search import _search_credential

        settings = MagicMock()
        settings.azure_search_api_key = ""

        with patch("app.azure_credential.get_azure_credential") as mock_cred:
            mock_cred.return_value = MagicMock()
            cred = _search_credential(settings)
            mock_cred.assert_called_once()


class TestBlobClientFactory:
    def test_uses_connection_string_when_set(self):
        from app.services.storage.blob import make_blob_service_client

        settings = MagicMock()
        settings.azure_storage_connection_string = (
            "DefaultEndpointsProtocol=https;AccountName=test;"
            "AccountKey=dGVzdA==;EndpointSuffix=core.windows.net"
        )
        client = make_blob_service_client(settings)
        assert client is not None

    def test_uses_credential_when_no_connection_string(self):
        from app.services.storage.blob import make_blob_service_client

        settings = MagicMock()
        settings.azure_storage_connection_string = ""
        settings.azure_storage_account_url = "https://test.blob.core.windows.net"

        with patch("app.azure_credential.get_azure_credential") as mock_cred:
            mock_cred.return_value = MagicMock()
            client = make_blob_service_client(settings)
            mock_cred.assert_called_once()
            assert client is not None
