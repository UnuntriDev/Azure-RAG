"""Shared slowapi Limiter instance.

Uses client IP as the key. In production behind Azure Container Apps / Application Gateway,
forward the real IP via X-Forwarded-For and set FORWARDED_ALLOW_IPS accordingly.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Per-endpoint limits — tune these to match expected demo traffic.
CHAT_LIMIT = "10/minute"
QUERY_LIMIT = "20/minute"
UPLOAD_LIMIT = "5/minute"
ANALYZE_LIMIT = "5/minute"
