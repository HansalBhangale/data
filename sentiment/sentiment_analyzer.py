"""
Sentiment Analyzer - FinBERT Integration

Uses FinBERT model for financial sentiment analysis.
Model is cached locally in the project folder for portability.
"""

import os
import torch
import pandas as pd
from typing import List, Dict, Optional, Tuple
from pathlib import Path
from transformers import AutoModelForSequenceClassification, AutoTokenizer
import warnings

warnings.filterwarnings('ignore')

# Model name for FinBERT
FINBERT_MODEL_NAME = "ProsusAI/finbert"

# Local model cache directory in project folder
LOCAL_MODEL_CACHE = Path(__file__).parent.parent / '.model_cache'

# Create cache directory if it doesn't exist
LOCAL_MODEL_CACHE.mkdir(parents=True, exist_ok=True)

# Global model and tokenizer (lazy loaded)
_model = None
_tokenizer = None


def get_finbert_model() -> Tuple:
    """
    Load FinBERT model and tokenizer (lazy loading).
    Model is downloaded to local project cache (.model_cache folder).
    
    Returns
    -------
    Tuple
        (model, tokenizer)
    """
    global _model, _tokenizer
    
    if _model is None or _tokenizer is None:
        print(f"Loading FinBERT model to local cache: {LOCAL_MODEL_CACHE}")
        _tokenizer = AutoTokenizer.from_pretrained(
            FINBERT_MODEL_NAME,
            cache_dir=LOCAL_MODEL_CACHE
        )
        _model = AutoModelForSequenceClassification.from_pretrained(
            FINBERT_MODEL_NAME,
            cache_dir=LOCAL_MODEL_CACHE
        )
        _model.eval()
        print("FinBERT model loaded successfully")
    
    return _model, _tokenizer


def analyze_single_text(text: str) -> Dict:
    """
    Analyze sentiment of a single text.
    
    Parameters
    ----------
    text : str
        Text to analyze
    
    Returns
    -------
    Dict
        {'label': str, 'score': float, 'confidence': float}
        label: 'positive', 'negative', or 'neutral'
        score: -1 (negative) to +1 (positive)
        confidence: probability of the prediction
    """
    if not text or len(text.strip()) < 5:
        return {'label': 'neutral', 'score': 0.0, 'confidence': 0.33}
    
    try:
        model, tokenizer = get_finbert_model()
        
        inputs = tokenizer(
            text, 
            return_tensors="pt", 
            truncation=True, 
            max_length=512,
            padding=True
        )
        
        with torch.no_grad():
            outputs = model(**inputs)
            probs = torch.softmax(outputs.logits, dim=1)[0]
        
        # FinBERT outputs: [negative, neutral, positive]
        labels = ['negative', 'neutral', 'positive']
        pred_idx = torch.argmax(probs).item()
        confidence = probs[pred_idx].item()
        
        label = labels[pred_idx]
        
        # Convert to -1 to +1 scale
        if label == 'positive':
            score = confidence
        elif label == 'negative':
            score = -confidence
        else:
            score = 0.0
        
        return {
            'label': label,
            'score': score,
            'confidence': confidence,
            'probs': {
                'negative': probs[0].item(),
                'neutral': probs[1].item(),
                'positive': probs[2].item()
            }
        }
    
    except Exception as e:
        return {'label': 'neutral', 'score': 0.0, 'confidence': 0.33}


def analyze_texts(texts: List[str]) -> List[Dict]:
    """
    Analyze sentiment for multiple texts.
    
    Parameters
    ----------
    texts : List[str]
        List of texts to analyze
    
    Returns
    -------
    List[Dict]
        List of sentiment results
    """
    return [analyze_single_text(text) for text in texts]


def aggregate_sentiment(sentiments: List[Dict]) -> Dict:
    """
    Aggregate multiple sentiment scores into one.
    
    Parameters
    ----------
    sentiments : List[Dict]
        List of sentiment dictionaries
    
    Returns
    -------
    Dict
        Aggregated sentiment with weighted scores
    """
    if not sentiments:
        return {'label': 'neutral', 'score': 0.0, 'confidence': 0.0, 'count': 0}
    
    # Calculate weighted average score
    total_score = sum(s['score'] for s in sentiments)
    total_confidence = sum(s['confidence'] for s in sentiments)
    
    avg_score = total_score / len(sentiments)
    avg_confidence = total_confidence / len(sentiments)
    
    # Determine label
    if avg_score > 0.15:
        label = 'positive'
    elif avg_score < -0.15:
        label = 'negative'
    else:
        label = 'neutral'
    
    return {
        'label': label,
        'score': avg_score,
        'confidence': avg_confidence,
        'count': len(sentiments),
        'positive_pct': sum(1 for s in sentiments if s['label'] == 'positive') / len(sentiments) * 100,
        'negative_pct': sum(1 for s in sentiments if s['label'] == 'negative') / len(sentiments) * 100,
        'neutral_pct': sum(1 for s in sentiments if s['label'] == 'neutral') / len(sentiments) * 100,
    }


def analyze_news_articles(news_items: List[Dict]) -> Dict:
    """
    Analyze sentiment for a list of news articles.
    
    Uses Marketaux's built-in sentiment if available, otherwise falls back to FinBERT.
    
    Parameters
    ----------
    news_items : List[Dict]
        List of news articles from Marketaux
    
    Returns
    -------
    Dict
        Aggregated sentiment analysis
    """
    if not news_items:
        return {'label': 'neutral', 'score': 0.0, 'confidence': 0.0, 'count': 0}
    
    # Check if Marketaux provides sentiment scores in entities
    marketaux_scores = []
    finbert_texts = []
    
    for item in news_items:
        # Extract Marketaux entity sentiments
        if item.get('entities'):
            for entity in item.get('entities', []):
                if entity.get('sentiment_score') is not None:
                    marketaux_scores.append(entity['sentiment_score'])
        
        # Also collect text for FinBERT analysis
        text = item.get('description') or item.get('title') or ''
        if text:
            finbert_texts.append(text)
    
    # Use Marketaux scores if available, otherwise fall back to FinBERT
    if marketaux_scores:
        avg_score = sum(marketaux_scores) / len(marketaux_scores)
        
        # Map -1 to +1 → 0 to 100
        normalized_score = (avg_score + 1) * 50
        
        return {
            'label': 'positive' if avg_score > 0.1 else 'negative' if avg_score < -0.1 else 'neutral',
            'score': avg_score,
            'confidence': 0.8,
            'count': len(marketaux_scores),
            'source': 'marketaux',
            'normalized_score': normalized_score,
            'positive_pct': sum(1 for s in marketaux_scores if s > 0.1) / len(marketaux_scores) * 100,
            'negative_pct': sum(1 for s in marketaux_scores if s < -0.1) / len(marketaux_scores) * 100,
            'neutral_pct': sum(1 for s in marketaux_scores if -0.1 <= s <= 0.1) / len(marketaux_scores) * 100,
        }
    
    # Fall back to FinBERT if no Marketaux sentiment
    if not finbert_texts:
        return {'label': 'neutral', 'score': 0.0, 'confidence': 0.0, 'count': 0}
    
    sentiments = analyze_texts(finbert_texts)
    result = aggregate_sentiment(sentiments)
    result['source'] = 'finbert'
    result['normalized_score'] = (result['score'] + 1) * 50
    result['articles_analyzed'] = len(finbert_texts)
    
    return result


def get_sentiment_score(ticker: str, news_items: List[Dict]) -> float:
    """
    Get normalized sentiment score for a ticker.
    
    Parameters
    ----------
    ticker : str
        Stock ticker
    news_items : List[Dict]
        News articles for the ticker
    
    Returns
    -------
    float
        Sentiment score normalized to 0-100 scale
        50 = neutral, 100 = very positive, 0 = very negative
    """
    result = analyze_news_articles(news_items)
    
    # Use normalized_score if available (0-100 scale), otherwise compute
    if 'normalized_score' in result:
        return result['normalized_score']
    
    # Fallback: normalize from -1 to +1 → 0 to 100
    normalized_score = (result['score'] + 1) * 50
    
    return normalized_score


def batch_analyze_tickers(
    ticker_news: Dict[str, List[Dict]],
    cache: bool = True
) -> Dict[str, float]:
    """
    Analyze sentiment for multiple tickers.
    
    Parameters
    ----------
    ticker_news : Dict[str, List[Dict]]
        Dictionary mapping ticker to news list
    cache : bool
        Whether to cache results
    
    Returns
    -------
    Dict[str, float]
        Dictionary mapping ticker to sentiment score (0-100)
    """
    results = {}
    
    for ticker, news in ticker_news.items():
        results[ticker] = get_sentiment_score(ticker, news)
    
    return results