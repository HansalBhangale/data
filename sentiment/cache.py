"""
Sentiment Cache - Cache sentiment data to avoid repeated API calls

Caches sentiment results for 24 hours to reduce API usage and improve performance.
"""

import os
import json
import hashlib
from typing import Dict, Optional
from datetime import datetime, timedelta
from pathlib import Path


# Cache directory
CACHE_DIR = Path(__file__).parent.parent / ".sentiment_cache"
CACHE_TTL_HOURS = 24


def _ensure_cache_dir():
    """Ensure cache directory exists."""
    CACHE_DIR.mkdir(exist_ok=True)


def _get_cache_key(identifier: str) -> str:
    """Generate cache key from identifier."""
    return hashlib.md5(identifier.encode()).hexdigest()


def _get_cache_path(key: str) -> Path:
    """Get file path for cache key."""
    return CACHE_DIR / f"{key}.json"


def get_cached_sentiment(identifier: str) -> Optional[Dict]:
    """
    Get cached sentiment data if available and not expired.
    
    Parameters
    ----------
    identifier : str
        Unique identifier (ticker, keyword, etc.)
    
    Returns
    -------
    Dict or None
        Cached sentiment data or None if expired/not found
    """
    _ensure_cache_dir()
    
    key = _get_cache_key(identifier)
    cache_path = _get_cache_path(key)
    
    if not cache_path.exists():
        return None
    
    try:
        with open(cache_path, 'r') as f:
            data = json.load(f)
        
        # Check expiration
        cached_time = datetime.fromisoformat(data.get('cached_at', '2020-01-01'))
        if datetime.now() - cached_time > timedelta(hours=CACHE_TTL_HOURS):
            # Expired - remove old cache
            cache_path.unlink()
            return None
        
        return data.get('sentiment')
    
    except Exception:
        return None


def set_cached_sentiment(identifier: str, sentiment: Dict):
    """
    Cache sentiment data.
    
    Parameters
    ----------
    identifier : str
        Unique identifier (ticker, keyword, etc.)
    sentiment : Dict
        Sentiment data to cache
    """
    _ensure_cache_dir()
    
    key = _get_cache_key(identifier)
    cache_path = _get_cache_path(key)
    
    data = {
        'identifier': identifier,
        'sentiment': sentiment,
        'cached_at': datetime.now().isoformat()
    }
    
    try:
        with open(cache_path, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Warning: Failed to cache sentiment: {e}")


def clear_cache():
    """Clear all cached sentiment data."""
    _ensure_cache_dir()
    
    for cache_file in CACHE_DIR.glob("*.json"):
        try:
            cache_file.unlink()
        except Exception:
            pass


def get_cache_stats() -> Dict:
    """Get cache statistics."""
    _ensure_cache_dir()
    
    files = list(CACHE_DIR.glob("*.json"))
    total_size = sum(f.stat().st_size for f in files)
    
    return {
        'files': len(files),
        'size_bytes': total_size,
        'size_mb': round(total_size / 1024 / 1024, 2)
    }