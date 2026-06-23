"""Azure Monitor OpenTelemetry integration.

Auto-instruments: FastAPI (ASGI spans), SQLAlchemy queries, httpx / requests,
and the OpenAI SDK calls — all exported to Application Insights when enabled.
"""

import logging

_log = logging.getLogger(__name__)


def setup_telemetry(connection_string: str, service_name: str = "azure-rag-backend") -> bool:
    """Configure Azure Monitor via OpenTelemetry SDK.

    Returns True when telemetry is enabled, False when disabled (empty connection string).
    Swallows errors so a misconfigured connection string never takes the app down.
    """
    if not connection_string:
        return False
    try:
        from azure.monitor.opentelemetry import configure_azure_monitor

        configure_azure_monitor(
            connection_string=connection_string,
            service_name=service_name,
        )
        return True
    except Exception as exc:
        _log.warning("Azure Monitor setup failed — telemetry disabled: %s", exc)
        return False
