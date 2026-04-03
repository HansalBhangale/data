#!/usr/bin/env python3
"""
Full Pipeline Test: Run risk profiling -> portfolio generation -> backtest for all investor profiles.

Tests that:
- Conservative investors get conservative portfolios with lower risk/return
- Moderate investors get balanced portfolios
- Aggressive investors get aggressive portfolios with higher risk/return

This version uses the SAME mapping functions as the GUI to verify correctness.

Usage:
    python test_full_pipeline.py
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import warnings
import json

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

# Stub classes for unpickling risk model
class PCABasedRiskScorer:
    def __init__(self, df=None): self.df = df
class EmpiricalCorrelationScorer:
    def __init__(self, df=None): self.df = df

from composite.scorer import compute_composite_scores
from composite.stock_risk import compute_stock_risk_scores
from composite.portfolio import build_portfolio, get_investor_params, get_assigned_buckets
from composite.portfolio_enhanced import (
    build_portfolio_enhanced, print_enhanced_report,
    get_enhanced_params, calculate_bucket_weights,
)


# =============================================================================
# MAPPING FUNCTIONS (SAME AS GUI - verifies mappings are correct)
# =============================================================================

def map_age_to_features(age: int) -> dict:
    """Map age to AGE and AGECL features.

    SCF 2022 AGECL definitions:
    - AGECL 1: 18-34
    - AGECL 2: 35-44
    - AGECL 3: 45-54
    - AGECL 4: 55-64
    - AGECL 5: 65-74
    - AGECL 6: 75+
    """
    if age < 35: agecl = 1
    elif age < 45: agecl = 2
    elif age < 55: agecl = 3
    elif age < 65: agecl = 4
    elif age < 75: agecl = 5
    else: agecl = 6
    return {"AGE": age, "AGECL": agecl}


def map_education_to_features(education: str) -> dict:
    """Map education level to EDUC feature.

    SCF 2022 EDUC definitions:
    - 8-9: High school/GED
    - 10-11: Some college or AA degree
    - 12: Bachelor's degree
    - 13: Master's degree
    - 14: Doctoral/Professional degree
    """
    education_map = {
        "Less than High School": 8,
        "High School/GED": 9,
        "Some College": 11,
        "Bachelor's": 12,
        "Master's": 13,
        "Doctoral": 14
    }
    return {"EDUC": education_map.get(education, 11)}


def map_occupation_to_features(occupation: str) -> dict:
    """Map occupation status to OCCAT1 and OCCAT2 features.

    SCF 2022 occupation categories:
    - OCCAT1: 1=Employee, 2=Self-employed, 3=Retired, 4=Not working
    - OCCAT2: Secondary classification
    """
    occ_map = {
        "Employee/Salaried": {"OCCAT1": 1, "OCCAT2": 2},
        "Self-Employed": {"OCCAT1": 2, "OCCAT2": 1},
        "Retired": {"OCCAT1": 3, "OCCAT2": 3},
        "Not Working/Student": {"OCCAT1": 4, "OCCAT2": 3}
    }
    return occ_map.get(occupation, {"OCCAT1": 1, "OCCAT2": 2})


def map_income_to_features(income_range: str) -> dict:
    """Map income range to income-related features.

    SCF 2022 INCCAT definitions:
    - INCCAT 1: $0-31K
    - INCCAT 2: $31K-54K
    - INCCAT 3: $54K-91K
    - INCCAT 4: $91K-151K
    - INCCAT 5: $151K-249K
    - INCCAT 6: $249K+
    """
    income_to_inccat = {
        "Under $30K": 1,
        "$30K-$55K": 2,
        "$55K-$90K": 3,
        "$90K-$150K": 4,
        "$150K-$250K": 5,
        "Over $250K": 6
    }
    inccat = income_to_inccat.get(income_range, 3)
    return {
        "INCCAT": inccat,
        "NINCCAT": max(1, inccat - 1) if inccat > 1 else 1,
        "NINC2CAT": 1 if inccat <= 2 else (2 if inccat <= 4 else 3),
        "INCPCTLECAT": min(12, inccat * 2),
        "NINCPCTLECAT": max(1, inccat * 2 - 1),
        "INCQRTCAT": min(4, max(1, (inccat + 1) // 2 + 1)),
        "NINCQRTCAT": min(4, max(1, inccat // 2 + 1))
    }


def map_networth_to_features(networth_range: str) -> dict:
    """Map net worth range to NWCAT and NWPCTLECAT features.

    SCF 2022 NWCAT definitions:
    - NWCAT 1: <$27K
    - NWCAT 2: $27K-193K
    - NWCAT 3: $193K-659K
    - NWCAT 4: $659K-1.94M
    - NWCAT 5: >$1.94M
    """
    nw_map = {
        "Under $30K": 1,
        "$30K-$200K": 2,
        "$200K-$700K": 3,
        "$700K-$2M": 4,
        "Over $2M": 5
    }
    nwcat = nw_map.get(networth_range, 3)
    nw_pctle_map = {1: 2, 2: 4, 3: 6, 4: 9, 5: 11}
    return {"NWCAT": nwcat, "NWPCTLECAT": nw_pctle_map.get(nwcat, 6)}


def map_assets_to_features(assets_range: str) -> dict:
    """Map total assets range to ASSETCAT feature.

    SCF 2022 ASSETCAT definitions:
    - ASSETCAT 1: <$32K
    - ASSETCAT 2: $32K-212K
    - ASSETCAT 3: $213K-455K
    - ASSETCAT 4: $455K-1.06M
    - ASSETCAT 5: $1.06M-2.12M
    - ASSETCAT 6: >$2.12M
    """
    asset_map = {
        "Under $30K": 1,
        "$30K-$200K": 2,
        "$200K-$500K": 3,
        "$500K-$1M": 4,
        "$1M-$2M": 5,
        "Over $2M": 6
    }
    return {"ASSETCAT": asset_map.get(assets_range, 3)}


def build_model_features(age, education, occupation, income_range, networth_range,
                         assets_range, has_emergency, has_savings_checking,
                         has_mutual_funds, has_retirement):
    """Build complete feature vector from user inputs using SCF mappings."""
    features = {}
    features.update(map_age_to_features(age))
    features.update(map_education_to_features(education))
    features.update(map_occupation_to_features(occupation))
    features.update(map_income_to_features(income_range))
    features.update(map_networth_to_features(networth_range))
    features.update(map_assets_to_features(assets_range))
    features.update({
        "EMERGSAV": int(has_emergency),
        "HSAVFIN": int(has_savings_checking),
        "HNMMF": int(has_mutual_funds),
        "HRETQLIQ": int(has_retirement)
    })
    return features


# =============================================================================
# INVESTOR PROFILES - Using GUI-style inputs (NOT hardcoded SCF values)
# =============================================================================

INVESTOR_PROFILES = {
    'conservative': {
        'name': 'Conservative (Risk-Averse Professional)',
        'inputs': {
            # Personal Information
            'age': 58,
            'education': "Some College",
            'occupation': "Employee/Salaried",
            # Financial Details
            'income_range': "$55K-$90K",
            'networth_range': "$200K-$700K",
            'assets_range': "$200K-$500K",
            # Experience & Holdings
            'has_emergency': True,
            'has_savings_checking': True,
            'has_mutual_funds': False,
            'has_retirement': True,
        }
    },
    'moderate': {
        'name': 'Moderate (Balanced Investor)',
        'inputs': {
            # Personal Information
            'age': 45,
            'education': "Bachelor's",
            'occupation': "Employee/Salaried",
            # Financial Details
            'income_range': "$90K-$150K",
            'networth_range': "$200K-$700K",
            'assets_range': "$200K-$500K",
            # Experience & Holdings
            'has_emergency': True,
            'has_savings_checking': True,
            'has_mutual_funds': True,
            'has_retirement': True,
        }
    },
    'aggressive': {
        'name': 'Aggressive (Young High-Earner)',
        'inputs': {
            # Personal Information
            'age': 28,
            'education': "Master's",
            'occupation': "Self-Employed",
            # Financial Details
            'income_range': "Over $250K",
            'networth_range': "Over $2M",
            'assets_range': "Over $2M",
            # Experience & Holdings
            'has_emergency': True,
            'has_savings_checking': True,
            'has_mutual_funds': True,
            'has_retirement': True,
        }
    },
}


def load_risk_score(profile_key, risk_model_path):
    """Predict investor risk score from profile using MAPPED features."""
    with open(risk_model_path, 'rb') as f:
        risk_data = pickle.load(f)
    model = risk_data['model']
    feature_names = risk_data['features']

    # Get profile inputs
    profile = INVESTOR_PROFILES[profile_key]
    inputs = profile['inputs']

    # Build features using mapping functions (SAME AS GUI)
    features = build_model_features(
        age=inputs['age'],
        education=inputs['education'],
        occupation=inputs['occupation'],
        income_range=inputs['income_range'],
        networth_range=inputs['networth_range'],
        assets_range=inputs['assets_range'],
        has_emergency=inputs['has_emergency'],
        has_savings_checking=inputs['has_savings_checking'],
        has_mutual_funds=inputs['has_mutual_funds'],
        has_retirement=inputs['has_retirement']
    )

    # Create feature vector in correct order
    feature_vector = [features.get(feat, 0) for feat in feature_names]
    X = np.array([feature_vector])

    return float(np.clip(model.predict(X)[0], 0, 100)), features


def load_model_scores(script_dir):
    """Load model predictions (fundamental + technical)."""
    # Fundamental
    with open(script_dir / 'output' / 'model_1y.pkl', 'rb') as f:
        fund_data = pickle.load(f)
    fund_model = fund_data['model']
    fund_features = fund_data['feature_names']

    df_fund = pd.read_csv(script_dir / 'output' / 'preprocessed_data.csv')
    X_fund = df_fund[fund_features].copy()
    X_fund = X_fund.replace([np.inf, -np.inf], np.nan)
    for col in X_fund.columns:
        X_fund[col] = X_fund[col].fillna(X_fund[col].median())
    fund_preds = fund_model.predict(X_fund)
    fund_scores = dict(zip(df_fund['ticker'].values, fund_preds.astype(float)))

    # Technical
    with open(script_dir / 'output_technical' / 'model_1y.pkl', 'rb') as f:
        tech_data = pickle.load(f)
    tech_model = tech_data['model']
    tech_features = tech_data['feature_names']

    df_tech = pd.read_csv(script_dir / 'output_technical' / 'technical_features_preprocessed.csv')
    X_tech = df_tech[tech_features].copy()
    X_tech = X_tech.replace([np.inf, -np.inf], np.nan)
    for col in X_tech.columns:
        X_tech[col] = X_tech[col].fillna(X_tech[col].median())
    tech_preds = tech_model.predict(X_tech)
    tech_scores = dict(zip(df_tech['ticker'].values, tech_preds.astype(float)))

    return fund_scores, tech_scores


def backtest_portfolio(portfolio, daily_prices, spy_daily, start_date='2024-01-01', end_date='2025-12-31'):
    """
    Backtest a portfolio using historical daily returns.
    """
    if not portfolio.get('allocations'):
        return {}

    tickers = [a['ticker'] for a in portfolio['allocations']]
    weights = np.array([a['weight_pct'] / 100.0 for a in portfolio['allocations']])
    weights = weights / weights.sum()

    port_prices = daily_prices[daily_prices['ticker'].isin(tickers)].copy()
    port_prices = port_prices[port_prices['date'] >= start_date]
    port_prices = port_prices[port_prices['date'] <= end_date]

    price_pivot = port_prices.pivot_table(index='date', columns='ticker', values='adj_close')
    price_pivot = price_pivot.sort_index()

    if price_pivot.empty or len(price_pivot) < 30:
        return {}

    returns = price_pivot.pct_change().dropna()
    available = [t for t in tickers if t in returns.columns]
    if len(available) < 2:
        return {}

    returns = returns[available]
    port_weights = np.array([weights[tickers.index(t)] for t in available])
    port_weights = port_weights / port_weights.sum()
    port_daily = returns.values @ port_weights

    spy = spy_daily[spy_daily['date'] >= start_date].copy()
    spy = spy[spy['date'] <= end_date].sort_values('date')
    if len(spy) > 1:
        spy_daily_ret = spy['adj_close'].pct_change().dropna()
    else:
        spy_daily_ret = pd.Series(dtype=float)

    port_cumulative = (1 + pd.Series(port_daily)).cumprod() - 1
    spy_cumulative = (1 + spy_daily_ret).cumprod() - 1

    trading_days = 252
    port_annual_return = port_daily.mean() * trading_days
    port_annual_vol = port_daily.std() * np.sqrt(trading_days)
    port_sharpe = (port_annual_return - 0.04) / port_annual_vol if port_annual_vol > 0 else 0

    port_cum = (1 + pd.Series(port_daily)).cumprod()
    running_max = port_cum.cummax()
    drawdown = (port_cum - running_max) / running_max
    max_drawdown = drawdown.min()

    if len(spy_daily_ret) > 0:
        spy_annual_return = spy_daily_ret.mean() * trading_days
        spy_annual_vol = spy_daily_ret.std() * np.sqrt(trading_days)
        spy_sharpe = (spy_annual_return - 0.04) / spy_annual_vol if spy_annual_vol > 0 else 0
        spy_cum = (1 + spy_daily_ret).cumprod()
        spy_running_max = spy_cum.cummax()
        spy_drawdown = (spy_cum - spy_running_max) / spy_cum
        spy_max_drawdown = spy_drawdown.min()
    else:
        spy_annual_return = spy_annual_vol = spy_sharpe = spy_max_drawdown = 0

    return {
        'annual_return': port_annual_return,
        'annual_volatility': port_annual_vol,
        'sharpe_ratio': port_sharpe,
        'max_drawdown': max_drawdown,
        'total_return': port_cumulative.iloc[-1] if len(port_cumulative) > 0 else 0,
        'spy_return': spy_cumulative.iloc[-1] if len(spy_cumulative) > 0 else 0,
        'spy_sharpe': spy_sharpe,
        'spy_max_drawdown': spy_max_drawdown,
        'spy_annual_return': spy_annual_return,
        'spy_annual_vol': spy_annual_vol,
        'n_holdings': len(available),
    }


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--enhanced', action='store_true', default=True)
    parser.add_argument('--no-enhanced', action='store_true')
    args = parser.parse_args()
    use_enhanced = not args.no_enhanced
    
    script_dir = Path(__file__).parent
    capital = 100_000
    risk_model_path = script_dir / 'risk prediction' / 'risk_tolerance_model.pkl'

    print("\n" + "=" * 90)
    print("FULL PIPELINE TEST: Risk Profiling -> Portfolio Generation -> Backtest")
    print(f"(Using {'ENHANCED' if use_enhanced else 'ORIGINAL'} Portfolio Builder)")
    print("=" * 90)

    # Load data once
    print("\nLoading data...")
    daily_prices = pd.read_csv(script_dir / 'daily_prices_all.csv', parse_dates=['date'])
    spy_daily = daily_prices[daily_prices['ticker'] == 'SPY'].copy()
    daily_prices = daily_prices[daily_prices['ticker'] != 'SPY']
    fundamental_df = pd.read_csv(script_dir / 'output' / 'preprocessed_data.csv')

    # Load model scores once
    print("Loading model predictions...")
    fund_scores, tech_scores = load_model_scores(script_dir)
    composite_df = compute_composite_scores(fund_scores, tech_scores)
    stock_risk_df = compute_stock_risk_scores(daily_prices, spy_daily, fundamental_df)
    print(f"  Composite scores: {len(composite_df)} stocks")
    print(f"  Stock risk scores: {len(stock_risk_df)} stocks")

    # Run pipeline for each profile
    profiles_to_test = ['conservative', 'moderate', 'aggressive']
    all_results = []

    for profile_key in profiles_to_test:
        profile = INVESTOR_PROFILES[profile_key]
        inputs = profile['inputs']

        print("\n" + "=" * 90)
        print(f"PROFILE: {profile_key.upper()}")
        print("=" * 90)

        # Show INPUT values (what user enters in GUI)
        print(f"\n  USER INPUTS:")
        print(f"    Age: {inputs['age']}")
        print(f"    Education: {inputs['education']}")
        print(f"    Occupation: {inputs['occupation']}")
        print(f"    Income: {inputs['income_range']}")
        print(f"    Net Worth: {inputs['networth_range']}")
        print(f"    Assets: {inputs['assets_range']}")
        print(f"    Emergency Fund: {inputs['has_emergency']}")
        print(f"    Savings A/C: {inputs['has_savings_checking']}")
        print(f"    Mutual Funds: {inputs['has_mutual_funds']}")
        print(f"    Retirement A/C: {inputs['has_retirement']}")

        # Step 1: Risk score (using MAPPED features)
        risk_score, mapped_features = load_risk_score(profile_key, risk_model_path)
        params = get_investor_params(risk_score)
        buckets = get_assigned_buckets(risk_score)

        # Show MAPPED values (what gets sent to model)
        print(f"\n  MAPPED SCF FEATURES:")
        print(f"    AGE: {mapped_features['AGE']} -> AGECL: {mapped_features['AGECL']}")
        print(f"    EDUC: {mapped_features['EDUC']}")
        print(f"    OCCAT1: {mapped_features['OCCAT1']}, OCCAT2: {mapped_features['OCCAT2']}")
        print(f"    INCCAT: {mapped_features['INCCAT']}, INCPCTLECAT: {mapped_features['INCPCTLECAT']}")
        print(f"    NWCAT: {mapped_features['NWCAT']}, NWPCTLECAT: {mapped_features['NWPCTLECAT']}")
        print(f"    ASSETCAT: {mapped_features['ASSETCAT']}")

        print(f"\n  RISK ASSESSMENT:")
        print(f"    Risk Score: {risk_score:.1f}/100")
        
        if use_enhanced:
            params = get_enhanced_params(risk_score)
            bucket_config = calculate_bucket_weights(risk_score)
            buckets = bucket_config['buckets']
            print(f"    Category: {params['category']}")
            print(f"    Assigned Buckets: {buckets}")
            print(f"    Bucket Weights: {bucket_config['bucket_weights']}")
            print(f"    Max Equity: {params['base_equity']:.0%}")
            print(f"    Max Weight/Stock: {params['max_weight_per_stock']:.0%}")
        else:
            params = get_investor_params(risk_score)
            buckets = get_assigned_buckets(risk_score)
            print(f"    Category: {params['category']}")
            print(f"    Assigned Buckets: {buckets}")
            print(f"    Max Equity: {params['max_equity']:.0%}")
            print(f"    Concentration Limit: {params['concentration_limit']:.0%}")

        # Step 2: Build portfolio
        if use_enhanced:
            portfolio = build_portfolio_enhanced(
                composite_df, stock_risk_df, risk_score, capital,
                fundamental_df=fundamental_df,
                daily_prices=daily_prices,
                spy_daily=spy_daily,
            )
        else:
            portfolio = build_portfolio(composite_df, stock_risk_df, risk_score, capital)

        if 'error' in portfolio:
            print(f"  ERROR: {portfolio['error']}")
            continue

        print(f"\n  PORTFOLIO:")
        print(f"    Holdings: {portfolio['n_holdings']}")
        print(f"    Equity Weight: {portfolio['equity_weight']:.1f}%")
        print(f"    Cash Weight: {portfolio['cash_weight']:.1f}%")

        # Show top holdings
        if portfolio['allocations']:
            print(f"    Top 5 Holdings:")
            for a in portfolio['allocations'][:5]:
                print(f"      {a['ticker']}: {a['weight_pct']:.1f}% (Score: {a['composite_score']:.2f})")

        # Step 3: Backtest
        print(f"\n  BACKTEST (2024-01-01 to 2025-12-31):")
        bt = backtest_portfolio(portfolio, daily_prices, spy_daily)

        if bt:
            print(f"    Annual Return:    {bt['annual_return']:.1%}")
            print(f"    Annual Volatility: {bt['annual_volatility']:.1%}")
            print(f"    Sharpe Ratio:     {bt['sharpe_ratio']:.2f}")
            print(f"    Max Drawdown:     {bt['max_drawdown']:.1%}")
            print(f"    Total Return:     {bt['total_return']:.1%}")
            print(f"    SPY Return:       {bt['spy_return']:.1%}")
            print(f"    SPY Sharpe:       {bt['spy_sharpe']:.2f}")
        else:
            print(f"    WARNING: Backtest failed (insufficient data)")
            bt = {}

        all_results.append({
            'profile': profile_key,
            'risk_score': risk_score,
            'category': portfolio.get('category', params.get('category', 'N/A')),
            'buckets': buckets,
            'max_equity': params.get('max_equity', params.get('base_equity', 0)),
            'n_holdings': portfolio['n_holdings'],
            'equity_weight': portfolio['equity_weight'],
            'cash_weight': portfolio['cash_weight'],
            'top_holding': portfolio['allocations'][0]['ticker'] if portfolio['allocations'] else 'N/A',
            'top_weight': portfolio['allocations'][0]['weight_pct'] if portfolio['allocations'] else 0,
            **bt
        })

    # Print comparison table
    print("\n" + "=" * 90)
    print("COMPARISON: All Profiles")
    print("=" * 90)

    df_results = pd.DataFrame(all_results)

    # Add beat_spy column to results
    df_results['beat_spy'] = df_results.apply(
        lambda r: r.get('annual_return', 0) > r.get('spy_return', 0) if 'annual_return' in r else False, 
        axis=1
    )

    print(f"\n{'Metric':<25} {'Conservative':>15} {'Moderate':>15} {'Aggressive':>15}")
    print("-" * 70)

    metrics = [
        ('Risk Score', 'risk_score', '{:.1f}'),
        ('Category', 'category', '{}'),
        ('Assigned Buckets', 'buckets', '{}'),
        ('Max Equity', 'max_equity', '{:.0%}'),
        ('Holdings', 'n_holdings', '{:.0f}'),
        ('Equity Weight', 'equity_weight', '{:.1f}%'),
        ('Top Holding', 'top_holding', '{}'),
        ('Top Weight', 'top_weight', '{:.1f}%'),
        ('Annual Return', 'annual_return', '{:.1%}'),
        ('Annual Volatility', 'annual_volatility', '{:.1%}'),
        ('Sharpe Ratio', 'sharpe_ratio', '{:.2f}'),
        ('Max Drawdown', 'max_drawdown', '{:.1%}'),
        ('Total Return', 'total_return', '{:.1%}'),
        ('SPY Return', 'spy_return', '{:.1%}'),
        ('SPY Sharpe', 'spy_sharpe', '{:.2f}'),
        ('Beat S&P', 'beat_spy', '{}'),
    ]

    for label, col, fmt in metrics:
        vals = []
        for _, row in df_results.iterrows():
            v = row.get(col, '')
            if col == 'beat_spy':
                vals.append('YES' if v else 'NO')
            elif isinstance(v, (int, float)) and not pd.isna(v):
                vals.append(fmt.format(v))
            else:
                vals.append(str(v))
        print(f"{label:<25} {vals[0]:>15} {vals[1]:>15} {vals[2]:>15}")

    # Add beat_spy column to results
    df_results['beat_spy'] = df_results.apply(
        lambda r: r.get('annual_return', 0) > r.get('spy_return', 0) if 'annual_return' in r else False, 
        axis=1
    )

    # Validation checks
    print("\n" + "=" * 90)
    print("VALIDATION CHECKS")
    print("=" * 90)

    cons = df_results[df_results['profile'] == 'conservative'].iloc[0]
    mod = df_results[df_results['profile'] == 'moderate'].iloc[0]
    agg = df_results[df_results['profile'] == 'aggressive'].iloc[0]

    checks = []

    # 1. Risk scores should be ordered
    score_ordered = cons['risk_score'] < mod['risk_score'] < agg['risk_score']
    checks.append(('Risk scores ordered (Cons < Mod < Agg)', score_ordered,
                   f"{cons['risk_score']:.1f} < {mod['risk_score']:.1f} < {agg['risk_score']:.1f}"))

    # 2. Equity weights should be ordered
    if 'equity_weight' in cons and 'equity_weight' in mod and 'equity_weight' in agg:
        eq_ordered = cons['equity_weight'] <= mod['equity_weight'] <= agg['equity_weight']
    checks.append(('Equity weights ordered (Cons <= Mod <= Agg)', eq_ordered,
                   f"{cons['equity_weight']:.1f}% <= {mod['equity_weight']:.1f}% <= {agg['equity_weight']:.1f}%"))

    # 3. Bucket assignments (different for enhanced vs original)
    if use_enhanced:
        # Enhanced: all profiles can access buckets 2-5
        checks.append(('Conservative buckets include higher risk', 2 in cons['buckets'] or 4 in cons['buckets'],
                       f"Buckets: {cons['buckets']}"))
        checks.append(('Moderate buckets include higher risk', 4 in mod['buckets'] or 5 in mod['buckets'],
                       f"Buckets: {mod['buckets']}"))
        checks.append(('Aggressive buckets are risky', 5 in agg['buckets'],
                       f"Buckets: {agg['buckets']}"))
    else:
        # Original: conservative limited to buckets 1-2
        checks.append(('Conservative buckets', cons['buckets'] in [[1], [1, 2]],
                       f"Buckets: {cons['buckets']}"))
        checks.append(('Moderate buckets', mod['buckets'] in [[2, 3]],
                       f"Buckets: {mod['buckets']}"))
        checks.append(('Aggressive buckets', agg['buckets'] in [[4, 5], [5]],
                       f"Buckets: {agg['buckets']}"))

    # 4. Beat S&P check
    if 'annual_return' in cons and 'spy_return' in cons:
        beat_spy = all([
            df_results[df_results['profile'] == p].iloc[0]['annual_return'] > 
            df_results[df_results['profile'] == p].iloc[0]['spy_return']
            for p in ['conservative', 'moderate', 'aggressive']
        ])
        checks.append(('All profiles beat S&P 500', beat_spy, "Check returns vs S&P"))

    # 5. Volatility should generally increase with risk
    if all(k in cons for k in ['annual_volatility']) and all(k in agg for k in ['annual_volatility']):
        if not pd.isna(cons['annual_volatility']) and not pd.isna(agg['annual_volatility']):
            vol_ordered = cons['annual_volatility'] <= agg['annual_volatility']
            checks.append(('Volatility ordered (Cons <= Agg)', vol_ordered,
                           f"{cons['annual_volatility']:.1%} <= {agg['annual_volatility']:.1%}"))

    print()
    for check_name, passed, detail in checks:
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check_name}: {detail}")

    # Show mapping verification
    print("\n" + "=" * 90)
    print("MAPPING VERIFICATION (GUI inputs -> SCF features)")
    print("=" * 90)

    print("\n  Conservative Profile:")
    print(f"    Age 58 -> AGECL: {map_age_to_features(58)['AGECL']} (expected: 4 for 55-64)")
    print(f"    Some College -> EDUC: {map_education_to_features('Some College')['EDUC']} (expected: 11)")
    print(f"    $55K-$90K -> INCCAT: {map_income_to_features('$55K-$90K')['INCCAT']} (expected: 3)")

    print("\n  Moderate Profile:")
    print(f"    Age 45 -> AGECL: {map_age_to_features(45)['AGECL']} (expected: 3 for 45-54)")
    bach_edu = map_education_to_features("Bachelor's")['EDUC']
    print(f"    Bachelor's -> EDUC: {bach_edu} (expected: 12)")
    print(f"    $90K-$150K -> INCCAT: {map_income_to_features('$90K-$150K')['INCCAT']} (expected: 4)")

    print("\n  Aggressive Profile:")
    print(f"    Age 28 -> AGECL: {map_age_to_features(28)['AGECL']} (expected: 1 for 18-34)")
    master_edu = map_education_to_features("Master's")['EDUC']
    print(f"    Master's -> EDUC: {master_edu} (expected: 13)")
    print(f"    Over $250K -> INCCAT: {map_income_to_features('Over $250K')['INCCAT']} (expected: 6)")

    print("\n" + "=" * 90)
    print("PIPELINE TEST COMPLETE")
    print("=" * 90 + "\n")


if __name__ == '__main__':
    main()