#!/usr/bin/env python
"""
Composite Model Pipeline Entry Point

Combines fundamental + technical model predictions with investor risk profiling
to build risk-matched portfolios.

Usage:
    python run_composite.py --profile moderate              # Generate portfolio
    python run_composite.py --profile moderate --capital 50000  # Custom capital
    python run_composite.py --risk-score 42                 # Custom risk score
    python run_composite.py --backtest                      # Backtest all buckets
    python run_composite.py --compare                       # Compare profiles
"""

import argparse
import json
import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

# Stub classes needed for unpickling the risk model
class PCABasedRiskScorer:
    def __init__(self, df=None): self.df = df
class EmpiricalCorrelationScorer:
    def __init__(self, df=None): self.df = df

from composite.scorer import compute_composite_scores
from composite.stock_risk import compute_stock_risk_scores
from composite.portfolio import (
    build_portfolio, print_portfolio_report,
    get_investor_params, get_assigned_buckets,
)
from composite.backtest import backtest_all_buckets, print_backtest_summary


# =============================================================================
# INVESTOR PROFILES (SCF-compatible)
# =============================================================================
INVESTOR_PROFILES = {
    'ultra_conservative': {
        'name': 'Ultra Conservative (Retired Senior)',
        'features': {
            'EDUC': 12, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 0,
            'HRETQLIQ': 1, 'NWCAT': 2, 'INCCAT': 1, 'ASSETCAT': 2,
            'NINCCAT': 1, 'NINC2CAT': 1, 'NWPCTLECAT': 25, 'INCPCTLECAT': 20,
            'NINCPCTLECAT': 20, 'INCQRTCAT': 1, 'NINCQRTCAT': 1,
            'AGE': 72, 'AGECL': 6, 'OCCAT1': 4, 'OCCAT2': 4
        }
    },
    'conservative': {
        'name': 'Conservative (Risk-Averse Professional)',
        'features': {
            'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 0,
            'HRETQLIQ': 1, 'NWCAT': 3, 'INCCAT': 2, 'ASSETCAT': 3,
            'NINCCAT': 2, 'NINC2CAT': 2, 'NWPCTLECAT': 40, 'INCPCTLECAT': 40,
            'NINCPCTLECAT': 40, 'INCQRTCAT': 2, 'NINCQRTCAT': 2,
            'AGE': 58, 'AGECL': 5, 'OCCAT1': 1, 'OCCAT2': 1
        }
    },
    'moderate': {
        'name': 'Moderate (Balanced Investor)',
        'features': {
            'EDUC': 16, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
            'HRETQLIQ': 1, 'NWCAT': 4, 'INCCAT': 4, 'ASSETCAT': 4,
            'NINCCAT': 3, 'NINC2CAT': 3, 'NWPCTLECAT': 60, 'INCPCTLECAT': 60,
            'NINCPCTLECAT': 60, 'INCQRTCAT': 3, 'NINCQRTCAT': 3,
            'AGE': 40, 'AGECL': 3, 'OCCAT1': 1, 'OCCAT2': 1
        }
    },
    'growth': {
        'name': 'Growth (Young High Earner)',
        'features': {
            'EDUC': 16, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
            'HRETQLIQ': 1, 'NWCAT': 5, 'INCCAT': 5, 'ASSETCAT': 5,
            'NINCCAT': 4, 'NINC2CAT': 4, 'NWPCTLECAT': 75, 'INCPCTLECAT': 75,
            'NINCPCTLECAT': 75, 'INCQRTCAT': 4, 'NINCQRTCAT': 4,
            'AGE': 32, 'AGECL': 2, 'OCCAT1': 1, 'OCCAT2': 1
        }
    },
    'aggressive': {
        'name': 'Aggressive (Young Finance Professional)',
        'features': {
            'EDUC': 17, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
            'HRETQLIQ': 1, 'NWCAT': 5, 'INCCAT': 6, 'ASSETCAT': 6,
            'NINCCAT': 5, 'NINC2CAT': 5, 'NWPCTLECAT': 85, 'INCPCTLECAT': 85,
            'NINCPCTLECAT': 85, 'INCQRTCAT': 4, 'NINCQRTCAT': 4,
            'AGE': 28, 'AGECL': 2, 'OCCAT1': 1, 'OCCAT2': 2
        }
    },
    'ultra_aggressive': {
        'name': 'Ultra Aggressive (Wealthy Risk-Seeker)',
        'features': {
            'EDUC': 17, 'EMERGSAV': 0, 'HSAVFIN': 1, 'HNMMF': 1,
            'HRETQLIQ': 1, 'NWCAT': 5, 'INCCAT': 6, 'ASSETCAT': 6,
            'NINCCAT': 6, 'NINC2CAT': 6, 'NWPCTLECAT': 95, 'INCPCTLECAT': 95,
            'NINCPCTLECAT': 95, 'INCQRTCAT': 4, 'NINCQRTCAT': 4,
            'AGE': 26, 'AGECL': 1, 'OCCAT1': 2, 'OCCAT2': 2
        }
    }
}


def predict_investor_risk(profile_key: str, risk_model_path: str) -> float:
    """Predict investor risk score from profile using trained model."""
    try:
        with open(risk_model_path, 'rb') as f:
            risk_data = pickle.load(f)
        model = risk_data['model']
        feature_names = risk_data['features']

        profile = INVESTOR_PROFILES[profile_key]
        feature_vector = [profile['features'].get(feat, 0) for feat in feature_names]
        X = np.array([feature_vector])

        risk_score = float(np.clip(model.predict(X)[0], 0, 100))
        print(f"\n  Investor Risk Score: {risk_score:.1f}/100 ({profile['name']})")
        return risk_score
    except Exception as e:
        print(f"\n  WARNING: Could not load risk model: {e}")
        print(f"  Using default risk score of 50 (Moderate)")
        return 50.0


def load_model_predictions(output_dir: str, model_type: str) -> dict:
    """Load model and generate predictions for all stocks."""
    model_path = Path(output_dir) / 'model_1y.pkl'
    scaler_path = Path(output_dir) / 'imputer_scaler.pkl'

    if not model_path.exists() or not scaler_path.exists():
        print(f"  WARNING: Model or scaler not found in {output_dir}")
        return {}

    try:
        # Load model (saved as dict with 'model', 'feature_names', etc.)
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data['model']
        feature_cols = model_data['feature_names']

        # Load feature names from scaler (saved as numpy array of feature names)
        with open(scaler_path, 'rb') as f:
            scaler_feature_names = pickle.load(f)
        if isinstance(scaler_feature_names, np.ndarray):
            scaler_feature_names = scaler_feature_names.tolist()

        # Load preprocessed data
        if model_type == 'fundamental':
            preprocessed_path = Path(output_dir).parent / 'output' / 'preprocessed_data.csv'
        else:
            # Technical model needs preprocessed data with sector z-scores
            preprocessed_path = Path(output_dir) / 'technical_features_preprocessed.csv'
            if not preprocessed_path.exists():
                # Fall back to raw features and compute z-scores
                preprocessed_path = Path(output_dir) / 'technical_features.csv'

        if not preprocessed_path.exists():
            print(f"  WARNING: Data not found at {preprocessed_path}")
            return {}

        df = pd.read_csv(preprocessed_path)
        print(f"  Loaded {model_type} data: {len(df)} rows, {len(feature_cols)} features")

        # Prepare features: clip inf, fill NaN with median
        X = df[feature_cols].copy()
        X = X.replace([np.inf, -np.inf], np.nan)
        for col in X.columns:
            median_val = X[col].median()
            X[col] = X[col].fillna(median_val)

        # Generate predictions
        preds = model.predict(X)

        scores = {}
        for i, ticker in enumerate(df['ticker'].values):
            scores[ticker] = float(preds[i])

        print(f"  Generated {len(scores)} {model_type} predictions")
        return scores

    except Exception as e:
        print(f"  WARNING: Could not generate {model_type} predictions: {e}")
        import traceback
        traceback.print_exc()
        return {}


def run_portfolio_generation(
    fundamental_df: pd.DataFrame,
    technical_df: pd.DataFrame,
    daily_prices: pd.DataFrame,
    spy_daily: pd.DataFrame,
    investor_risk_score: float,
    capital: float = 100_000,
    output_dir: str = 'output_composite',
    script_dir: Path = None,
) -> dict:
    """
    Full pipeline: score stocks → compute risk → build portfolio.

    Parameters
    ----------
    fundamental_df : pd.DataFrame
        Preprocessed fundamental data with predictions
    technical_df : pd.DataFrame
        Preprocessed technical data with predictions
    daily_prices : pd.DataFrame
        Daily OHLCV data (for stock risk computation)
    spy_daily : pd.DataFrame
        SPY daily data
    investor_risk_score : float
        Investor risk score 0-100
    capital : float
        Investment capital
    output_dir : str
        Output directory

    Returns
    -------
    dict
        Portfolio results
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Step 1: Generate predictions from trained models
    print("\n" + "=" * 60)
    print("STEP 1: GENERATING MODEL PREDICTIONS")
    print("=" * 60)

    # Load fundamental model predictions
    fund_scores = load_model_predictions(str(script_dir / 'output'), 'fundamental')

    # Load technical model predictions
    tech_scores = load_model_predictions(str(script_dir / 'output_technical'), 'technical')

    if not fund_scores and not tech_scores:
        print("  ERROR: No predictions generated. Cannot proceed.")
        return {}

    # Step 2: Compute composite scores
    print("\n" + "=" * 60)
    print("STEP 2: COMPUTING COMPOSITE SCORES")
    print("=" * 60)

    composite_df = compute_composite_scores(fund_scores, tech_scores)

    # Step 2: Compute stock risk scores
    print("\n" + "=" * 60)
    print("STEP 2: COMPUTING STOCK RISK SCORES")
    print("=" * 60)

    stock_risk_df = compute_stock_risk_scores(daily_prices, spy_daily, fundamental_df)

    # Step 3: Build portfolio
    print("\n" + "=" * 60)
    print("STEP 3: BUILDING RISK-MATCHED PORTFOLIO")
    print("=" * 60)

    portfolio = build_portfolio(composite_df, stock_risk_df, investor_risk_score, capital)
    print_portfolio_report(portfolio, capital)

    # Save results
    with open(output_path / 'portfolio.json', 'w') as f:
        json.dump(portfolio, f, indent=2)
    composite_df.to_csv(output_path / 'composite_scores.csv', index=False)
    stock_risk_df.to_csv(output_path / 'stock_risk_scores.csv', index=False)

    print(f"\n  Results saved to {output_path}/")

    return portfolio


def run_backtest(
    fundamental_df: pd.DataFrame,
    technical_df: pd.DataFrame,
    daily_prices: pd.DataFrame,
    spy_daily: pd.DataFrame,
    output_dir: str = 'output_composite',
):
    """Run backtest for all risk buckets."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Compute stock risk scores
    print("\n" + "=" * 60)
    print("COMPUTING STOCK RISK SCORES FOR BACKTEST")
    print("=" * 60)
    stock_risk_df = compute_stock_risk_scores(daily_prices, spy_daily, fundamental_df)

    # For backtest, we'd need historical composite scores and actual returns
    # This is a placeholder — in production, you'd load historical data
    print("\n  Backtest requires historical data (multiple quarters of scores + actual returns)")
    print("  This feature will be fully implemented when historical data pipeline is ready.")

    return {}


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Composite Model Pipeline')
    parser.add_argument('--profile', type=str, default='moderate',
                       choices=list(INVESTOR_PROFILES.keys()),
                       help='Investor risk profile')
    parser.add_argument('--risk-score', type=float, default=None,
                       help='Custom investor risk score (overrides profile)')
    parser.add_argument('--capital', type=float, default=100_000,
                       help='Investment capital (default: $100,000)')
    parser.add_argument('--output', type=str, default='output_composite',
                       help='Output directory')
    parser.add_argument('--backtest', action='store_true',
                       help='Run backtest for all risk buckets')
    parser.add_argument('--compare', action='store_true',
                       help='Compare portfolios across profiles')
    parser.add_argument('--risk-model', type=str,
                       default='risk prediction/risk_tolerance_model.pkl',
                       help='Path to trained risk prediction model')

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_dir = script_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n  Script directory: {script_dir}")

    # Load data
    print("\n" + "=" * 60)
    print("LOADING DATA")
    print("=" * 60)

    # Load daily prices
    daily_prices_path = script_dir / 'daily_prices_all.csv'
    if daily_prices_path.exists():
        daily_prices = pd.read_csv(daily_prices_path, parse_dates=['date'])
        spy_daily = daily_prices[daily_prices['ticker'] == 'SPY'].copy()
        daily_prices = daily_prices[daily_prices['ticker'] != 'SPY']
        print(f"  Daily prices: {len(daily_prices)} rows, {daily_prices['ticker'].nunique()} tickers")
    else:
        print("  ERROR: daily_prices_all.csv not found. Run technical model fetch first.")
        return

    # Load preprocessed fundamental data (has targets and sector info)
    fund_preprocessed_path = script_dir / 'output' / 'preprocessed_data.csv'
    if fund_preprocessed_path.exists():
        fundamental_df = pd.read_csv(fund_preprocessed_path)
        print(f"  Fundamental data: {len(fundamental_df)} rows")
    else:
        fundamental_df = pd.read_csv(script_dir / 'sp500_fundamental_dataset.csv')
        print(f"  Fundamental data (raw): {len(fundamental_df)} rows")

    # Load technical features and preprocess
    tech_features_path = script_dir / 'output_technical' / 'technical_features.csv'
    if tech_features_path.exists():
        technical_df = pd.read_csv(tech_features_path)
        # Preprocess to add sector z-scores
        from sp500_technical.preprocessing import compute_sector_zscores, clip_outliers
        technical_df = clip_outliers(technical_df)
        technical_df = compute_sector_zscores(technical_df)
        # Save preprocessed version
        tech_preprocessed_path = script_dir / 'output_technical' / 'technical_features_preprocessed.csv'
        technical_df.to_csv(tech_preprocessed_path, index=False)
        print(f"  Technical features (preprocessed): {len(technical_df)} rows")
    else:
        technical_df = pd.DataFrame()
        print("  Technical features: not found")

    # Determine investor risk score
    if args.risk_score is not None:
        investor_risk_score = args.risk_score
        print(f"\n  Using custom risk score: {investor_risk_score:.1f}")
    else:
        risk_model_path = script_dir / args.risk_model
        if risk_model_path.exists():
            investor_risk_score = predict_investor_risk(args.profile, str(risk_model_path))
        else:
            print(f"\n  Risk model not found at {risk_model_path}")
            investor_risk_score = 50.0
            print(f"  Using default risk score: {investor_risk_score:.1f} (Moderate)")

    if args.compare:
        # Compare multiple profiles — compute scores once, then build portfolios
        print("\n" + "=" * 60)
        print("GENERATING MODEL PREDICTIONS")
        print("=" * 60)
        fund_scores = load_model_predictions(str(script_dir / 'output'), 'fundamental')
        tech_scores = load_model_predictions(str(script_dir / 'output_technical'), 'technical')
        composite_df = compute_composite_scores(fund_scores, tech_scores)
        stock_risk_df = compute_stock_risk_scores(daily_prices, spy_daily, fundamental_df)

        profiles = ['conservative', 'moderate', 'aggressive']
        for profile_key in profiles:
            if risk_model_path.exists():
                rs = predict_investor_risk(profile_key, str(risk_model_path))
            else:
                rs = {'conservative': 25, 'moderate': 50, 'aggressive': 75}.get(profile_key, 50)

            print(f"\n{'=' * 60}")
            print(f"PROFILE: {profile_key.upper()} (Risk Score: {rs:.1f})")
            print(f"{'=' * 60}")

            portfolio = build_portfolio(composite_df, stock_risk_df, rs, args.capital)
            print_portfolio_report(portfolio, args.capital)

    elif args.backtest:
        run_backtest(fundamental_df, technical_df, daily_prices, spy_daily, str(output_dir))

    else:
        # Single portfolio generation
        run_portfolio_generation(
            fundamental_df, technical_df, daily_prices, spy_daily,
            investor_risk_score, args.capital, str(output_dir), script_dir
        )


if __name__ == '__main__':
    main()
