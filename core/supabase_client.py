from supabase import create_client, Client
from core.config import Config

# Singleton instance (prevents connection leaks)
_supabase_client = None

def get_supabase_client() -> Client:
    """
    Returns a singleton Supabase client instance.
    This prevents creating multiple connections on every call.
    """
    global _supabase_client
    if _supabase_client is None:
        Config.validate()
        _supabase_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_KEY)
    return _supabase_client
