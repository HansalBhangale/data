"""
Rebalancing Module - Portfolio Rebalancing Logic

Provides functions to calculate rebalancing actions (buy/sell/hold)
based on current portfolio allocations vs target allocations.
"""

from typing import Dict, List, Optional
from datetime import datetime, timezone
import pandas as pd


def calculate_rebalance_actions(
    current_allocations: List[Dict],
    target_allocations: List[Dict],
    threshold: float = 0.05,
    current_capital: float = 100000,
) -> Dict:
    """
    Calculate rebalancing actions: BUY, SELL, or HOLD for each stock.
    
    Parameters
    ----------
    current_allocations : list[dict]
        Current portfolio holdings.
        Each dict should have: ticker, weight_pct, capital_allocated (optional)
    target_allocations : list[dict]
        Target portfolio (from portfolio generation).
        Each dict should have: ticker, weight_pct (optional for new stocks)
    threshold : float
        Drift threshold to trigger buy/sell (default 5% = 0.05)
    current_capital : float
        Current total portfolio value (default 100000)
    
    Returns
    -------
    dict
        {
            "actions": [
                {
                    "ticker": str,
                    "action": "BUY" | "SELL" | "HOLD",
                    "current_weight": float,
                    "target_weight": float,
                    "weight_diff": float,
                    "shares": int,
                    "amount": float,
                }
            ],
            "summary": {
                "total_buy_amount": float,
                "total_sell_amount": float,
                "net_cash_flow": float,
                "max_drift": float,
                "n_buy": int,
                "n_sell": int,
                "n_hold": int,
            }
        }
    """
    if not current_allocations:
        return _empty_rebalance_result()
    
    current_by_ticker = {a['ticker'].upper(): a for a in current_allocations}
    target_by_ticker = {a['ticker'].upper(): a for a in target_allocations}
    
    all_tickers = set(current_by_ticker.keys()) | set(target_by_ticker.keys())
    
    actions = []
    total_buy = 0.0
    total_sell = 0.0
    max_drift = 0.0
    
    for ticker in sorted(all_tickers):
        current = current_by_ticker.get(ticker, {})
        target = target_by_ticker.get(ticker, {})
        
        current_weight = current.get('weight_pct', 0) / 100
        target_weight = target.get('weight_pct', 10) / 100
        
        current_amount = current.get('capital_allocated', current_capital * current_weight)
        
        weight_diff = target_weight - current_weight
        abs_weight_diff = abs(weight_diff)
        
        max_drift = max(max_drift, abs_weight_diff)
        
        if abs_weight_diff <= threshold:
            action = "HOLD"
            shares = 0
            amount = 0
        elif weight_diff > 0:
            action = "BUY"
            buy_amount = weight_diff * current_capital
            shares = int(buy_amount / 100)
            amount = shares * 100
            total_buy += amount
        else:
            action = "SELL"
            sell_amount = abs(weight_diff) * current_capital
            shares = int(sell_amount / 100)
            amount = shares * 100
            total_sell += amount
        
        actions.append({
            'ticker': ticker,
            'action': action,
            'current_weight': round(current_weight * 100, 2),
            'target_weight': round(target_weight * 100, 2),
            'weight_diff': round(weight_diff * 100, 2),
            'shares': shares,
            'amount': round(amount, 2),
        })
    
    actions.sort(key=lambda x: (
        0 if x['action'] == 'HOLD' else 1 if x['action'] == 'SELL' else 2,
        -abs(x['weight_diff'])
    ))
    
    n_buy = sum(1 for a in actions if a['action'] == 'BUY')
    n_sell = sum(1 for a in actions if a['action'] == 'SELL')
    n_hold = sum(1 for a in actions if a['action'] == 'HOLD')
    
    return {
        'actions': actions,
        'summary': {
            'total_buy_amount': round(total_buy, 2),
            'total_sell_amount': round(total_sell, 2),
            'net_cash_flow': round(total_buy - total_sell, 2),
            'max_drift': round(max_drift * 100, 2),
            'n_buy': n_buy,
            'n_sell': n_sell,
            'n_hold': n_hold,
        }
    }


def _empty_rebalance_result() -> Dict:
    return {
        'actions': [],
        'summary': {
            'total_buy_amount': 0,
            'total_sell_amount': 0,
            'net_cash_flow': 0,
            'max_drift': 0,
            'n_buy': 0,
            'n_sell': 0,
            'n_hold': 0,
        }
    }


def regenerate_target_from_buckets(
    risk_score: float,
    stock_risk_df: pd.DataFrame,
    bucket_weights: List[float],
    buckets: List[int],
    top_n_per_bucket: int = 10,
    max_stocks: int = 10,
    current_holdings: List[str] = None,
    replacement_threshold: float = 0.12,
    portfolio_age_days: int = 0,
    composite_df: pd.DataFrame = None,
) -> List[Dict]:
    """
    Regenerate target portfolio allocations based on composite scores.
    
    CRITICAL: Uses composite_score (HIGHER = BETTER) for ranking, NOT stock_risk_score.
    
    Smart replacement logic:
    - For portfolios < 90 days old: Keep ALL current holdings (no stock changes)
    - For portfolios >= 90 days old: Replace only if stock dropped below competitive threshold
    """
    COOLDOWN_DAYS = 90
    
    # NEW PORTFOLIO (< 90 days): Keep ALL current holdings with equal weight
    if portfolio_age_days < COOLDOWN_DAYS and current_holdings:
        weight_per_stock = 100.0 / len(current_holdings)
        return [
            {'ticker': str(t).upper(), 'weight_pct': weight_per_stock}
            for t in current_holdings
        ]
    
    # Load composite scores if not provided
    if composite_df is None or composite_df.empty:
        try:
            composite_df = pd.read_csv('output_composite/composite_scores.csv')
        except:
            composite_df = None
    
    # Merge composite scores with stock risk data
    if composite_df is not None and 'composite_score' in composite_df.columns:
        merged = stock_risk_df.merge(
            composite_df[['ticker', 'composite_score']], 
            on='ticker', 
            how='inner'
        )
    else:
        merged = stock_risk_df.copy()
        merged['composite_score'] = -merged['stock_risk_score']
    
    # Filter to eligible buckets
    eligible = merged[merged['risk_bucket'].isin(buckets)].copy()
    if len(eligible) == 0:
        return []
    
    # Sort by composite_score DESCENDING (higher = better)
    eligible = eligible.sort_values('composite_score', ascending=False)
    
    top_pool = eligible.head(max_stocks * 3)
    cutoff_score = eligible.iloc[max_stocks - 1]['composite_score'] if len(eligible) >= max_stocks else eligible.iloc[-1]['composite_score']
    threshold_score = cutoff_score - replacement_threshold
    
    kept_stocks = []
    if current_holdings:
        current_holdings_set = set([t.upper() for t in current_holdings])
        for ticker in current_holdings_set:
            stock_data = top_pool[top_pool['ticker'].str.upper() == ticker]
            if len(stock_data) > 0 and stock_data.iloc[0]['composite_score'] >= threshold_score:
                kept_stocks.append(stock_data.iloc[0]['ticker'])
    
    # Fill remaining slots
    slots_to_fill = max_stocks - len(kept_stocks)
    if slots_to_fill > 0:
        candidates = top_pool[~top_pool['ticker'].isin(kept_stocks)]
        for _, row in candidates.head(slots_to_fill).iterrows():
            kept_stocks.append(row['ticker'])
    
    # Build target allocations
    if kept_stocks:
        weight_per_stock = 100.0 / len(kept_stocks)
        return [{'ticker': t, 'weight_pct': weight_per_stock} for t in kept_stocks]
    return []


def check_rebalance_needed(
    current_allocations: List[Dict],
    target_allocations: List[Dict],
    threshold: float = 0.05,
) -> bool:
    """
    Check if rebalancing is needed based on threshold.
    
    Returns True if any stock's weight differs from target by more than threshold.
    """
    result = calculate_rebalance_actions(current_allocations, target_allocations, threshold)
    return result['summary']['max_drift'] > (threshold * 100)


def get_rebalance_summary_text(actions: List[Dict]) -> str:
    """Generate human-readable rebalance summary."""
    if not actions:
        return "No rebalancing needed."
    
    buys = [a for a in actions if a['action'] == 'BUY']
    sells = [a for a in actions if a['action'] == 'SELL']
    holds = [a for a in actions if a['action'] == 'HOLD']
    
    lines = []
    if buys:
        lines.append(f"🟢 BUY {len(buys)}: {', '.join(a['ticker'] for a in buys)}")
    if sells:
        lines.append(f"🔴 SELL {len(sells)}: {', '.join(a['ticker'] for a in sells)}")
    if holds:
        lines.append(f"⚪ HOLD {len(holds)}: {', '.join(a['ticker'] for a in holds)}")
    
    return " | ".join(lines)


def format_action_row(action: Dict) -> Dict:
    """Format a single action for display."""
    emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'HOLD': '⚪'
    }.get(action['action'], '•')
    
    return {
        'Ticker': action['ticker'],
        'Current %': f"{action['current_weight']:.1f}%",
        'Target %': f"{action['target_weight']:.1f}%",
        'Action': f"{emoji} {action['action']}",
        'Shares': f"{action['shares']}" if action['shares'] > 0 else '—',
        'Amount': f"${action['amount']:,.0f}" if action['amount'] > 0 else '—',
    }
