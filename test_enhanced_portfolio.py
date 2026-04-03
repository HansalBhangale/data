#!/usr/bin/env python3
"""
Test enhanced portfolio construction.
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

# Stub classes
class PCABasedRiskScorer:
    def __init__(self, df=None): self.df = df
class EmpiricalCorrelationScorer:
    def __init__(self, df=None): self.df = df

from composite.scorer import compute_composite_scores
from composite.stock_risk import compute_stock_risk_scores
from composite.portfolio_enhanced import build_portfolio_enhanced


# Mapping functions
def map_age_to_features(age: int) -> dict:
    if age < 35: agecl = 1
    elif age < 45: agecl = 2
    elif age < 55: agecl = 3
    elif age < 65: agecl = 4
    elif age < 75: agecl = 5
    else: agecl = 6
    return {"AGE": age, "AGECL": agecl}

def map_education_to_features(education: str) -> dict:
    education_map = {
        "Less than High School": 8, "High School/GED": 9, "Some College": 11,
        "Bachelor's": 12, "Master's": 13, "Doctoral": 14
    }
    return {"EDUC": education_map.get(education, 11)}

def map_occupation_to_features(occupation: str) -> dict:
    occ_map = {
        "Employee/Salaried": {"OCCAT1": 1, "OCCAT2": 2},
        "Self-Employed": {"OCCAT1": 2, "OCCAT2": 1},
        "Retired": {"OCCAT1": 3, "OCCAT2": 3},
        "Not Working/Student": {"OCCAT1": 4, "OCCAT2": 3}
    }
    return occ_map.get(occupation, {"OCCAT1": 1, "OCCAT2": 2})

def map_income_to_features(income_range: str) -> dict:
    income_to_inccat = {
        "Under $30K": 1, "$30K-$55K": 2, "$55K-$90K": 3,
        "$90K-$150K": 4, "$150K-$250K": 5, "Over $250K": 6
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
    nw_map = {"Under $30K": 1, "$30K-$200K": 2, "$200K-$700K": 3, "$700K-$2M": 4, "Over $2M": 5}
    nwcat = nw_map.get(networth_range, 3)
    return {"NWCAT": nwcat, "NWPCTLECAT": {1:2, 2:4, 3:6, 4:9, 5:11}.get(nwcat, 6)}

def map_assets_to_features(assets_range: str) -> dict:
    asset_map = {"Under $30K": 1, "$30K-$200K": 2, "$200K-$500K": 3, "$500K-$1M": 4, "$1M-$2M": 5, "Over $2M": 6}
    return {"ASSETCAT": asset_map.get(assets_range, 3)}

def build_model_features(age, education, occupation, income_range, networth_range,
                         assets_range, has_emergency, has_savings_checking,
                         has_mutual_funds, has_retirement):
    features = {}
    features.update(map_age_to_features(age))
    features.update(map_education_to_features(education))
    features.update(map_occupation_to_features(occupation))
    features.update(map_income_to_features(income_range))
    features.update(map_networth_to_features(networth_range))
    features.update(map_assets_to_features(assets_range))
    features.update({"EMERGSAV": int(has_emergency), "HSAVFIN": int(has_savings_checking),
                     "HNMMF": int(has_mutual_funds), "HRETQLIQ": int(has_retirement)})
    return features


INVESTOR_PROFILES = {
    'conservative': {
        'inputs': {'age': 58, 'education': "Some College", 'occupation': "Employee/Salaried",
                   'income_range': "$55K-$90K", 'networth_range': "$200K-$700K",
                   'assets_range': "$200K-$500K", 'has_emergency': True,
                   'has_savings_checking': True, 'has_mutual_funds': False, 'has_retirement': True}
    },
    'moderate': {
        'inputs': {'age': 45, 'education': "Bachelor's", 'occupation': "Employee/Salaried",
                   'income_range': "$90K-$150K", 'networth_range': "$200K-$700K",
                   'assets_range': "$200K-$500K", 'has_emergency': True,
                   'has_savings_checking': True, 'has_mutual_funds': True, 'has_retirement': True}
    },
    'aggressive': {
        'inputs': {'age': 28, 'education': "Master's", 'occupation': "Self-Employed",
                   'income_range': "Over $250K", 'networth_range': "Over $2M",
                   'assets_range': "Over $2M", 'has_emergency': True,
                   'has_savings_checking': True, 'has_mutual_funds': True, 'has_retirement': True}
    },
}


def load_risk_score(profile_key, risk_model_path):
    with open(risk_model_path, 'rb') as f:
        risk_data = pickle.load(f)
    model = risk_data['model']
    feature_names = risk_data['features']
    inputs = INVESTOR_PROFILES[profile_key]['inputs']
    features = build_model_features(**inputs)
    feature_vector = [features.get(feat, 0) for feat in feature_names]
    X = np.array([feature_vector])
    return float(np.clip(model.predict(X)[0], 0, 100))


def load_model_scores(script_dir):
    with open(script_dir / 'output' / 'model_1y.pkl', 'rb') as f:
        fund_data = pickle.load(f)
    df_fund = pd.read_csv(script_dir / 'output' / 'preprocessed_data.csv')
    X_fund = df_fund[fund_data['feature_names']].replace([np.inf, -np.inf], np.nan)
    for col in X_fund.columns:
        X_fund[col] = X_fund[col].fillna(X_fund[col].median())
    fund_scores = dict(zip(df_fund['ticker'].values, fund_data['model'].predict(X_fund).astype(float)))

    with open(script_dir / 'output_technical' / 'model_1y.pkl', 'rb') as f:
        tech_data = pickle.load(f)
    df_tech = pd.read_csv(script_dir / 'output_technical' / 'technical_features_preprocessed.csv')
    X_tech = df_tech[tech_data['feature_names']].replace([np.inf, -np.inf], np.nan)
    for col in X_tech.columns:
        X_tech[col] = X_tech[col].fillna(X_tech[col].median())
    tech_scores = dict(zip(df_tech['ticker'].values, tech_data['model'].predict(X_tech).astype(float)))

    return fund_scores, tech_scores


def backtest_portfolio(portfolio, daily_prices, spy_daily, start_date='2024-01-01'):
    if not portfolio.get('allocations'):
        return {}

    tickers = [a['ticker'] for a in portfolio['allocations']]
    weights = np.array([a['weight_pct'] / 100.0 for a in portfolio['allocations']])
    weights = weights / weights.sum()

    port_prices = daily_prices[daily_prices['ticker'].isin(tickers)].copy()
    port_prices = port_prices[port_prices['date'] >= start_date]
    price_pivot = port_prices.pivot_table(index='date', columns='ticker', values='adj_close').sort_index()

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

    spy = spy_daily[spy_daily['date'] >= start_date].sort_values('date')
    spy_ret = spy['adj_close'].pct_change().dropna() if len(spy) > 1 else pd.Series(dtype=float)

    port_cum = (1 + pd.Series(port_daily)).cumprod()
    spy_cum = (1 + spy_ret).cumprod() if len(spy_ret) > 0 else pd.Series([1])

    trading_days = 252
    ann_return = port_daily.mean() * trading_days
    ann_vol = port_daily.std() * np.sqrt(trading_days)
    sharpe = (ann_return - 0.04) / ann_vol if ann_vol > 0 else 0

    running_max = port_cum.cummax()
    max_dd = ((port_cum - running_max) / running_max).min()

    spy_ann_return = spy_ret.mean() * trading_days if len(spy_ret) > 0 else 0
    spy_sharpe = ((spy_ann_return - 0.04) / (spy_ret.std() * np.sqrt(trading_days))) if len(spy_ret) > 0 else 0

    return {
        'annual_return': ann_return,
        'annual_volatility': ann_vol,
        'sharpe_ratio': sharpe,
        'max_drawdown': max_dd,
        'total_return': port_cum.iloc[-1] - 1,
        'spy_return': spy_cum.iloc[-1] - 1 if len(spy_cum) > 0 else 0,
        'spy_sharpe': spy_sharpe,
        'n_holdings': len(available),
    }


def main():
    script_dir = Path(__file__).parent
    capital = 100_000
    risk_model_path = script_dir / 'risk prediction' / 'risk_tolerance_model.pkl'

    print("\n" + "=" * 90)
    print("ENHANCED PORTFOLIO TEST - Beating S&P 500")
    print("=" * 90)

    print("\nLoading data...")
    daily_prices = pd.read_csv(script_dir / 'daily_prices_all.csv', parse_dates=['date'])
    spy_daily = daily_prices[daily_prices['ticker'] == 'SPY'].copy()
    daily_prices = daily_prices[daily_prices['ticker'] != 'SPY']
    fundamental_df = pd.read_csv(script_dir / 'output' / 'preprocessed_data.csv')

    print("Loading model predictions...")
    fund_scores, tech_scores = load_model_scores(script_dir)
    composite_df = compute_composite_scores(fund_scores, tech_scores)
    stock_risk_df = compute_stock_risk_scores(daily_prices, spy_daily, fundamental_df)

    results = []

    for profile_key in ['conservative', 'moderate', 'aggressive']:
        print("\n" + "=" * 90)
        print(f"PROFILE: {profile_key.upper()}")
        print("=" * 90)

        risk_score = load_risk_score(profile_key, risk_model_path)
        print(f"\nRisk Score: {risk_score:.1f}/100")

        portfolio = build_portfolio_enhanced(
            composite_df, stock_risk_df, risk_score, capital,
            fundamental_df=fundamental_df,
            daily_prices=daily_prices,
            spy_daily=spy_daily
        )

        if 'error' in portfolio:
            print(f"ERROR: {portfolio['error']}")
            continue

        print(f"\nCategory: {portfolio['category']}")
        print(f"Equity: {portfolio['equity_weight']:.1f}%, Cash: {portfolio['cash_weight']:.1f}%")
        print(f"Buckets: {portfolio['buckets']}")
        print(f"Holdings: {portfolio['n_holdings']}")

        bt = backtest_portfolio(portfolio, daily_prices, spy_daily)

        if bt:
            print(f"\nResults:")
            print(f"  Annual Return:  {bt['annual_return']:.1%}")
            print(f"  Volatility:      {bt['annual_volatility']:.1%}")
            print(f"  Sharpe Ratio:    {bt['sharpe_ratio']:.2f}")
            print(f"  Max Drawdown:    {bt['max_drawdown']:.1%}")
            print(f"  Total Return:    {bt['total_return']:.1%}")
            print(f"\n  S&P 500 Return:  {bt['spy_return']:.1%}")
            print(f"  S&P Sharpe:      {bt['spy_sharpe']:.2f}")

            if bt['annual_return'] > bt['spy_return']:
                print(f"\n  [PASS] BEAT S&P 500 by {bt['annual_return'] - bt['spy_return']:.1%}!")
            else:
                print(f"\n  [FAIL] Underperformed S&P 500 by {bt['spy_return'] - bt['annual_return']:.1%}")

            results.append({
                'profile': profile_key,
                'risk_score': risk_score,
                'return': bt['annual_return'],
                'sharpe': bt['sharpe_ratio'],
                'spy_return': bt['spy_return'],
                'spy_sharpe': bt['spy_sharpe'],
                'beat_spy': bt['annual_return'] > bt['spy_return'],
            })

    # Summary
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)
    print(f"\n{'Profile':<15} {'Return':>10} {'Sharpe':>10} {'S&P Return':>12} {'Beat S&P':>10}")
    print("-" * 60)
    for r in results:
        status = "[PASS]" if r['beat_spy'] else "[FAIL]"
        print(f"{r['profile']:<15} {r['return']:>10.1%} {r['sharpe']:>10.2f} {r['spy_return']:>12.1%} {status:>10}")


if __name__ == '__main__':
    main()