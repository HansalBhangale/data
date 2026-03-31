"""
Rate Limiter & SEC-Compliant HTTP Client
=========================================
Token-bucket rate limiter capped at ≤10 req/sec for SEC EDGAR compliance.
Includes exponential backoff with jitter, transparent JSON caching,
and User-Agent rotation.
"""

import json
import hashlib
import logging
import random
import time
from pathlib import Path
from typing import Optional

import requests

from . import config

logger = logging.getLogger(__name__)


class RateLimiter:
    """Token-bucket rate limiter for SEC EDGAR API compliance."""

    def __init__(self, rate: float = config.SEC_REQUESTS_PER_SECOND):
        self.rate = rate
        self.interval = 1.0 / rate
        self._last_request_time = 0.0

    def wait(self):
        """Block until it's safe to make the next request."""
        now = time.monotonic()
        elapsed = now - self._last_request_time
        if elapsed < self.interval:
            sleep_time = self.interval - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.monotonic()


class SECClient:
    """
    SEC EDGAR API client with rate limiting, retry logic, and caching.
    
    Features:
    - Token-bucket rate limiter (≤10 req/sec)
    - Exponential backoff with jitter on 429/5xx errors
    - Transparent JSON response caching
    - User-Agent rotation on rate-limit hits
    - Connection pooling via requests.Session
    """

    def __init__(self):
        self.session = requests.Session()
        self.rate_limiter = RateLimiter()
        self._current_agent_idx = 0
        self._update_user_agent()
        self.session.headers.update({
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate",
        })

    def _update_user_agent(self):
        """Set the current User-Agent header."""
        agent = config.SEC_USER_AGENTS[self._current_agent_idx]
        self.session.headers["User-Agent"] = agent
        logger.debug(f"Using User-Agent: {agent}")

    def _rotate_user_agent(self):
        """Switch to the next User-Agent email on rate-limit."""
        self._current_agent_idx = (self._current_agent_idx + 1) % len(config.SEC_USER_AGENTS)
        self._update_user_agent()
        logger.warning(f"Rotated to User-Agent index {self._current_agent_idx}")

    def _get_cache_path(self, url: str, cache_dir: Path) -> Path:
        """Generate a deterministic cache file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        # Extract a readable name from the URL (e.g., CIK number)
        parts = url.rstrip(".json").split("/")
        name = parts[-1] if parts else url_hash
        return cache_dir / f"{name}.json"

    def _is_cache_valid(self, cache_path: Path) -> bool:
        """Check if a cached file exists and is within the expiry window."""
        if not config.CACHE_ENABLED:
            return False
        if not cache_path.exists():
            return False
        age_hours = (time.time() - cache_path.stat().st_mtime) / 3600
        return age_hours < config.CACHE_EXPIRY_HOURS

    def get_json(
        self,
        url: str,
        cache_dir: Optional[Path] = None,
        force_refresh: bool = False,
    ) -> Optional[dict]:
        """
        Fetch JSON from a URL with rate limiting, caching, and retries.
        
        Args:
            url: The URL to fetch
            cache_dir: Directory for caching responses. None = no caching.
            force_refresh: Skip cache and re-download
            
        Returns:
            Parsed JSON as dict, or None on failure
        """
        # Check cache first
        if cache_dir and not force_refresh:
            cache_path = self._get_cache_path(url, cache_dir)
            if self._is_cache_valid(cache_path):
                try:
                    with open(cache_path, "r", encoding="utf-8") as f:
                        return json.load(f)
                except (json.JSONDecodeError, IOError):
                    logger.warning(f"Corrupt cache file {cache_path}, re-downloading")

        # Fetch from network with retries
        for attempt in range(config.SEC_MAX_RETRIES):
            self.rate_limiter.wait()

            try:
                response = self.session.get(url, timeout=30)

                if response.status_code == 200:
                    data = response.json()
                    # Save to cache
                    if cache_dir:
                        cache_path = self._get_cache_path(url, cache_dir)
                        cache_path.parent.mkdir(parents=True, exist_ok=True)
                        with open(cache_path, "w", encoding="utf-8") as f:
                            json.dump(data, f)
                    return data

                elif response.status_code == 404:
                    logger.warning(f"404 Not Found: {url}")
                    return None

                elif response.status_code == 429:
                    # Rate limited - rotate User-Agent and back off
                    self._rotate_user_agent()
                    backoff = min(
                        config.SEC_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1),
                        config.SEC_BACKOFF_MAX,
                    )
                    logger.warning(
                        f"429 Rate Limited on attempt {attempt+1}/{config.SEC_MAX_RETRIES}. "
                        f"Backing off {backoff:.1f}s"
                    )
                    time.sleep(backoff)

                elif response.status_code >= 500:
                    # Server error - retry with backoff
                    backoff = min(
                        config.SEC_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1),
                        config.SEC_BACKOFF_MAX,
                    )
                    logger.warning(
                        f"{response.status_code} Server Error on attempt {attempt+1}. "
                        f"Backing off {backoff:.1f}s"
                    )
                    time.sleep(backoff)

                else:
                    logger.error(f"Unexpected status {response.status_code} for {url}")
                    return None

            except requests.exceptions.Timeout:
                backoff = config.SEC_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Timeout on attempt {attempt+1}. Backing off {backoff:.1f}s")
                time.sleep(backoff)

            except requests.exceptions.ConnectionError as e:
                backoff = config.SEC_BACKOFF_BASE * (2 ** attempt) + random.uniform(0, 1)
                logger.warning(f"Connection error on attempt {attempt+1}: {e}. Backing off {backoff:.1f}s")
                time.sleep(backoff)

            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed for {url}: {e}")
                return None

        logger.error(f"Failed after {config.SEC_MAX_RETRIES} attempts: {url}")
        return None

    def close(self):
        """Close the underlying session."""
        self.session.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
