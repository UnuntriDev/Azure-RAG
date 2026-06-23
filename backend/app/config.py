from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ── Postgres ──
    database_url: str = "postgresql+asyncpg://rag:rag@localhost:5432/rag"

    # ── Azure OpenAI ──
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2024-10-21"
    azure_openai_chat_deployment: str = "gpt-4o-mini"
    azure_openai_embedding_deployment: str = "text-embedding-3-small"

    # ── Azure AI Search ──
    azure_search_endpoint: str = ""
    azure_search_api_key: str = ""
    azure_search_index_name: str = "rag-chunks"
    # Optional: name of the semantic configuration on the index (requires Basic tier or higher).
    # Leave empty to use hybrid BM25 + vector without semantic reranking.
    azure_search_semantic_config: str = ""

    # ── Azure Blob ──
    azure_storage_connection_string: str = ""
    azure_storage_account_url: str = ""
    azure_storage_container: str = "documents"

    # ── Google OAuth (auth) ──
    # Leave empty to disable auth in local dev (all requests anonymous).
    google_client_id: str = ""

    # ── Redis (cache) ──
    # Leave empty to disable caching (get/set become no-ops).
    redis_url: str = ""

    # ── Azure Monitor (Application Insights) ──
    # Leave empty to disable telemetry.
    # Get from Portal → Application Insights → Overview → Connection string.
    applicationinsights_connection_string: str = ""

    # ── Session cookie ──
    cookie_secure: bool = False
    cookie_domain: str = ""
    # "lax" works when frontend+backend share a site (dev, or nginx reverse-proxy).
    # For cross-site prod (frontend and API on different domains) set "none" + cookie_secure=true,
    # otherwise the browser won't send the cookie on credentialed fetch.
    cookie_samesite: str = "lax"

    # ── App ──
    cors_origins: str = "http://localhost:3000"
    log_level: str = "INFO"
    # Off locally; set DB_SSL_REQUIRE=true on the Container App
    # (Azure Flexible Server enforces TLS).
    db_ssl_require: bool = False
    max_upload_mb: int = 50
    https_redirect: bool = False

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
