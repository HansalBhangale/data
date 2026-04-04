"""
Bond-Specific Sentiment Analysis

Provides sentiment analysis specifically tailored for bond ETFs.
"""

from typing import Dict, List, Optional
from .news_fetcher import fetch_bond_news, get_api_key
from .sentiment_analyzer import analyze_news_articles, get_sentiment_score

# Bond ETF keyword mappings for sentiment analysis
# Each bond category has specific search terms relevant to that segment
BOND_KEYWORDS = {
    # Short-term Treasury (Ultra Conservative)
    'SHY': ['Treasury bills', 'short-term Treasury', 'T-Bills rates', 'Fed funds rate'],
    'VGSH': ['short-term Treasury', 'Treasury bills', 'overnight rates'],
    'SCHO': ['short-term Treasury', '1-3 year Treasury', 'Treasury yields'],
    'VCSH': ['short-term corporate bond', 'short-term investment grade'],
    'IGSB': ['short-term investment grade bonds', 'corporate bond yields'],
    
    # Intermediate-term Treasury (Conservative)
    'IEF': ['7-10 year Treasury', 'Treasury note', '10-year yield', 'Fed policy'],
    'SCHR': ['intermediate Treasury', '7-10 year bond', 'Treasury auction'],
    'VCIT': ['intermediate corporate bond', 'investment grade corporate'],
    'IGIB': ['intermediate investment grade', 'corporate bond market'],
    
    # Broad Market (Moderate)
    'AGG': ['aggregate bond market', 'investment grade bonds', 'US bond market', 'Fed rates'],
    'BOND': ['total bond market', 'AGG alternative', 'investment grade'],
    'IUSB': ['US bond aggregate', 'total bond market index'],
    'BND': ['total bond market', 'global bonds', 'aggregate bond'],
    
    # Investment Grade Corporate (Growth)
    'LQD': ['investment grade corporate', 'corporate bond spreads', 'credit quality', 'investment grade'],
    'VCIT': ['corporate bonds', 'investment grade credit', 'credit spreads'],
    'IGIB': ['corporate bonds', 'credit markets', 'IG corporate'],
    
    # High Yield (Aggressive)
    'HYG': ['high yield bonds', 'junk bonds', 'credit risk', 'high yield spreads', 'HY market'],
    'JNK': ['high yield bonds', 'junk bond market', 'credit spreads'],
    'HYLB': ['high yield bonds', 'floating rate high yield'],
    'SJNK': ['junior bonds', 'high yield default'],
    
    # Emerging Markets / Long Duration (Ultra Aggressive)
    'EMB': ['emerging market bonds', 'EM sovereign debt', 'external debt'],
    'TLT': ['long-term Treasury', '20+ year bond', 'long duration', 'Treasury curve'],
    'LTPZ': ['long-duration Treasury', 'long-term TIPS', 'inflation protected'],
    'EDV': ['extended duration Treasury', 'long-term zero coupon'],
    'ZROZ': ['long-term Treasury zero', 'long duration'],
}

# Bond category groupings
BOND_CATEGORIES = {
    'ultra_conservative': ['SHY', 'VGSH', 'SCHO', 'VCSH', 'IGSB'],
    'conservative': ['IEF', 'SCHR', 'VCIT', 'IGIB'],
    'moderate': ['AGG', 'BOND', 'IUSB', 'BND'],
    'growth': ['LQD', 'VCIT', 'IGIB'],
    'aggressive': ['HYG', 'JNK', 'HYLB', 'SJNK'],
    'ultra_aggressive': ['EMB', 'TLT', 'LTPZ', 'EDV', 'ZROZ'],
}

# Sentiment weights for different bond news categories
BOND_SENTIMENT_WEIGHTS = {
    'Fed_policy': 0.30,       # Federal Reserve announcements
    'Treasury_rates': 0.25,   # Treasury yield movements
    'Credit_market': 0.25,    # Credit spreads and quality
    'Macro_economic': 0.20,  # General economic conditions
}


def get_bond_keywords(ticker: str) -> List[str]:
    """
    Get relevant keywords for a bond ETF.
    
    Parameters
    ----------
    ticker : str
        Bond ETF ticker
    
    Returns
    -------
    List[str]
        List of search keywords
    """
    return BOND_KEYWORDS.get(ticker.upper(), ['bond market', 'fixed income', 'Treasury'])


def get_category_keywords(category: str) -> List[str]:
    """
    Get all keywords for a bond category.
    
    Parameters
    ----------
    category : str
        Category name
    
    Returns
    -------
    List[str]
        Combined list of keywords
    """
    tickers = BOND_CATEGORIES.get(category.lower(), [])
    keywords = []
    for ticker in tickers:
        keywords.extend(BOND_KEYWORDS.get(ticker, []))
    return list(set(keywords))  # Remove duplicates


def get_bond_sentiment(
    ticker: str,
    api_key: Optional[str] = None,
    max_keywords: int = 3
) -> Dict:
    """
    Get sentiment for a specific bond ETF.
    
    Parameters
    ----------
    ticker : str
        Bond ETF ticker
    api_key : str, optional
        Marketaux API key
    max_keywords : int
        Maximum keywords to search
    
    Returns
    -------
    Dict
        Sentiment analysis result
    """
    keywords = get_bond_keywords(ticker.upper())
    all_sentiments = []
    articles = []
    
    for keyword in keywords[:max_keywords]:
        news = fetch_bond_news(keyword, api_key, max_results=5)
        if news:
            sentiment = analyze_news_articles(news)
            all_sentiments.append(sentiment)
            articles.extend(news)
    
    if not all_sentiments:
        return {
            'ticker': ticker.upper(),
            'label': 'neutral',
            'score': 50.0,
            'confidence': 0.0,
            'count': 0,
            'articles_analyzed': 0
        }
    
    # Aggregate across all keywords
    avg_score = sum(s.get('score', 0) for s in all_sentiments) / len(all_sentiments)
    avg_confidence = sum(s.get('confidence', 0) for s in all_sentiments) / len(all_sentiments)
    
    # Normalize to 0-100 scale
    normalized_score = (avg_score + 1) * 50
    
    # Determine label
    if avg_score > 0.15:
        label = 'positive'
    elif avg_score < -0.15:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {
        'ticker': ticker.upper(),
        'label': label,
        'score': normalized_score,
        'confidence': avg_confidence,
        'count': len(all_sentiments),
        'articles_analyzed': len(articles),
        'keywords_used': keywords[:max_keywords]
    }


def get_bonds_sentiment(
    tickers: List[str],
    api_key: Optional[str] = None
) -> Dict[str, Dict]:
    """
    Get sentiment for multiple bond ETFs.
    
    Parameters
    ----------
    tickers : List[str]
        List of bond ETF tickers
    api_key : str, optional
        Marketaux API key
    
    Returns
    -------
    Dict[str, Dict]
        Dictionary mapping ticker to sentiment result
    """
    results = {}
    
    for ticker in tickers:
        results[ticker.upper()] = get_bond_sentiment(ticker, api_key)
    
    return results


def get_category_sentiment(
    category: str,
    api_key: Optional[str] = None
) -> Dict:
    """
    Get aggregate sentiment for a bond category.
    
    Parameters
    ----------
    category : str
        Category name (ultra_conservative, conservative, etc.)
    api_key : str, optional
        Marketaux API key
    
    Returns
    -------
    Dict
        Aggregate sentiment for the category
    """
    tickers = BOND_CATEGORIES.get(category.lower(), [])
    
    if not tickers:
        return {
            'category': category,
            'label': 'neutral',
            'score': 50.0,
            'count': 0
        }
    
    sentiments = get_bonds_sentiment(tickers, api_key)
    
    # Aggregate
    scores = [s['score'] for s in sentiments.values() if s.get('score', 0) > 0]
    
    if not scores:
        return {
            'category': category,
            'label': 'neutral',
            'score': 50.0,
            'count': 0
        }
    
    avg_score = sum(scores) / len(scores)
    
    return {
        'category': category,
        'label': 'positive' if avg_score > 55 else 'negative' if avg_score < 45 else 'neutral',
        'score': avg_score,
        'count': len(scores),
        'tickers': tickers
    }


def get_risk_based_bond_sentiment(
    risk_score: float,
    bond_tickers: List[str],
    api_key: Optional[str] = None
) -> Dict:
    """
    Get bond sentiment based on investor risk score.
    
    Parameters
    ----------
    risk_score : float
        Investor risk score (0-100)
    bond_tickers : List[str]
        Bond ETFs in the portfolio
    api_key : str, optional
        Marketaux API key
    
    Returns
    -------
    Dict
        Risk-adjusted bond sentiment
    """
    # Get sentiment for all bonds in portfolio
    sentiments = get_bonds_sentiment(bond_tickers, api_key)
    
    if not sentiments:
        return {
            'score': 50.0,
            'label': 'neutral',
            'count': 0
        }
    
    # Calculate weighted sentiment based on allocation (if weights available)
    scores = [s['score'] for s in sentiments.values() if s.get('score', 0) > 0]
    
    if not scores:
        return {
            'score': 50.0,
            'label': 'neutral',
            'count': 0
        }
    
    avg_sentiment = sum(scores) / len(scores)
    
    # Adjust for risk tolerance
    # Higher risk tolerance = less sensitivity to negative bond sentiment
    risk_factor = risk_score / 100  # 0 to 1
    adjusted_score = 50 + (avg_sentiment - 50) * (1 - risk_factor * 0.3)
    
    return {
        'score': adjusted_score,
        'raw_score': avg_sentiment,
        'label': 'positive' if adjusted_score > 55 else 'negative' if adjusted_score < 45 else 'neutral',
        'count': len(scores),
        'bonds': list(sentiments.keys())
    }