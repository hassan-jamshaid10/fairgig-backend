"""
Supabase client — only used in prod (ENV=prod).
Falls back gracefully when credentials are missing.
"""

from functools import lru_cache
from typing import Optional

from shared.config import get_settings

_client = None


@lru_cache
def get_supabase():
    """Return a Supabase client (prod only). Returns None in local env."""
    settings = get_settings()
    if settings.ENV != "prod" or not settings.SUPABASE_URL:
        return None

    try:
        from supabase import create_client, Client  # noqa: F401
        client: Client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
        return client
    except Exception as exc:
        print(f"[supabase] Could not initialise client: {exc}")
        return None
