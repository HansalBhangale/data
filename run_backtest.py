#!/usr/bin/env python
"""
Portfolio Backtester — compares risk-matched portfolios against S&P 500.

For each investor profile (Conservative, Moderate, Aggressive):
1. Uses historical model predictions (quarter by quarter)
2. Builds risk-matched portfolios
3. Computes 1-year forward returns
4. Compares to SPY benchmark
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import warnings

warnings.filterwarnings('ignore')

# Stub classes for risk model unpickling
class PCABasedRiskScorer:
    def __init__(self, df=None): self.df = df
class EmpiricalCorrelationScorer:
    def __init__(self, df=None): self.df = df

from composite.scorer import compute_composite_scores
from composite.stock_risk import compute_stock_risk_scores
from composite.portfolio import build_portfolio, get_assigned_buckets


def load_model_predictions_from_data(model_path, scaler_path, data_df, feature_col_name='feature_names'):
    """Load model and generate predictions for given data."""
    with open(model_path, 'rb') as f:
        model_data = pickle.load(f)
    model = model_data['model']
    feature_cols = model_data.get(feature_col_name, model_data.get('feature_names', []))

    # Prepare features
    available_cols = [c for c in feature_cols if c in data_df.columns]
    if len(available_cols) < len(feature_cols):
        missing = set(feature_cols) - set(available_cols)
        print(f"    Missing {len(missing)} features, filling with median")

    X = data_df[feature_cols].copy()
    X = X.replace([np.inf, -np.inf], np.nan)
    for col in X.columns:
        median_val = X[col].median()
        X[col] = X[col].fillna(median_val)

    preds = model.predict(X)
    return {ticker: float(pred) for ticker, pred in zip(data_df['ticker'].values, preds)}


def compute_1y_forward_returns(daily_prices):
    """Compute 1-year forward returns for each stock at each quarter-end."""
    daily_prices = daily_prices.copy()
    daily_prices['date'] = pd.to_datetime(daily_prices['date'])
    daily_prices = daily_prices.sort_values(['ticker', 'date'])

    # Get quarter-end dates
    quarter_ends = daily_prices['date'].dt.to_period('Q').unique()
    quarter_ends = pd.Series(quarter_ends).sort_values()
    quarter_ends = quarter_ends.dt.to_timestamp(how='end')

    returns_data = []
    for ticker, grp in daily_prices.groupby('ticker'):
        grp = grp.sort_values('date')
        for q_end in quarter_ends:
            # Find price at quarter-end
            mask_before = grp['date'] <= q_end
            before = grp[mask_before]
            if len(before) == 0:
                continue
            price_start = before.iloc[-1]['adj_close']
            actual_date = before.iloc[-1]['date']

            # Find price 1 year later
            target_date = q_end + pd.DateOffset(years=1)
            mask_after = (grp['date'] > q_end) & (grp['date'] <= target_date)
            after = grp[mask_after]
            if len(after) == 0:
                continue
            price_end = after.iloc[-1]['adj_close']

            fwd_return = (price_end / price_start) - 1
            returns_data.append({
                'ticker': ticker,
                'quarter_end': q_end,
                'start_date': actual_date,
                'end_date': after.iloc[-1]['date'],
                'fwd_return_1y': fwd_return,
            })

    if not returns_data:
        return pd.DataFrame(columns=['ticker', 'quarter_end', 'start_date', 'end_date', 'fwd_return_1y'])
    df = pd.DataFrame(returns_data)
    df['quarter_end'] = pd.to_datetime(df['quarter_end'])
    df['start_date'] = pd.to_datetime(df['start_date'])
    df['end_date'] = pd.to_datetime(df['end_date'])
    return df.reset_index(drop=True)


def compute_spy_returns(spy_daily):
    """Compute SPY 1-year forward returns at each quarter-end."""
    spy = spy_daily.copy()
    spy['date'] = pd.to_datetime(spy['date'])
    spy = spy.sort_values('date')

    quarter_ends = spy['date'].dt.to_period('Q').unique()
    quarter_ends = pd.Series(quarter_ends).sort_values()
    quarter_ends = quarter_ends.dt.to_timestamp(how='end')

    spy_returns = []
    for q_end in quarter_ends:
        q_end_ts = pd.Timestamp(q_end)
        mask_before = spy['date'] <= q_end_ts
        before = spy[mask_before]
        if len(before) == 0:
            continue
        price_start = before.iloc[-1]['adj_close']

        target_date = q_end_ts + pd.DateOffset(years=1)
        mask_after = (spy['date'] > q_end_ts) & (spy['date'] <= target_date)
        after = spy[mask_after]
        if len(after) == 0:
            continue
        price_end = after.iloc[-1]['adj_close']

        fwd_return = (price_end / price_start) - 1
        spy_returns.append({
            'quarter_end': q_end_ts,
            'spy_return_1y': fwd_return,
        })

    if not spy_returns:
        return pd.DataFrame(columns=['quarter_end', 'spy_return_1y'])
    df = pd.DataFrame(spy_returns)
    df['quarter_end'] = pd.to_datetime(df['quarter_end'])
    return df.reset_index(drop=True)


def run_backtest(
    daily_prices,
    fundamental_df,
    spy_daily,
    risk_model_path,
    capital=100_000,
):
    """
    Full backtest: for each quarter, build portfolios and compute 1-year returns.
    """
    print("\n" + "=" * 80)
    print(" PORTFOLIO BACKTEST vs S&P 500")
    print("=" * 80)

    # Load models
    fund_model_path = Path('output/model_1y.pkl')
    tech_model_path = Path('output_technical/model_1y.pkl')

    if not fund_model_path.exists() or not tech_model_path.exists():
        print("  ERROR: Model files not found. Run training first.")
        return

    # Compute stock risk scores
    print("\n  Computing stock risk scores...")
    stock_risk_df = compute_stock_risk_scores(daily_prices, spy_daily, fundamental_df)

    # Compute 1-year forward returns
    print("  Computing 1-year forward returns...")
    fwd_returns = compute_1y_forward_returns(daily_prices)
    spy_rets = compute_spy_returns(spy_daily)

    # Get quarter-end dates from fundamental data
    fundamental_df['quarter_end'] = pd.to_datetime(fundamental_df['quarter_end'])
    quarters = sorted(fundamental_df['quarter_end'].dt.to_period('Q').unique())
    quarters = [q.to_timestamp(how='end') for q in quarters]

    # Investor profiles
    profiles = {
        'Conservative': {'risk_score': 35, 'buckets': [1, 2]},
        'Moderate': {'risk_score': 50, 'buckets': [2, 3]},
        'Aggressive': {'risk_score': 85, 'buckets': [4, 5]},
    }

    # For each quarter, generate predictions and build portfolios
    print(f"\n  Backtesting {len(quarters)} quarters...")

    portfolio_returns = {name: [] for name in profiles}
    spy_returns_list = []
    quarter_labels = []

    for i, q_end in enumerate(quarters):
        # Get data up to this quarter
        hist_fund = fundamental_df[fundamental_df['quarter_end'] <= q_end].copy()
        hist_daily = daily_prices[daily_prices['date'] <= q_end].copy()
        hist_spy = spy_daily[spy_daily['date'] <= q_end].copy()

        if len(hist_fund) < 100 or len(hist_daily) < 100:
            continue

        # Generate predictions for this quarter's latest data
        # Use the latest quarter's data for each ticker
        latest_fund = hist_fund.sort_values('quarter_end').groupby('ticker').last().reset_index()
        latest_daily = hist_daily.sort_values('date').groupby('ticker').last().reset_index()

        # Load models and generate predictions
        try:
            fund_scores = load_model_predictions_from_data(
                str(fund_model_path), None, latest_fund
            )
        except:
            continue

        # For technical, we need to compute features from historical daily data
        # Simplified: use the latest technical features if available
        tech_features_path = Path('output_technical/technical_features.csv')
        if tech_features_path.exists():
            tech_df = pd.read_csv(tech_features_path, parse_dates=['quarter_end'])
            tech_hist = tech_df[tech_df['quarter_end'] <= q_end].copy()
            if len(tech_hist) > 0:
                latest_tech = tech_hist.sort_values('quarter_end').groupby('ticker').last().reset_index()
                from sp500_technical.preprocessing import compute_sector_zscores, clip_outliers
                latest_tech = clip_outliers(latest_tech)
                latest_tech = compute_sector_zscores(latest_tech)
                try:
                    tech_scores = load_model_predictions_from_data(
                        str(tech_model_path), None, latest_tech
                    )
                except:
                    continue
            else:
                continue
        else:
            continue

        # Compute composite scores
        composite_df = compute_composite_scores(fund_scores, tech_scores)

        # Recompute stock risk for this quarter
        try:
            stock_risk = compute_stock_risk_scores(hist_daily, hist_spy, hist_fund)
        except:
            continue

        # Build portfolios for each profile
        for name, params in profiles.items():
            portfolio = build_portfolio(
                composite_df, stock_risk, params['risk_score'], capital, top_n_per_bucket=10
            )

            if 'error' in portfolio or not portfolio.get('allocations'):
                portfolio_returns[name].append(np.nan)
                continue

            # Compute portfolio return
            port_ret = 0.0
            total_weight = 0.0
            for alloc in portfolio['allocations']:
                ticker = alloc['ticker']
                weight = alloc['weight_pct'] / 100.0
                # Get forward return for this stock
                q_end_str = pd.Timestamp(q_end).strftime('%Y-%m-%d')
                if 'q_str' not in fwd_returns.columns:
                    fwd_returns['q_str'] = fwd_returns['quarter_end'].dt.strftime('%Y-%m-%d')
                stock_rets = fwd_returns[
                    (fwd_returns['ticker'] == ticker) &
                    (fwd_returns['q_str'] == q_end_str)
                ]
                if len(stock_rets) > 0:
                    ret = stock_rets.iloc[0]['fwd_return_1y']
                    if not np.isnan(ret):
                        port_ret += weight * ret
                        total_weight += weight

            if total_weight > 0:
                port_ret = port_ret / total_weight
                portfolio_returns[name].append(port_ret)
            else:
                portfolio_returns[name].append(np.nan)

        # Get SPY return for this quarter
        q_end_str = pd.Timestamp(q_end).strftime('%Y-%m-%d')
        spy_rets['q_str'] = spy_rets['quarter_end'].dt.strftime('%Y-%m-%d')
        spy_ret_match = spy_rets[spy_rets['q_str'] == q_end_str]
        if len(spy_ret_match) > 0:
            spy_returns_list.append(spy_ret_match.iloc[0]['spy_return_1y'])
        else:
            spy_returns_list.append(np.nan)

        quarter_labels.append(q_end.strftime('%Y-%m'))

    # Compute results
    print("\n" + "-" * 80)
    print(f"  {'Quarter':<12}", end='')
    for name in profiles:
        print(f" {name:>14}", end='')
    print(f" {'S&P 500':>12}")
    print("  " + "-" * 76)

    for i, label in enumerate(quarter_labels):
        print(f"  {label:<12}", end='')
        for name in profiles:
            ret = portfolio_returns[name][i] if i < len(portfolio_returns[name]) else np.nan
            if np.isnan(ret):
                print(f" {'N/A':>14}", end='')
            else:
                print(f" {ret:>+13.2%}", end='')
        spy_ret = spy_returns_list[i] if i < len(spy_returns_list) else np.nan
        if np.isnan(spy_ret):
            print(f" {'N/A':>12}")
        else:
            print(f" {spy_ret:>+11.2%}")

    # Summary statistics
    print("\n" + "=" * 80)
    print(" BACKTEST SUMMARY")
    print("=" * 80)

    print(f"\n  {'Metric':<25}", end='')
    for name in profiles:
        print(f" {name:>14}", end='')
    print(f" {'S&P 500':>12}")
    print("  " + "-" * 76)

    for name in profiles:
        rets = np.array([r for r in portfolio_returns[name] if not np.isnan(r)])
        if len(rets) > 0:
            ann_ret = np.mean(rets)
            ann_vol = np.std(rets)
            sharpe = ann_ret / (ann_vol + 1e-10)
            win_rate = np.mean(rets > 0)
            print(f"  {name:<25}")
            print(f"    Periods:              {len(rets)}")
            print(f"    Avg 1-Year Return:    {np.mean(rets):+.2%}")
            print(f"    Annualized Return:    {ann_ret:+.2%}")
            print(f"    Annualized Vol:       {ann_vol:.2%}")
            print(f"    Sharpe Ratio:         {sharpe:.2f}")
            print(f"    Win Rate:             {win_rate:.0%}")
        else:
            print(f"  {name:<25}: No valid periods")

    spy_rets_arr = np.array([r for r in spy_returns_list if not np.isnan(r)])
    if len(spy_rets_arr) > 0:
        spy_ann = np.mean(spy_rets_arr)
        spy_vol = np.std(spy_rets_arr)
        spy_sharpe = spy_ann / (spy_vol + 1e-10)
        print(f"\n  S&P 500 Benchmark:")
        print(f"    Periods:              {len(spy_rets_arr)}")
        print(f"    Avg 1-Year Return:    {np.mean(spy_rets_arr):+.2%}")
        print(f"    Annualized Return:    {spy_ann:+.2%}")
        print(f"    Annualized Vol:       {spy_vol:.2%}")
        print(f"    Sharpe Ratio:         {spy_sharpe:.2f}")
        print(f"    Win Rate:             {np.mean(spy_rets_arr > 0):.0%}")

    print("\n" + "=" * 80)


def main():
    """Run the backtest."""
    print("\n" + "=" * 80)
    print(" LOADING DATA")
    print("=" * 80)

    # Load daily prices
    daily_prices_path = Path('daily_prices_all.csv')
    if daily_prices_path.exists():
        daily_prices = pd.read_csv(daily_prices_path, parse_dates=['date'])
        spy_daily = daily_prices[daily_prices['ticker'] == 'SPY'].copy()
        daily_prices = daily_prices[daily_prices['ticker'] != 'SPY']
        print(f"  Daily prices: {len(daily_prices)} rows, {daily_prices['ticker'].nunique()} tickers")
    else:
        print("  ERROR: daily_prices_all.csv not found.")
        return

    # Load fundamental data
    fund_path = Path('output/preprocessed_data.csv')
    if fund_path.exists():
        fundamental_df = pd.read_csv(fund_path)
    else:
        fundamental_df = pd.read_csv('sp500_fundamental_dataset.csv')
    print(f"  Fundamental data: {len(fundamental_df)} rows")

    # Run backtest
    run_backtest(
        daily_prices, fundamental_df, spy_daily,
        risk_model_path='risk prediction/risk_tolerance_model.pkl',
        capital=100_000,
    )


if __name__ == '__main__':
    main()
