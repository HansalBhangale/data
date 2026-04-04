import numpy as np
import pandas as pd
from typing import Dict, List, Optional
import warnings

warnings.filterwarnings('ignore')

INVESTOR_PARAMS_ENHANCED = {
    #                    equity  bond  cash  max_per_stock  bond_buckets
    'ultra_conservative': (0.20, 0.75, 0.05,  0.10,         ['SHY']),
    'conservative':       (0.55, 0.38, 0.07,  0.15,         ['SHY','IEF']),
    'moderate':           (0.70, 0.25, 0.05,  0.20,         ['IEF','AGG']),
    'growth':             (0.85, 0.13, 0.02,  0.25,         ['AGG','LQD']),
    'aggressive':         (0.90, 0.08, 0.02,  0.28,         ['LQD','HYG']),
    'ultra_aggressive':   (0.95, 0.04, 0.01,  0.30,         ['HYG']),
}

def get_profile(investor_risk_score: float):
    """Map 0-100 score to profile."""
    if investor_risk_score <= 20:   return INVESTOR_PARAMS_ENHANCED['ultra_conservative']
    elif investor_risk_score <= 35: return INVESTOR_PARAMS_ENHANCED['conservative']
    elif investor_risk_score <= 50: return INVESTOR_PARAMS_ENHANCED['moderate']
    elif investor_risk_score <= 70: return INVESTOR_PARAMS_ENHANCED['growth']
    elif investor_risk_score <= 85: return INVESTOR_PARAMS_ENHANCED['aggressive']
    else:                           return INVESTOR_PARAMS_ENHANCED['ultra_aggressive']

def get_category_name(investor_risk_score: float):
    if investor_risk_score <= 20:   return 'Ultra Conservative'
    elif investor_risk_score <= 35: return 'Conservative'
    elif investor_risk_score <= 50: return 'Moderate'
    elif investor_risk_score <= 70: return 'Growth'
    elif investor_risk_score <= 85: return 'Aggressive'
    else:                           return 'Ultra Aggressive'

def run_max_sharpe(scores_series: pd.Series, max_weight: float = 0.20):
    """
    Score-based weighting as a simplified max_sharpe equivalent, 
    matching the existing logic fallback for stability.
    """
    if len(scores_series) == 0:
        return {}
        
    scores_vals = scores_series.values
    # Avoid negative or zero by clamping
    scores_vals = np.maximum(scores_vals, 1e-4)
    raw_weights = np.power(scores_vals, 1.5) # gamma=1.5
    weights = raw_weights / raw_weights.sum()
    
    # Simple capping
    for _ in range(5):
        excess = np.maximum(weights - max_weight, 0)
        if excess.sum() < 1e-10:
            break
        weights = np.minimum(weights, max_weight)
        remaining = weights < max_weight
        if remaining.sum() > 0 and excess.sum() > 0:
            weights[remaining] += excess.sum() * (weights[remaining] / weights[remaining].sum())
            
    weights /= weights.sum()
    return {t: w for t, w in zip(scores_series.index, weights)}

def allocate_portfolio(investor_risk_score, composite_scores: pd.Series, bond_scores: pd.Series, capital: float = 100000):
    """
    composite_scores: pd.Series where index is stock ticker, value is final score.
    bond_scores: pd.Series where index is bond ETF ticker, value is bond score.
    """
    profile = get_profile(investor_risk_score)
    equity_pct, bond_pct, cash_pct, max_wt, bond_buckets = profile
    
    # Step 1 — Optimize WITHIN equity sleeve
    # Select top 10 stocks by score for the sleeve
    top_stocks = composite_scores.sort_values(ascending=False).head(10)
    equity_weights = run_max_sharpe(top_stocks, max_weight=max_wt)
    
    # Step 2 — Optimize WITHIN bond sleeve
    # Filter bond_scores to only include allowed bond_buckets
    eligible_bonds = bond_scores[bond_scores.index.isin(bond_buckets)]
    if len(eligible_bonds) == 0 and len(bond_scores) > 0:
        # fallback to best available if buckets missing
        eligible_bonds = bond_scores.sort_values(ascending=False).head(1)
        
    bond_weights = run_max_sharpe(eligible_bonds, max_weight=0.60)
    
    # Step 3 — Scale to total capital
    final_weights = {
        **{k: v * equity_pct for k, v in equity_weights.items()},
        **{k: v * bond_pct   for k, v in bond_weights.items()}
    }
    
    # Validate sum
    total_w = sum(final_weights.values()) + cash_pct
    assert abs(total_w - 1.0) < 0.01, f"Weights do not sum to 100%: {total_w}"
    
    allocations = []
    
    # Build allocations list for reporting easily
    for t, w in equity_weights.items():
        allocations.append({
            'ticker': t,
            'type': 'Equity',
            'score': round(float(top_stocks[t]), 2),
            'weight_pct': round(w * equity_pct * 100, 2),
            'capital_allocated': round(w * equity_pct * capital, 2)
        })
        
    for t, w in bond_weights.items():
        allocations.append({
            'ticker': t,
            'type': 'Bond',
            'score': round(float(eligible_bonds[t]), 2),
            'weight_pct': round(w * bond_pct * 100, 2),
            'capital_allocated': round(w * bond_pct * capital, 2)
        })
        
    allocations.sort(key=lambda x: x['weight_pct'], reverse=True)
    
    return {
        'investor_risk_score': investor_risk_score,
        'category': get_category_name(investor_risk_score),
        'equity_weight': round(equity_pct * 100, 2),
        'equity_amount': round(equity_pct * capital, 2),
        'bond_weight': round(bond_pct * 100, 2),
        'bond_amount': round(bond_pct * capital, 2),
        'cash_weight': round(cash_pct * 100, 2),
        'cash_amount': round(cash_pct * capital, 2),
        'allocations': allocations
    }

def print_bond_portfolio_report(portfolio: Dict):
    print("\n" + "=" * 95)
    print(" UNIFIED PORTFOLIO REPORT (Equity + Bonds + Cash)")
    print("=" * 95)

    print(f"\n  Investor Risk Score: {portfolio['investor_risk_score']:.0f}/100")
    print(f"  Category: {portfolio['category']}")
    print(f"\n  Total Capital: ${portfolio['equity_amount']+portfolio['bond_amount']+portfolio['cash_amount']:,.0f}")
    print(f"  Equity: {portfolio['equity_weight']:>5.1f}% (${portfolio['equity_amount']:,.0f})")
    print(f"  Bonds:  {portfolio['bond_weight']:>5.1f}% (${portfolio['bond_amount']:,.0f})")
    print(f"  Cash:   {portfolio['cash_weight']:>5.1f}% (${portfolio['cash_amount']:,.0f})")

    if portfolio['allocations']:
        print(f"\n  {'Type':<8} {'Ticker':<8} {'Score':>6} {'Wt%':>6} {'Amount':>10}")
        print("  " + "-" * 50)
        for a in portfolio['allocations']:
            print(f"  {a['type']:<8} {a['ticker']:<8} {a['score']:>6.2f} {a['weight_pct']:>5.1f}% ${a['capital_allocated']:>9,.0f}")

    print("\n" + "=" * 95)
