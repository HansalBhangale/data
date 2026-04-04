"""
News Fetcher - Marketaux API Integration

Fetches real-time financial news for stocks and bonds.
"""

import os
import requests
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time
from pathlib import Path

# Try to load from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        print(f"Loaded .env from {env_path}")
except ImportError:
    pass

MARKETAUX_BASE_URL = "https://api.marketaux.com/v1"

# Default API key - can be overridden with environment variable
DEFAULT_API_KEY = os.environ.get("MARKETAUX_API_KEY", "")


def get_api_key() -> str:
    """Get API key from environment or .env file."""
    return os.environ.get("MARKETAUX_API_KEY", DEFAULT_API_KEY)


def fetch_stock_news(
    ticker: str,
    api_key: Optional[str] = None,
    max_results: int = 10
) -> List[Dict]:
    """
    Fetch news for a specific stock ticker.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol (e.g., 'AAPL', 'MSFT')
    api_key : str, optional
        Marketaux API key
    max_results : int
        Maximum number of news articles to fetch
    
    Returns
    -------
    List[Dict]
        List of news articles with content, url, published_at
    """
    api_key = api_key or get_api_key()
    
    if not api_key:
        return []
    
    url = f"{MARKETAUX_BASE_URL}/news/all"
    params = {
        "symbols": ticker.upper(),
        "api_token": api_key,
        "limit": min(max_results, 20),
        "language": "en",
        "published_after": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "filter_entities": "true",
        "must_have_entities": "true",
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        
        # Check for rate limit or payment required
        if response.status_code == 402:
            print(f"Marketaux API limit exceeded for {ticker}")
            return []
        elif response.status_code == 429:
            print(f"Marketaux rate limit exceeded for {ticker}")
            return []
            
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            return data["data"]
        return []
    
    except requests.exceptions.HTTPError as e:
        if e.response.status_code in [402, 429]:
            return []
        print(f"Error fetching news for {ticker}: {e}")
        return []
    except Exception as e:
        print(f"Error fetching news for {ticker}: {e}")
        return []


def fetch_bond_news(
    keywords: str,
    api_key: Optional[str] = None,
    max_results: int = 10
) -> List[Dict]:
    """
    Fetch news related to bonds/fixed income.
    
    Parameters
    ----------
    keywords : str
        Search keywords (e.g., 'Treasury rates', 'Fed policy')
    api_key : str, optional
        Marketaux API key
    max_results : int
        Maximum number of news articles
    
    Returns
    -------
    List[Dict]
        List of news articles
    """
    api_key = api_key or get_api_key()
    
    if not api_key:
        return []
    
    url = f"{MARKETAUX_BASE_URL}/news/all"
    params = {
        "search": keywords,
        "api_token": api_key,
        "limit": min(max_results, 20),
        "language": "en",
        "published_after": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            return data["data"]
        return []
    
    except Exception as e:
        print(f"Error fetching bond news for '{keywords}': {e}")
        return []


def fetch_general_market_sentiment(
    api_key: Optional[str] = None,
    max_results: int = 20
) -> List[Dict]:
    """
    Fetch general market news for overall sentiment.
    
    Parameters
    ----------
    api_key : str, optional
        Marketaux API key
    max_results : int
        Maximum number of articles
    
    Returns
    -------
    List[Dict]
        List of market news articles
    """
    api_key = api_key or get_api_key()
    
    if not api_key:
        return []
    
    url = f"{MARKETAUX_BASE_URL}/news/all"
    params = {
        "search": "stock market OR S&P 500 OR Federal Reserve",
        "api_token": api_key,
        "limit": max_results,
        "language": "en",
        "published_after": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if data.get("data"):
            return data["data"]
        return []
    
    except Exception as e:
        print(f"Error fetching market sentiment: {e}")
        return []


def fetch_multiple_stocks_news(
    tickers: List[str],
    api_key: Optional[str] = None,
    max_per_stock: int = 5,
    delay: float = 0.5
) -> Dict[str, List[Dict]]:
    """
    Fetch news for multiple stock tickers.
    
    Parameters
    ----------
    tickers : List[str]
        List of stock ticker symbols
    api_key : str, optional
        Marketaux API key
    max_per_stock : int
        Maximum articles per stock
    delay : float
        Delay between requests (seconds)
    
    Returns
    -------
    Dict[str, List[Dict]]
        Dictionary mapping ticker to news list
    """
    api_key = api_key or get_api_key()
    results = {}
    
    for ticker in tickers:
        results[ticker] = fetch_stock_news(ticker, api_key, max_per_stock)
        time.sleep(delay)  # Rate limiting
    
    return results


def extract_news_content(news_items: List[Dict]) -> List[str]:
    """
    Extract text content from news items.
    
    Parameters
    ----------
    news_items : List[Dict]
        List of news articles
    
    Returns
    -------
    List[str]
        List of article descriptions/headlines
    """
    contents = []
    
    for item in news_items:
        if item.get("description"):
            contents.append(item["description"])
        elif item.get("title"):
            contents.append(item["title"])
    
    return contents