import json
import os
import hashlib
import time
import logging
import pandas as pd
from typing import Optional, Dict

# Cache TTL in seconds (24 hours by default)
CACHE_TTL_SECONDS = 24 * 60 * 60

class CacheManager:
    @staticmethod
    def _get_cache_path(client_id: str) -> str:
        # Sanitize client_id just in case
        safe_id = "".join([c for c in client_id if c.isalnum() or c in ('-', '_')])
        return f"analysis_cache_{safe_id}.json"

    @staticmethod
    def _load_cache(client_id: str) -> Dict:
        path = CacheManager._get_cache_path(client_id)
        if not os.path.exists(path):
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            
            # Check TTL
            cached_at = cache_data.get('_cached_at', 0)
            if time.time() - cached_at > CACHE_TTL_SECONDS:
                logging.debug(f"Cache expired for {client_id}")
                return {}
            return cache_data
        except (json.JSONDecodeError, IOError, OSError) as e:
            logging.debug(f"Cache load failed: {type(e).__name__}")
            return {}

    @staticmethod
    def _save_cache(client_id: str, cache: Dict):
        path = CacheManager._get_cache_path(client_id)
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Cache save failed: {e}")

    @staticmethod
    def get_analysis(client_id: str, input_hash: str) -> Optional[Dict]:
        """
        Retrieves analysis result if input_hash matches.
        """
        if not client_id:
            return None
        cache = CacheManager._load_cache(client_id)
        if cache.get('input_hash') == input_hash:
            return cache.get('result')
        return None

    @staticmethod
    def set_analysis(client_id: str, input_hash: str, result: Dict):
        """
        Saves analysis result.
        """
        if not client_id:
            return
        # Per client file, so we just overwrite/update the single entry for now
        # Or if we want history, we can store list. For now, strict cache: 1 hash = 1 result
        cache = {
            'input_hash': input_hash,
            'result': result,
            '_cached_at': time.time()  # TTL support
        }
        CacheManager._save_cache(client_id, cache)

    @staticmethod
    def generate_input_hash(fin_df, sales_df, docs_meta) -> str:
        """
        Generates a hash from inputs to detect changes.
        Uses hash_pandas_object with index=True for index sensitivity.
        """
        s = ""
        if fin_df is not None:
             s += str(pd.util.hash_pandas_object(fin_df, index=True).sum())
        if sales_df is not None:
             s += str(pd.util.hash_pandas_object(sales_df, index=True).sum())
        # docs_meta is list of (name, size)
        s += str(docs_meta)
        
        return hashlib.md5(s.encode('utf-8')).hexdigest()
