"""
Long-Only Backtesting for Risk Buckets.

For each risk bucket (1-5), simulates quarterly rebalancing over historical
periods and tracks portfolio performance metrics.
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional


def backtest_bucket(
    composite_scores_history: List[pd.DataFrame],
    stock_risk_df: pd.DataFrame,
    returns_history: pd.DataFrame,
    bucket: int,
    top_n: int = 10,
    gamma: float = 2.0,
) -> Dict:
    """
    Backtest a single risk bucket with quarterly rebalancing.

    Parameters
    ----------
    composite_scores_history : List[pd.DataFrame]
        List of composite score DataFrames, one per quarter.
        Each has columns: ticker, composite_score
    stock_risk_df : pd.DataFrame
        Stock risk scores with columns: ticker, risk_bucket
    returns_history : pd.DataFrame
        Historical returns with columns: ticker, quarter_end, fwd_return_1y
    bucket : int
        Risk bucket to backtest (1-5)
    top_n : int
        Number of top stocks to select per quarter
    gamma : float
        Exponential weighting exponent

    Returns
    -------
    dict
        Backtest results with returns, Sharpe, max DD, hit rate
    """
    eligible_tickers = stock_risk_df[stock_risk_df['risk_bucket'] == bucket]['ticker'].tolist()

    if not eligible_tickers:
        return {'error': f'No stocks in bucket {bucket}'}

    quarterly_returns = []
    hit_count = 0
    total_periods = 0

    for i, scores_df in enumerate(composite_scores_history):
        # Filter to eligible stocks in this bucket
        eligible = scores_df[scores_df['ticker'].isin(eligible_tickers)].copy()
        if len(eligible) < 3:
            continue

        # Select top N by composite score
        selected = eligible.sort_values('composite_score', ascending=False).head(top_n)

        # Exponential weighting
        scores = selected['composite_score'].values
        raw_w = np.power(scores, gamma)
        weights = raw_w / raw_w.sum()

        # Get actual returns for this quarter
        if i < len(returns_history):
            quarter_returns = returns_history.iloc[i]
            if 'ticker' in quarter_returns.index:
                stock_rets = quarter_returns.set_index('ticker')['fwd_return_1y']
            else:
                stock_rets = quarter_returns

            # Compute portfolio return
            port_ret = 0.0
            for j, (_, row) in enumerate(selected.iterrows()):
                ticker = row['ticker']
                if ticker in stock_rets.index:
                    ret = stock_rets[ticker]
                    if not np.isnan(ret):
                        port_ret += weights[j] * ret
                        total_periods += 1
                        if ret > 0:
                            hit_count += 1

            quarterly_returns.append(port_ret)

    if not quarterly_returns:
        return {'error': f'No return data for bucket {bucket}'}

    rets = np.array(quarterly_returns)

    # Annualize (4 quarters per year)
    ann_return = np.mean(rets) * 4
    ann_vol = np.std(rets) * np.sqrt(4)
    sharpe = ann_return / (ann_vol + 1e-10)

    # Max drawdown
    cumulative = np.cumprod(1 + rets)
    running_max = np.maximum.accumulate(cumulative)
    drawdowns = (cumulative - running_max) / running_max
    max_dd = np.min(drawdowns)

    hit_rate = hit_count / max(total_periods, 1)

    return {
        'bucket': bucket,
        'n_periods': len(quarterly_returns),
        'annualized_return': round(float(ann_return), 4),
        'annualized_volatility': round(float(ann_vol), 4),
        'sharpe_ratio': round(float(sharpe), 4),
        'max_drawdown': round(float(max_dd), 4),
        'hit_rate': round(float(hit_rate), 4),
        'quarterly_returns': [round(float(r), 4) for r in quarterly_returns],
    }


def backtest_all_buckets(
    composite_scores_history: List[pd.DataFrame],
    stock_risk_df: pd.DataFrame,
    returns_history: pd.DataFrame,
    top_n: int = 10,
    gamma: float = 2.0,
) -> Dict[int, Dict]:
    """
    Backtest all 5 risk buckets.

    Returns dict of {bucket_id: backtest_results}
    """
    results = {}
    for bucket in range(1, 6):
        print(f"\n  Backtesting Bucket {bucket}...")
        result = backtest_bucket(
            composite_scores_history, stock_risk_df, returns_history,
            bucket=bucket, top_n=top_n, gamma=gamma
        )
        results[bucket] = result
        if 'error' not in result:
            print(f"    Ann Return: {result['annualized_return']:+.2%}  "
                  f"Vol: {result['annualized_volatility']:.2%}  "
                  f"Sharpe: {result['sharpe_ratio']:.2f}  "
                  f"Max DD: {result['max_drawdown']:.2%}  "
                  f"Hit Rate: {result['hit_rate']:.0%}")
        else:
            print(f"    Error: {result['error']}")

    return results


def print_backtest_summary(results: Dict[int, Dict]):
    """Print formatted backtest summary table."""
    print("\n" + "=" * 80)
    print(" BACKTEST SUMMARY (Long-Only, Quarterly Rebalance, 1-Year Horizon)")
    print("=" * 80)
    print(f"\n  {'Bucket':>8} {'Ann Return':>12} {'Volatility':>12} {'Sharpe':>8} {'Max DD':>10} {'Hit Rate':>10} {'Periods':>8}")
    print("  " + "-" * 72)

    bucket_names = {
        1: '1 (Safest)',
        2: '2',
        3: '3',
        4: '4',
        5: '5 (Riskiest)',
    }

    for b in range(1, 6):
        r = results.get(b, {})
        if 'error' in r:
            print(f"  {bucket_names[b]:>8} {'N/A':>12} {'N/A':>12} {'N/A':>8} {'N/A':>10} {'N/A':>10} {'N/A':>8}")
        else:
            print(f"  {bucket_names[b]:>8} {r['annualized_return']:>+11.2%} "
                  f"{r['annualized_volatility']:>11.2%} {r['sharpe_ratio']:>8.2f} "
                  f"{r['max_drawdown']:>10.2%} {r['hit_rate']:>10.0%} "
                  f"{r['n_periods']:>8}")

    print("\n" + "=" * 80)
