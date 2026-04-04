"""
Yahoo Finance Sentiment Fetcher

Uses Yahoo Finance (yfinance) to get news and FinBERT for sentiment analysis.
This is a free alternative to Marketaux API with no rate limits.
"""

import yfinance as yf
from typing import List, Dict, Optional
from sentiment.sentiment_analyzer import analyze_texts, aggregate_sentiment
import time


def get_yahoo_news(ticker: str, max_news: int = 5) -> List[str]:
    """
    Get news titles for a ticker from Yahoo Finance.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    max_news : int
        Maximum number of news articles to fetch
    
    Returns
    -------
    List[str]
        List of news titles
    """
    try:
        stock = yf.Ticker(ticker)
        news = stock.news
        
        if not news:
            return []
        
        titles = []
        for item in news[:max_news]:
            title = item.get('content', {}).get('title', '')
            if title:
                titles.append(title)
        
        return titles
    
    except Exception:
        return []


def get_sentiment_from_yahoo(ticker: str, max_news: int = 5) -> Dict:
    """
    Get sentiment score for a ticker using Yahoo Finance + FinBERT.
    
    Parameters
    ----------
    ticker : str
        Stock ticker symbol
    max_news : int
        Maximum number of news articles
    
    Returns
    -------
    Dict
        {'label': str, 'score': float, 'count': int}
    """
    titles = get_yahoo_news(ticker, max_news)
    
    if not titles:
        return {
            'label': 'neutral',
            'score': 50.0,
            'count': 0,
            'source': 'yahoo'
        }
    
    sentiments = analyze_texts(titles)
    result = aggregate_sentiment(sentiments)
    
    # Convert -1 to +1 scale to 0-100 scale
    normalized_score = (result['score'] + 1) * 50
    
    return {
        'label': result['label'],
        'score': normalized_score,
        'count': len(titles),
        'source': 'yahoo'
    }


def get_stock_sentiment_yahoo(tickers: List[str], max_per_stock: int = 5) -> Dict[str, float]:
    """
    Get sentiment scores for multiple stocks.
    
    Parameters
    ----------
    tickers : List[str]
        List of stock tickers
    max_per_stock : int
        Maximum news articles per stock
    
    Returns
    -------
    Dict[str, float]
        {ticker: sentiment_score_0_to_100}
    """
    results = {}
    
    for ticker in tickers:
        try:
            sentiment = get_sentiment_from_yahoo(ticker, max_per_stock)
            results[ticker] = sentiment['score']
            time.sleep(0.1)  # Be nice to Yahoo Finance
        except Exception:
            results[ticker] = 50.0  # Default to neutral
    
    return results


def get_bond_sentiment_yahoo(tickers: List[str]) -> Dict[str, float]:
    """
    Get sentiment scores for bond ETFs using Yahoo Finance.
    
    Parameters
    ----------
    tickers : List[str]
        List of bond ETF tickers
    
    Returns
    -------
    Dict[str, float]
        {ticker: sentiment_score_0_to_100}
    """
    results = {}
    
    # Bond-related keywords for search
    bond_keywords = {
        'SHY': ['Treasury', 'bonds', 'Fed'],
        'IEF': ['Treasury', 'bonds', 'yield'],
        'AGG': ['bonds', 'aggregate', 'fixed income'],
        'LQD': ['corporate bonds', 'credit'],
        'HYG': ['high yield', 'junk bonds'],
        'TLT': ['Treasury', 'long-term', 'bonds'],
        'EMB': ['emerging markets', 'bonds'],
    }
    
    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            news = stock.news
            
            if not news:
                # Try with keywords
                keywords = bond_keywords.get(ticker, ['bonds', 'fixed income'])
                news = stock.news
            
            if news:
                titles = [item.get('content', {}).get('title', '') for item in news[:3]]
                if titles:
                    sentiments = analyze_texts(titles)
                    result = aggregate_sentiment(sentiments)
                    results[ticker] = (result['score'] + 1) * 50
                else:
                    results[ticker] = 50.0
            else:
                results[ticker] = 50.0
                
            time.sleep(0.1)
            
        except Exception:
            results[ticker] = 50.0
    
    return results


if __name__ == "__main__":
    # Test
    print("Testing Yahoo Finance Sentiment...")
    
    test_stocks = ['AAPL', 'MSFT', 'NVDA', 'GOOGL', 'META', 'TSLA']
    
    for stock in test_stocks:
        result = get_sentiment_from_yahoo(stock, 5)
        print(f"  {stock}: {result['label']} ({result['score']:.0f}/100)")
    
    print("\nTesting bonds...")
    test_bonds = ['AGG', 'LQD', 'HYG', 'TLT']
    
    for bond in test_bonds:
        result = get_sentiment_from_yahoo(bond, 3)
        print(f"  {bond}: {result['label']} ({result['score']:.0f}/100)")