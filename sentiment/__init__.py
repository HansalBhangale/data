"""
Sentiment Analysis Module

Provides real-time sentiment analysis for stocks and bonds using:
- Yahoo Finance + FinBERT (primary, free, unlimited)
- Marketaux API + FinBERT (fallback)
- Pre-computed CSV files (fallback)
"""

from .news_fetcher import fetch_stock_news, fetch_bond_news, fetch_general_market_sentiment
from .sentiment_analyzer import analyze_news_articles, get_sentiment_score, get_finbert_model
from .bond_sentiment import get_bond_sentiment, BOND_KEYWORDS
from .run_sentiment import get_stock_sentiment, get_bond_sentiment_scores
from .yahoo_sentiment import get_sentiment_from_yahoo, get_stock_sentiment_yahoo, get_bond_sentiment_yahoo

__all__ = [
    'fetch_stock_news',
    'fetch_bond_news', 
    'fetch_general_market_sentiment',
    'analyze_news_articles',
    'get_sentiment_score',
    'get_finbert_model',
    'get_bond_sentiment',
    'BOND_KEYWORDS',
    'get_stock_sentiment',
    'get_bond_sentiment_scores',
    'get_sentiment_from_yahoo',
    'get_stock_sentiment_yahoo',
    'get_bond_sentiment_yahoo',
]