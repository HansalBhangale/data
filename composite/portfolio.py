"""
Risk-Matched Portfolio Construction.

Assigns stocks to risk buckets, matches investor risk profile to appropriate
buckets, and constructs optimized long-only portfolios.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple


# Investor risk profile → assigned stock buckets
INVESTOR_BUCKET_MAP = {
    (0, 20):   [1],        # Ultra Conservative → safest stocks only
    (21, 35):  [1, 2],     # Conservative → safe + moderately stable
    (36, 50):  [2, 3],     # Moderate → balanced
    (51, 70):  [3, 4],     # Growth → moderate to aggressive
    (71, 85):  [4, 5],     # Aggressive → high risk
    (86, 100): [5],        # Ultra Aggressive → riskiest stocks only
}

# Investor risk → portfolio parameters
INVESTOR_PARAMS = {
    (0, 20):   {'category': 'Ultra Conservative', 'max_equity': 0.40, 'concentration_limit': 0.10, 'min_holdings': 6},
    (21, 35):  {'category': 'Conservative',        'max_equity': 0.55, 'concentration_limit': 0.15, 'min_holdings': 8},
    (36, 50):  {'category': 'Moderate',            'max_equity': 0.70, 'concentration_limit': 0.20, 'min_holdings': 10},
    (51, 70):  {'category': 'Growth',              'max_equity': 0.85, 'concentration_limit': 0.25, 'min_holdings': 12},
    (71, 85):  {'category': 'Aggressive',          'max_equity': 0.90, 'concentration_limit': 0.28, 'min_holdings': 14},
    (86, 100): {'category': 'Ultra Aggressive',    'max_equity': 0.95, 'concentration_limit': 0.30, 'min_holdings': 15},
}


def get_investor_params(risk_score: float) -> Dict:
    """Get portfolio parameters based on investor risk score."""
    for (low, high), params in INVESTOR_PARAMS.items():
        if low <= risk_score <= high:
            return params
    return INVESTOR_PARAMS[(36, 50)]


def get_assigned_buckets(risk_score: float) -> List[int]:
    """Get stock risk buckets assigned to this investor."""
    for (low, high), buckets in INVESTOR_BUCKET_MAP.items():
        if low <= risk_score <= high:
            return buckets
    return [2, 3]


def build_portfolio(
    composite_df: pd.DataFrame,
    stock_risk_df: pd.DataFrame,
    investor_risk_score: float,
    capital: float = 100_000,
    top_n_per_bucket: int = 10,
    gamma: float = 2.0,
) -> Dict:
    """
    Build risk-matched portfolio.

    Parameters
    ----------
    composite_df : pd.DataFrame
        Output from scorer.compute_composite_scores()
        Columns: ticker, fundamental_score, technical_score, composite_score
    stock_risk_df : pd.DataFrame
        Output from stock_risk.compute_stock_risk_scores()
        Columns: ticker, stock_risk_score, risk_bucket
    investor_risk_score : float
        Investor risk score 0-100
    capital : float
        Total investment capital
    top_n_per_bucket : int
        Number of top stocks to select from each assigned bucket
    gamma : float
        Exponential weighting exponent (higher = more concentration in top scores)

    Returns
    -------
    dict
        Portfolio with allocations, metrics, and metadata
    """
    params = get_investor_params(investor_risk_score)
    assigned_buckets = get_assigned_buckets(investor_risk_score)

    # Merge composite scores with stock risk
    merged = composite_df.merge(stock_risk_df[['ticker', 'stock_risk_score', 'risk_bucket']], on='ticker', how='inner')

    # Filter to assigned buckets
    eligible = merged[merged['risk_bucket'].isin(assigned_buckets)].copy()

    if len(eligible) == 0:
        return {
            'error': 'No eligible stocks in assigned risk buckets',
            'investor_risk_score': investor_risk_score,
            'category': params['category'],
            'assigned_buckets': assigned_buckets,
        }

    # Select top N per bucket
    selected = []
    for bucket in assigned_buckets:
        bucket_stocks = eligible[eligible['risk_bucket'] == bucket].sort_values(
            'composite_score', ascending=False
        ).head(top_n_per_bucket)
        selected.append(bucket_stocks)

    if not selected:
        return {
            'error': 'No stocks selected after filtering',
            'investor_risk_score': investor_risk_score,
        }

    portfolio_stocks = pd.concat(selected, ignore_index=True)

    if len(portfolio_stocks) < 3:
        return {
            'error': f'Only {len(portfolio_stocks)} stocks available (need at least 3)',
            'investor_risk_score': investor_risk_score,
        }

    # Exponential weighting
    scores = portfolio_stocks['composite_score'].values
    raw_weights = np.power(scores, gamma)
    weights = raw_weights / raw_weights.sum()

    # Apply concentration limit
    cl = params['concentration_limit']
    for _ in range(10):
        excess = np.maximum(weights - cl, 0)
        if excess.sum() < 1e-10:
            break
        weights = np.minimum(weights, cl)
        remaining = weights < cl
        if remaining.sum() > 0 and excess.sum() > 0:
            weights[remaining] += excess.sum() * (weights[remaining] / weights[remaining].sum())

    # Normalize
    if weights.sum() > 0:
        weights /= weights.sum()

    # Apply minimum position threshold (5%)
    min_weight = 0.05
    mask = weights >= min_weight
    weights = weights * mask
    if weights.sum() > 0:
        weights /= weights.sum()
    portfolio_stocks = portfolio_stocks[mask].reset_index(drop=True)
    weights = weights[mask]

    # Equity allocation
    eq_w = params['max_equity']
    cash_w = 1.0 - eq_w
    eq_amt = capital * eq_w
    cash_amt = capital * cash_w

    # Build allocations
    allocations = []
    for i, (_, row) in enumerate(portfolio_stocks.iterrows()):
        sw = weights[i] * eq_w
        sa = capital * sw
        allocations.append({
            'ticker': row['ticker'],
            'composite_score': round(float(row['composite_score']), 4),
            'fundamental_score': round(float(row['fundamental_score']), 4),
            'technical_score': round(float(row['technical_score']), 4),
            'stock_risk_score': round(float(row['stock_risk_score']), 2),
            'risk_bucket': int(row['risk_bucket']),
            'weight_pct': round(sw * 100, 2),
            'capital_allocated': round(sa, 2),
        })

    # Sort by weight descending
    allocations.sort(key=lambda x: x['weight_pct'], reverse=True)

    return {
        'investor_risk_score': investor_risk_score,
        'category': params['category'],
        'assigned_buckets': assigned_buckets,
        'equity_weight': round(eq_w * 100, 2),
        'equity_amount': round(eq_amt, 2),
        'cash_weight': round(cash_w * 100, 2),
        'cash_amount': round(cash_amt, 2),
        'n_holdings': len(allocations),
        'concentration_limit': params['concentration_limit'] * 100,
        'allocations': allocations,
    }


def print_portfolio_report(portfolio: Dict, capital: float = 100_000):
    """Print formatted portfolio report."""
    if 'error' in portfolio:
        print(f"\n  ERROR: {portfolio['error']}")
        return

    print("\n" + "=" * 80)
    print(" RISK-MATCHED PORTFOLIO REPORT")
    print("=" * 80)

    print(f"\n  Investor Risk Score: {portfolio['investor_risk_score']:.0f}/100")
    print(f"  Category: {portfolio['category']}")
    print(f"  Assigned Stock Buckets: {portfolio['assigned_buckets']}")
    print(f"  Capital: ${capital:,.0f}")
    print(f"  Equity: {portfolio['equity_weight']:.1f}% (${portfolio['equity_amount']:,.0f})")
    print(f"  Cash: {portfolio['cash_weight']:.1f}% (${portfolio['cash_amount']:,.0f})")
    print(f"  Holdings: {portfolio['n_holdings']}")
    print(f"  Max per Stock: {portfolio['concentration_limit']:.0f}%")

    if portfolio['allocations']:
        print(f"\n  {'#':>2} {'Ticker':<8} {'Comp':>6} {'Fund':>6} {'Tech':>6} {'Risk':>6} {'Bucket':>6} {'Wt%':>6} {'Capital':>10}")
        print("  " + "-" * 76)
        for i, a in enumerate(portfolio['allocations'], 1):
            print(f"  {i:>2} {a['ticker']:<8} {a['composite_score']:>6.3f} {a['fundamental_score']:>6.3f} "
                  f"{a['technical_score']:>6.3f} {a['stock_risk_score']:>6.1f} {a['risk_bucket']:>6} "
                  f"{a['weight_pct']:>5.1f}% ${a['capital_allocated']:>9,.0f}")

        print(f"\n       {'Cash':<8} {'':>6} {'':>6} {'':>6} {'':>6} {'':>6} "
              f"{portfolio['cash_weight']:>5.1f}% ${portfolio['cash_amount']:>9,.0f}")

    print("\n" + "=" * 80)
