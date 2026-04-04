"""
Sentiment Analysis Runner

Entry point for running sentiment analysis on stocks and bonds.
"""

import os
import sys
import pandas as pd
from typing import Dict, List
import streamlit as st

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentiment.news_fetcher import (
    fetch_stock_news,
    fetch_bond_news,
    fetch_multiple_stocks_news,
    get_api_key
)
from sentiment.sentiment_analyzer import (
    analyze_news_articles,
    get_sentiment_score,
    batch_analyze_tickers,
    get_finbert_model
)
from sentiment.bond_sentiment import (
    get_bond_sentiment,
    get_bonds_sentiment,
    BOND_KEYWORDS
)
from sentiment.cache import get_cached_sentiment, set_cached_sentiment


def get_stock_sentiment(
    tickers: List[str],
    use_cache: bool = True,
    max_per_stock: int = 5
) -> Dict[str, float]:
    """
    Get sentiment scores for multiple stock tickers.
    
    Parameters
    ----------
    tickers : List[str]
        List of stock ticker symbols
    use_cache : bool
        Whether to use cached results
    max_per_stock : int
        Maximum news articles per stock
    
    Returns
    -------
    Dict[str, float]
        Dictionary mapping ticker to sentiment score (0-100)
    """
    api_key = get_api_key()
    
    if not api_key:
        print("Warning: No Marketaux API key found")
        return {t: 50.0 for t in tickers}
    
    results = {}
    
    for ticker in tickers:
        # Check cache
        cache_key = f"stock_{ticker}"
        if use_cache:
            cached = get_cached_sentiment(cache_key)
            if cached:
                results[ticker] = cached['score']
                continue
        
        # Fetch news
        news = fetch_stock_news(ticker, api_key, max_per_stock)
        
        # Get sentiment score (0-100)
        score = get_sentiment_score(ticker, news)
        
        # Cache result
        if use_cache:
            set_cached_sentiment(cache_key, {
                'score': score,
                'news_count': len(news)
            })
        
        results[ticker] = score
    
    return results


def get_bond_sentiment_scores(
    tickers: List[str],
    use_cache: bool = True
) -> Dict[str, float]:
    """
    Get sentiment scores for bond ETFs.
    
    Parameters
    ----------
    tickers : List[str]
        List of bond ETF tickers
    use_cache : bool
        Whether to use cached results
    
    Returns
    -------
    Dict[str, float]
        Dictionary mapping ticker to sentiment score (0-100)
    """
    api_key = get_api_key()
    
    if not api_key:
        print("Warning: No Marketaux API key found")
        return {t: 50.0 for t in tickers}
    
    results = {}
    
    for ticker in tickers:
        # Check cache
        cache_key = f"bond_{ticker}"
        if use_cache:
            cached = get_cached_sentiment(cache_key)
            if cached:
                results[ticker] = cached['score']
                continue
        
        # Get sentiment
        sentiment = get_bond_sentiment(ticker, api_key)
        
        # Cache result
        if use_cache:
            set_cached_sentiment(cache_key, sentiment)
        
        results[ticker] = sentiment.get('score', 50.0)
    
    return results


def get_portfolio_sentiment(
    stock_tickers: List[str],
    bond_tickers: List[str],
    stock_weights: List[float],
    bond_weights: List[float]
) -> Dict:
    """
    Get overall portfolio sentiment.
    
    Parameters
    ----------
    stock_tickers : List[str]
        Stock ticker symbols
    bond_tickers : List[str]
        Bond ETF tickers
    stock_weights : List[float]
        Stock weights (0-1)
    bond_weights : List[float]
        Bond weights (0-1)
    
    Returns
    -------
    Dict
        Portfolio sentiment analysis
    """
    # Get individual sentiments
    stock_sentiments = get_stock_sentiment(stock_tickers)
    bond_sentiments = get_bond_sentiment_scores(bond_tickers)
    
    # Calculate weighted average
    total_weight = sum(stock_weights) + sum(bond_weights)
    
    if total_weight > 0:
        stock_contrib = sum(
            stock_sentiments.get(t, 50) * w 
            for t, w in zip(stock_tickers, stock_weights)
        )
        bond_contrib = sum(
            bond_sentiments.get(t, 50) * w 
            for t, w in zip(bond_tickers, bond_weights)
        )
        
        portfolio_score = (stock_contrib + bond_contrib) / total_weight
    else:
        portfolio_score = 50.0
    
    # Determine label
    if portfolio_score > 55:
        label = 'positive'
    elif portfolio_score < 45:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {
        'score': portfolio_score,
        'label': label,
        'stock_sentiments': stock_sentiments,
        'bond_sentiments': bond_sentiments
    }


def test_sentiment_system():
    """Test the sentiment system with sample tickers."""
    print("Testing Sentiment Analysis System...")
    
    api_key = get_api_key()
    if not api_key:
        print("ERROR: No API key found. Set MARKETAUX_API_KEY environment variable.")
        print("Get free API key at: https://marketaux.com")
        return
    
    print(f"API Key found: {api_key[:10]}...")
    
    # Test stock sentiment
    print("\n--- Stock Sentiment Test ---")
    test_stocks = ['AAPL', 'MSFT', 'GOOGL']
    stock_sentiments = get_stock_sentiment(test_stocks)
    
    for ticker, score in stock_sentiments.items():
        label = 'positive' if score > 55 else 'negative' if score < 45 else 'neutral'
        print(f"  {ticker}: {score:.1f} ({label})")
    
    # Test bond sentiment
    print("\n--- Bond Sentiment Test ---")
    test_bonds = ['AGG', 'LQD', 'HYG']
    bond_sentiments = get_bond_sentiment_scores(test_bonds)
    
    for ticker, score in bond_sentiments.items():
        label = 'positive' if score > 55 else 'negative' if score < 45 else 'neutral'
        print(f"  {ticker}: {score:.1f} ({label})")
    
    print("\n--- Test Complete ---")


if __name__ == "__main__":
    # Check for API key
    if "MARKETAUX_API_KEY" not in os.environ:
        print("Note: Set MARKETAUX_API_KEY environment variable for real-time data")
        print("Get free API key at: https://marketaux.com")
        print()
    
    test_sentiment_system()