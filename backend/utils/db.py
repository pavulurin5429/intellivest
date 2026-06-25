from typing import Optional
from .config import get_settings

_client = None


def get_supabase():
    global _client
    if _client is not None:
        return _client
    try:
        from supabase import create_client
        settings = get_settings()
        if settings.supabase_url and settings.supabase_key and settings.supabase_key != "your_supabase_anon_key":
            _client = create_client(settings.supabase_url, settings.supabase_key)
        else:
            return None
    except Exception as e:
        from loguru import logger
        logger.warning(f"Supabase not configured: {e}. Running without DB persistence.")
        return None
    return _client
