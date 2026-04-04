"""
Composite Scorer — combines fundamental, technical, and sentiment model predictions.

Uses IC-weighted combination based on walk-forward validation results:
  Fundamental IC: 0.120  → weight = 0.35 (includes sentiment adjustment)
  Technical IC:   0.185  → weight = 0.55 (includes sentiment adjustment)
  Sentiment:                weight = 0.10 (new component)
"""

import pandas as pd
import numpy as np
import os
from typing import Dict, Optional


# Default weights (from IC analysis + sentiment)
DEFAULT_FUND_WEIGHT = 0.35
DEFAULT_TECH_WEIGHT = 0.55
DEFAULT_SENTIMENT_WEIGHT = 0.10


def compute_composite_scores(
    fundamental_scores: Dict[str, float],
    technical_scores: Dict[str, float],
    sentiment_scores: Optional[Dict[str, float]] = None,
    fund_weight: float = DEFAULT_FUND_WEIGHT,
    tech_weight: float = DEFAULT_TECH_WEIGHT,
    sentiment_weight: float = DEFAULT_SENTIMENT_WEIGHT,
) -> pd.DataFrame:
    """
    Combine fundamental, technical, and sentiment predictions into composite scores.

    Parameters
    ----------
    fundamental_scores : Dict[str, float]
        {ticker: score_0_to_1} from fundamental model
    technical_scores : Dict[str, float]
        {ticker: score_0_to_1} from technical model
    sentiment_scores : Dict[str, float], optional
        {ticker: score_0_to_100} from sentiment analysis
        Will be normalized to 0-1 scale
    fund_weight : float
        Weight for fundamental scores (default 0.35)
    tech_weight : float
        Weight for technical scores (default 0.55)
    sentiment_weight : float
        Weight for sentiment scores (default 0.10)

    Returns
    -------
    pd.DataFrame
        Columns: ticker, fundamental_score, technical_score, sentiment_score, composite_score
    """
    # Normalize sentiment scores from 0-100 to 0-1
    normalized_sentiment = {}
    if sentiment_scores:
        for ticker, score in sentiment_scores.items():
            normalized_sentiment[str(ticker)] = score / 100.0  # Convert 0-100 to 0-1
    else:
        # Default to neutral (0.5) if no sentiment data
        print("  Note: No sentiment scores provided, using neutral (0.5)")
    
    fund_tickers = {str(k): v for k, v in fundamental_scores.items() if isinstance(k, str) and k.strip()}
    tech_tickers = {str(k): v for k, v in technical_scores.items() if isinstance(k, str) and k.strip()}
    sent_tickers = {str(k): v for k, v in normalized_sentiment.items()}

    all_tickers = sorted(set(fund_tickers.keys()) | set(tech_tickers.keys()) | set(sent_tickers.keys()))

    records = []
    for ticker in all_tickers:
        fund = fund_tickers.get(ticker, 0.5)
        tech = tech_tickers.get(ticker, 0.5)
        sent = sent_tickers.get(ticker, 0.5)  # Default to neutral
        
        composite = fund_weight * fund + tech_weight * tech + sentiment_weight * sent
        
        records.append({
            'ticker': ticker,
            'fundamental_score': round(fund, 4),
            'technical_score': round(tech, 4),
            'sentiment_score': round(sent, 4),
            'composite_score': round(composite, 4),
        })

    df = pd.DataFrame(records)
    df = df.sort_values('composite_score', ascending=False).reset_index(drop=True)

    # Check if sentiment is being used
    has_sentiment = sentiment_scores is not None and len(sentiment_scores) > 0
    
    print(f"\nComposite Scores:")
    print(f"  Tickers: {len(df)}")
    print(f"  Weights: Fund={fund_weight:.0%}, Tech={tech_weight:.0%}, Sentiment={sentiment_weight:.0%}")
    if has_sentiment:
        print(f"  Sentiment stocks: {len(sentiment_scores)}")
        sent_mean = df['sentiment_score'].mean()
        print(f"  Sentiment mean: {sent_mean:.4f}")
    print(f"  Score range: {df['composite_score'].min():.4f} - {df['composite_score'].max():.4f}")
    print(f"  Mean: {df['composite_score'].mean():.4f}")

    return df


def compute_composite_scores_legacy(
    fundamental_scores: Dict[str, float],
    technical_scores: Dict[str, float],
    fund_weight: float = DEFAULT_FUND_WEIGHT,
    tech_weight: float = DEFAULT_TECH_WEIGHT,
) -> pd.DataFrame:
    """
    Legacy function for backward compatibility (no sentiment).
    """
    return compute_composite_scores(
        fundamental_scores,
        technical_scores,
        sentiment_scores=None,
        fund_weight=fund_weight / (1 - DEFAULT_SENTIMENT_WEIGHT),
        tech_weight=tech_weight / (1 - DEFAULT_SENTIMENT_WEIGHT),
        sentiment_weight=0,
    )