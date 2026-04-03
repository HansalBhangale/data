"""
Enhanced Portfolio Construction - Momentum + Quality + Risk Adjusted.

Key improvements:
1. Dynamic bucket weights based on exact risk score
2. Quality scores with confidence weighting (reduce when data missing)
3. PyPortfolioOpt optimization for optimal weights
4. All profiles designed to beat S&P 500 while managing risk
5. Proper risk controls per profile
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple
import warnings

warnings.filterwarnings('ignore')


def _fetch_historical_prices(tickers: List[str], period: str = '1y') -> pd.DataFrame:
    """Fetch historical daily closing prices for a list of tickers."""
    try:
        import yfinance as yf
        data = yf.download(tickers, period=period, progress=False)
        if isinstance(data.columns, pd.MultiIndex):
            price_cols = [c for c in ['Adj Close', 'Close'] if c in data.columns.get_level_values(0)]
            if price_cols:
                price_data = data.xs(price_cols[0], level=0, axis=1)
            else:
                return pd.DataFrame()
        else:
            price_data = data
        if isinstance(price_data, pd.Series):
            price_data = price_data.to_frame()
        price_data = price_data.dropna(axis=1, thresh=len(price_data) * 0.8)
        if price_data.empty or len(price_data) < 60:
            return pd.DataFrame()
        return price_data
    except Exception:
        return pd.DataFrame()


def compute_momentum_scores(daily_prices: pd.DataFrame, lookback: int = 252) -> Dict[str, float]:
    """
    Compute momentum score for each stock based on recent performance.
    """
    daily_prices = daily_prices.copy()
    daily_prices['date'] = pd.to_datetime(daily_prices['date'])
    momentum_scores = {}

    for ticker, grp in daily_prices.groupby('ticker'):
        grp = grp.sort_values('date').reset_index(drop=True)
        if len(grp) < lookback:
            continue
        close = grp['adj_close'].values[-lookback:]
        price_return = (close[-1] - close[0]) / close[0]
        returns = np.diff(close) / close[:-1]
        vol = np.std(returns) * np.sqrt(252)
        risk_adj_return = price_return / (vol + 0.01) if vol > 0 else 0
        positive_days = np.sum(returns > 0) / len(returns) if len(returns) > 0 else 0.5
        momentum_score = (
            0.4 * (1 / (1 + np.exp(-5 * price_return))) +
            0.4 * (1 / (1 + np.exp(-2 * risk_adj_return))) +
            0.2 * positive_days
        )
        momentum_scores[ticker] = momentum_score

    return momentum_scores


def compute_quality_scores(fundamental_df: pd.DataFrame) -> Tuple[Dict[str, float], Dict[str, float]]:
    """
    Compute quality score and confidence score based on fundamentals.
    
    Returns:
        quality_scores: {ticker: quality_score (0-1)}
        confidence_scores: {ticker: confidence (0-1)} - proportion of data available
    """
    if fundamental_df is None or len(fundamental_df) == 0:
        return {}, {}

    quality_scores = {}
    confidence_scores = {}

    fund_latest = fundamental_df.sort_values('quarter_end').groupby('ticker').last().reset_index()

    sector_medians = {}
    if 'sector' in fund_latest.columns:
        for col in ['net_income', 'stockholders_equity', 'total_debt', 'revenue']:
            if col in fund_latest.columns:
                sector_medians[col] = fund_latest.groupby('sector')[col].median().to_dict()

    market_medians = {}
    for col in ['net_income', 'stockholders_equity', 'total_debt', 'revenue']:
        if col in fund_latest.columns:
            market_medians[col] = fund_latest[col].median()

    for _, row in fund_latest.iterrows():
        ticker = row['ticker']
        scores = []
        fields_found = 0
        total_fields = 3

        has_equity = 'stockholders_equity' in row and pd.notna(row.get('stockholders_equity'))
        has_income = 'net_income' in row and pd.notna(row.get('net_income'))
        has_debt = 'total_debt' in row and pd.notna(row.get('total_debt'))
        has_revenue = 'revenue' in row and pd.notna(row.get('revenue'))

        if has_equity and has_income:
            equity = abs(row['stockholders_equity'])
            net_income = row['net_income']
            roe = net_income / (equity + 1e-10)
            if -1 <= roe <= 2:
                scores.append(max(0, min(1, (roe + 0.5) / 1.5)))
                fields_found += 1
            else:
                if 'sector' in row and 'net_income' in sector_medians:
                    sector = row['sector']
                    if sector in sector_medians['net_income']:
                        scores.append(0.5)
                        fields_found += 0.5

        if has_equity and has_debt:
            debt = row['total_debt']
            equity = abs(row['stockholders_equity'])
            dte = debt / (equity + 1e-10)
            if dte >= 0:
                scores.append(max(0, 1 - dte / 5))
                fields_found += 1

        if has_revenue:
            fields_found += 1

        if scores:
            quality_scores[ticker] = np.mean(scores)
            confidence_scores[ticker] = fields_found / total_fields
        else:
            quality_scores[ticker] = 0.5
            confidence_scores[ticker] = 0.0

    return quality_scores, confidence_scores


def calculate_bucket_weights(risk_score: float) -> Dict:
    """
    Calculate bucket weights dynamically based on exact risk score.
    Higher investor risk score = higher stock buckets (riskier stocks).
    Lower investor risk score = lower stock buckets (safer stocks).
    """
    if risk_score <= 20:
        return {'buckets': [1, 2, 3], 'bucket_weights': [0.40, 0.35, 0.25]}
    elif risk_score <= 35:
        return {'buckets': [1, 2, 3, 4], 'bucket_weights': [0.25, 0.30, 0.30, 0.15]}
    elif risk_score <= 50:
        return {'buckets': [2, 3, 4, 5], 'bucket_weights': [0.15, 0.30, 0.35, 0.20]}
    elif risk_score <= 70:
        return {'buckets': [3, 4, 5], 'bucket_weights': [0.10, 0.35, 0.55]}
    elif risk_score <= 85:
        return {'buckets': [4, 5], 'bucket_weights': [0.25, 0.75]}
    else:
        return {'buckets': [5], 'bucket_weights': [1.0]}


INVESTOR_PARAMS_ENHANCED = {
    (0, 20):   {'category': 'Ultra Conservative', 'base_equity': 0.95, 'cash_reserve': 0.05,
                'quality_weight': 0.20, 'momentum_weight': 0.30, 'max_weight_per_stock': 0.15, 'min_holdings': 10},
    (21, 35):  {'category': 'Conservative', 'base_equity': 0.97, 'cash_reserve': 0.03,
                'quality_weight': 0.15, 'momentum_weight': 0.35, 'max_weight_per_stock': 0.15, 'min_holdings': 10},
    (36, 50):  {'category': 'Moderate', 'base_equity': 0.98, 'cash_reserve': 0.02,
                'quality_weight': 0.15, 'momentum_weight': 0.40, 'max_weight_per_stock': 0.18, 'min_holdings': 10},
    (51, 70):  {'category': 'Growth', 'base_equity': 0.99, 'cash_reserve': 0.01,
                'quality_weight': 0.10, 'momentum_weight': 0.45, 'max_weight_per_stock': 0.20, 'min_holdings': 10},
    (71, 85):  {'category': 'Aggressive', 'base_equity': 0.99, 'cash_reserve': 0.01,
                'quality_weight': 0.05, 'momentum_weight': 0.50, 'max_weight_per_stock': 0.22, 'min_holdings': 10},
    (86, 100): {'category': 'Ultra Aggressive', 'base_equity': 0.99, 'cash_reserve': 0.01,
                'quality_weight': 0.05, 'momentum_weight': 0.55, 'max_weight_per_stock': 0.25, 'min_holdings': 10},
}


def get_enhanced_params(risk_score: float) -> Dict:
    """Get enhanced portfolio parameters."""
    for (low, high), params in INVESTOR_PARAMS_ENHANCED.items():
        if low <= risk_score <= high:
            return params.copy()
    return INVESTOR_PARAMS_ENHANCED[(36, 50)].copy()


def _optimize_weights_enhanced(
    portfolio_stocks: pd.DataFrame,
    min_weight: float = 0.02,
    max_weight: float = 0.20,
    risk_free_rate: float = 0.04,
) -> Optional[np.ndarray]:
    """
    Optimize portfolio weights using PyPortfolioOpt Max Sharpe.
    
    Uses final_score * 0.15 as expected annual returns to beat S&P (~10%).
    """
    try:
        import os
        os.environ['CVXPY_PRINT_SOLVER_STATUS'] = '0'

        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            from pypfopt import EfficientFrontier
            from pypfopt import risk_models

        tickers = portfolio_stocks['ticker'].tolist()
        final_scores = portfolio_stocks['final_score'].values

        prices = _fetch_historical_prices(tickers)

        if prices.empty or len(prices) < 60:
            return None

        available = [t for t in tickers if t in prices.columns]
        if len(available) < 3:
            return None

        prices = prices[available]

        mu = pd.Series(
            [final_scores[tickers.index(t)] * 0.15 for t in available],
            index=available,
        )

        S = risk_models.sample_cov(prices, frequency=252)

        if np.isnan(S.values).any() or np.isinf(S.values).any():
            return None

        ef = EfficientFrontier(mu, S, weight_bounds=(min_weight, max_weight))
        ef.max_sharpe(risk_free_rate=risk_free_rate)
        weights = ef.clean_weights()

        weight_array = np.array([weights.get(t, 0.0) for t in tickers])

        if weight_array.sum() <= 0:
            return None

        weight_array /= weight_array.sum()

        perf = ef.portfolio_performance(risk_free_rate)
        print(f"      PyPortfolioOpt: Return={perf[0]:.1%}, Vol={perf[1]:.1%}, Sharpe={perf[2]:.2f}")

        return weight_array

    except ImportError:
        print("      WARNING: PyPortfolioOpt not installed, using score-based weights")
        return None
    except Exception as e:
        print(f"      WARNING: Optimization failed ({e}), using score-based weights")
        return None


def _weight_by_scores_enhanced(
    portfolio_stocks: pd.DataFrame,
    gamma: float = 1.5,
    min_weight: float = 0.02,
    max_weight: float = 0.20,
) -> np.ndarray:
    """Weight stocks by exponential score weighting."""
    scores = portfolio_stocks['final_score'].values
    raw_weights = np.power(scores, gamma)
    weights = raw_weights / raw_weights.sum()

    if 'bucket_weight' in portfolio_stocks.columns:
        bucket_weight_mult = portfolio_stocks['bucket_weight'].values
        weights = weights * bucket_weight_mult
        weights = weights / weights.sum()

    for _ in range(10):
        excess = np.maximum(weights - max_weight, 0)
        if excess.sum() < 1e-10:
            break
        weights = np.minimum(weights, max_weight)
        remaining = weights < max_weight
        if remaining.sum() > 0 and excess.sum() > 0:
            weights[remaining] += excess.sum() * (weights[remaining] / weights[remaining].sum())

    mask = weights >= min_weight
    weights = weights * mask
    if weights.sum() > 0:
        weights /= weights.sum()

    return weights


def build_portfolio_enhanced(
    composite_df: pd.DataFrame,
    stock_risk_df: pd.DataFrame,
    investor_risk_score: float,
    capital: float = 100_000,
    fundamental_df: pd.DataFrame = None,
    daily_prices: pd.DataFrame = None,
    spy_daily: pd.DataFrame = None,
    top_n: int = 25,
    max_stocks: int = 10,
    use_optimization: bool = True,
) -> Dict:
    """
    Build enhanced portfolio with momentum, quality, and PyPortfolioOpt.
    
    Key features:
    1. Dynamic bucket weights - all profiles can beat S&P
    2. Quality confidence adjustment - reduces weight when data missing
    3. PyPortfolioOpt optimization for optimal Sharpe
    4. Proper risk controls per profile
    """
    params = get_enhanced_params(investor_risk_score)
    bucket_config = calculate_bucket_weights(investor_risk_score)

    momentum_scores = {}
    if daily_prices is not None:
        momentum_scores = compute_momentum_scores(daily_prices)

    quality_scores, quality_confidence = compute_quality_scores(fundamental_df)

    merged = composite_df.merge(
        stock_risk_df[['ticker', 'stock_risk_score', 'risk_bucket']],
        on='ticker',
        how='inner'
    )

    if momentum_scores:
        merged['momentum_score'] = merged['ticker'].map(momentum_scores).fillna(0.5)
    else:
        merged['momentum_score'] = 0.5

    if quality_scores:
        merged['quality_score'] = merged['ticker'].map(quality_scores).fillna(0.5)
    else:
        merged['quality_score'] = 0.5

    if quality_confidence:
        merged['quality_confidence'] = merged['ticker'].map(quality_confidence).fillna(0.0)
    else:
        merged['quality_confidence'] = 0.0

    base_quality_weight = params['quality_weight']
    base_momentum_weight = params['momentum_weight']
    base_composite_weight = 1 - base_quality_weight - base_momentum_weight

    adjusted_quality_weight = base_quality_weight * merged['quality_confidence']
    total_weight = base_composite_weight + base_momentum_weight + adjusted_quality_weight

    composite_weight = base_composite_weight / total_weight
    momentum_weight = base_momentum_weight / total_weight
    quality_weight = adjusted_quality_weight / total_weight

    risk_adj_factor = 0
    if investor_risk_score > 50:
        risk_adj_factor = -0.05

    merged['risk_norm'] = merged['stock_risk_score'] / 100

    allowed_buckets = bucket_config['buckets']
    bucket_weights = bucket_config['bucket_weights']

    eligible = merged[merged['risk_bucket'].isin(allowed_buckets)].copy()

    if len(eligible) == 0:
        return {
            'error': 'No eligible stocks',
            'investor_risk_score': investor_risk_score,
        }

    eligible['final_score'] = (
        composite_weight * eligible['composite_score'] +
        momentum_weight * eligible['momentum_score'] +
        quality_weight * eligible['quality_score'] -
        risk_adj_factor * (eligible['risk_norm'] - 0.5)
    )

    selected_stocks = []
    for bucket, weight in zip(allowed_buckets, bucket_weights):
        bucket_stocks = eligible[eligible['risk_bucket'] == bucket].copy()
        bucket_stocks = bucket_stocks.sort_values('final_score', ascending=False)
        n_from_bucket = max(3, int(top_n * weight))
        bucket_stocks = bucket_stocks.head(n_from_bucket)
        bucket_stocks['bucket_weight'] = weight
        selected_stocks.append(bucket_stocks)

    portfolio_stocks = pd.concat(selected_stocks, ignore_index=True)

    # Cap to max_stocks (default 10)
    portfolio_stocks = portfolio_stocks.sort_values('final_score', ascending=False).head(max_stocks).reset_index(drop=True)

    if len(portfolio_stocks) < params['min_holdings']:
        remaining = eligible[~eligible['ticker'].isin(portfolio_stocks['ticker'])]
        remaining = remaining.sort_values('final_score', ascending=False)
        additional = remaining.head(params['min_holdings'] - len(portfolio_stocks))
        additional['bucket_weight'] = 0.1
        portfolio_stocks = pd.concat([portfolio_stocks, additional], ignore_index=True)

    portfolio_stocks = portfolio_stocks.reset_index(drop=True)

    max_weight = params['max_weight_per_stock']
    min_weight = 0.02

    if use_optimization:
        weights = _optimize_weights_enhanced(
            portfolio_stocks,
            min_weight=min_weight,
            max_weight=max_weight,
            risk_free_rate=0.04,
        )
    else:
        weights = None

    if weights is None:
        weights = _weight_by_scores_enhanced(
            portfolio_stocks,
            gamma=1.5,
            min_weight=min_weight,
            max_weight=max_weight,
        )

    mask = weights > 1e-6
    weights = weights * mask
    if weights.sum() > 0:
        weights /= weights.sum()
    portfolio_stocks = portfolio_stocks[mask].reset_index(drop=True)
    weights = weights[mask]

    equity_allocation = params['base_equity']
    cash_allocation = params['cash_reserve']

    eq_amt = capital * equity_allocation
    cash_amt = capital * cash_allocation

    allocations = []
    for i, (_, row) in enumerate(portfolio_stocks.iterrows()):
        sw = weights[i] * equity_allocation
        sa = capital * sw
        allocations.append({
            'ticker': row['ticker'],
            'composite_score': round(float(row['composite_score']), 4),
            'momentum_score': round(float(row['momentum_score']), 4),
            'quality_score': round(float(row['quality_score']), 4),
            'quality_confidence': round(float(row.get('quality_confidence', 0.5)), 4),
            'final_score': round(float(row['final_score']), 4),
            'stock_risk_score': round(float(row['stock_risk_score']), 2),
            'risk_bucket': int(row['risk_bucket']),
            'weight_pct': round(sw * 100, 2),
            'capital_allocated': round(sa, 2),
        })

    allocations.sort(key=lambda x: x['weight_pct'], reverse=True)

    return {
        'investor_risk_score': investor_risk_score,
        'category': params['category'],
        'equity_weight': round(equity_allocation * 100, 2),
        'equity_amount': round(eq_amt, 2),
        'cash_weight': round(cash_allocation * 100, 2),
        'cash_amount': round(cash_amt, 2),
        'n_holdings': len(allocations),
        'buckets': allowed_buckets,
        'bucket_weights': bucket_weights,
        'max_weight_per_stock': max_weight * 100,
        'min_holdings': params['min_holdings'],
        'composite_weight': round(float(composite_weight.mean()), 3),
        'momentum_weight': round(float(momentum_weight.mean()), 3),
        'quality_weight': round(float(quality_weight.mean()), 3),
        'allocations': allocations,
    }


def print_enhanced_report(portfolio: Dict, capital: float = 100_000):
    """Print enhanced portfolio report."""
    if 'error' in portfolio:
        print(f"\n  ERROR: {portfolio['error']}")
        return

    print("\n" + "=" * 95)
    print(" ENHANCED PORTFOLIO REPORT - Designed to Beat S&P 500")
    print("=" * 95)

    print(f"\n  Investor Risk Score: {portfolio['investor_risk_score']:.0f}/100")
    print(f"  Category: {portfolio['category']}")
    print(f"  Allowed Buckets: {portfolio['buckets']}")
    print(f"  Bucket Weights: {[round(w, 2) for w in portfolio['bucket_weights']]}")
    print(f"  Score Weights: Composite={portfolio['composite_weight']:.0%}, Momentum={portfolio['momentum_weight']:.0%}, Quality={portfolio['quality_weight']:.0%}")

    print(f"\n  Capital: ${capital:,.0f}")
    print(f"  Equity: {portfolio['equity_weight']:.1f}% (${portfolio['equity_amount']:,.0f})")
    print(f"  Cash: {portfolio['cash_weight']:.1f}% (${portfolio['cash_amount']:,.0f})")
    print(f"  Holdings: {portfolio['n_holdings']} (min: {portfolio['min_holdings']})")
    print(f"  Max Weight/Stock: {portfolio['max_weight_per_stock']:.0f}%")

    if portfolio['allocations']:
        print(f"\n  {'#':>2} {'Ticker':<8} {'Final':>6} {'Comp':>6} {'Mom':>6} {'Qual':>6} {'Conf':>6} {'Risk':>6} {'Bkt':>4} {'Wt%':>6}")
        print("  " + "-" * 85)
        for i, a in enumerate(portfolio['allocations'], 1):
            print(f"  {i:>2} {a['ticker']:<8} {a['final_score']:>6.3f} {a['composite_score']:>6.3f} "
                  f"{a['momentum_score']:>6.3f} {a['quality_score']:>6.3f} {a['quality_confidence']:>6.2f} "
                  f"{a['stock_risk_score']:>6.1f} {a['risk_bucket']:>4} {a['weight_pct']:>5.1f}%")

    print("\n" + "=" * 95)
