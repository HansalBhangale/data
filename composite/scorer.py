"""
Composite Scorer — combines fundamental and technical model predictions.

Uses IC-weighted combination based on walk-forward validation results:
  Fundamental IC: 0.120  → weight = 0.120 / (0.120 + 0.185) ≈ 0.40
  Technical IC:   0.185  → weight = 0.185 / (0.120 + 0.185) ≈ 0.60
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple


# Default IC-weighted weights (from walk-forward CV)
DEFAULT_FUND_WEIGHT = 0.40
DEFAULT_TECH_WEIGHT = 0.60


def compute_composite_scores(
    fundamental_scores: Dict[str, float],
    technical_scores: Dict[str, float],
    fund_weight: float = DEFAULT_FUND_WEIGHT,
    tech_weight: float = DEFAULT_TECH_WEIGHT,
) -> pd.DataFrame:
    """
    Combine fundamental and technical predictions into composite scores.

    Parameters
    ----------
    fundamental_scores : Dict[str, float]
        {ticker: score_0_to_1} from fundamental model
    technical_scores : Dict[str, float]
        {ticker: score_0_to_1} from technical model
    fund_weight : float
        Weight for fundamental scores (default 0.40)
    tech_weight : float
        Weight for technical scores (default 0.60)

    Returns
    -------
    pd.DataFrame
        Columns: ticker, fundamental_score, technical_score, composite_score
    """
    fund_tickers = {str(k): v for k, v in fundamental_scores.items() if isinstance(k, str) and k.strip()}
    tech_tickers = {str(k): v for k, v in technical_scores.items() if isinstance(k, str) and k.strip()}

    all_tickers = sorted(set(fund_tickers.keys()) | set(tech_tickers.keys()))

    records = []
    for ticker in all_tickers:
        fund = fund_tickers.get(ticker, 0.5)
        tech = tech_tickers.get(ticker, 0.5)
        composite = fund_weight * fund + tech_weight * tech
        records.append({
            'ticker': ticker,
            'fundamental_score': round(fund, 4),
            'technical_score': round(tech, 4),
            'composite_score': round(composite, 4),
        })

    df = pd.DataFrame(records)
    df = df.sort_values('composite_score', ascending=False).reset_index(drop=True)

    print(f"\nComposite Scores:")
    print(f"  Tickers: {len(df)}")
    print(f"  Weights: Fund={fund_weight:.0%}, Tech={tech_weight:.0%}")
    print(f"  Score range: {df['composite_score'].min():.4f} - {df['composite_score'].max():.4f}")
    print(f"  Mean: {df['composite_score'].mean():.4f}")

    return df
