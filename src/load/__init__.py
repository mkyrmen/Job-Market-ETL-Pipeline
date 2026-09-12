"""Load layer: persistence targets for normalised job records."""

from src.load.sqlite_loader import SQLiteLoader
from src.load.supabase_loader import SupabaseLoader

__all__ = ["SQLiteLoader", "SupabaseLoader"]