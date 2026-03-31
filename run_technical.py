#!/usr/bin/env python
"""
SP500 Technical Model Pipeline Entry Point

Usage:
    python run_technical.py --step fetch          # Download daily OHLCV
    python run_technical.py --step train          # Compute features, train, evaluate
    python run_technical.py                       # All steps
    python run_technical.py --step train --walk-forward  # Walk-forward CV
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

from sp500_technical.config import CACHE_DIR, TIME_SPLIT
from sp500_technical.data_fetcher import (
    fetch_all_tickers, load_cached_tickers,
)
from sp500_technical.features import compute_all_features_vectorized
from sp500_technical.preprocessing import preprocess_technical_data, get_feature_columns

from sp500_ml.utils import (
    load_data, save_data, save_metrics, print_data_summary,
    check_target_leakage,
)
from sp500_ml.features import print_feature_summary
from sp500_ml.splitting import (
    train_val_test_split, filter_rows_with_target, get_split_stats,
    walk_forward_cv,
)
from sp500_ml.imputation import impute_and_scale
from sp500_ml.model_lgbm import LightGBMModel
from sp500_ml.evaluation import (
    evaluate_model, evaluate_top_bottom_decile,
)


def run_fetch(
    data_path: str,
    cache_dir: str = CACHE_DIR,
    force: bool = False,
) -> dict:
    """
    Step 1: Download daily OHLCV from Yahoo Finance.
    """
    print("\n" + "=" * 60)
    print("STEP 1: FETCHING DAILY PRICE DATA")
    print("=" * 60)

    # Get ticker list from fundamental dataset
    fund_df = pd.read_csv(data_path)
    ticker_list = sorted(fund_df['ticker'].unique())
    print(f"Tickers from fundamental dataset: {len(ticker_list)}")

    # Download
    daily_data = fetch_all_tickers(ticker_list, cache_dir, force=force)

    # Also fetch SPY
    print("\nFetching SPY data...")
    spy_data = fetch_all_tickers(['SPY'], cache_dir, force=force)

    print(f"\nTotal tickers cached: {len(daily_data) + len(spy_data)}")

    return {
        'daily_data': daily_data,
        'spy_daily': spy_data.get('SPY'),
        'ticker_list': ticker_list,
    }


def run_train(
    data_path: str,
    output_dir: str,
    cache_dir: str = CACHE_DIR,
    target_col: str = 'excess_return_1y',
    use_rank_target: bool = True,
    tune_hyperparams: bool = False,
    n_trials: int = 30,
    n_top_features: int = 40,
) -> dict:
    """
    Steps 2-3: Feature computation, preprocessing, and model training.

    Two-pass approach:
    - Pass 1: Train on all features to get importance scores
    - Keep top N features by gain importance
    - Pass 2: Retrain on pruned features
    """
    print("\n" + "=" * 60)
    print("STEP 2-3: TECHNICAL FEATURES & MODEL TRAINING")
    print("=" * 60)

    # Load fundamental data (for targets and sector mapping)
    # Use preprocessed data which has rank-normalized targets
    preprocessed_path = Path(data_path).parent / 'output' / 'preprocessed_data.csv'
    if preprocessed_path.exists():
        fund_df = pd.read_csv(preprocessed_path)
        print(f"Loaded preprocessed fundamental data: {len(fund_df)} rows")
    else:
        fund_df = pd.read_csv(data_path)
        print(f"WARNING: Preprocessed data not found. Using raw fundamental data.")

    # Load cached daily data from combined CSV
    combined_path = Path(__file__).parent / 'daily_prices_all.csv'
    if not combined_path.exists():
        print("ERROR: daily_prices_all.csv not found. Run --step fetch first.")
        return {}

    print(f"\nLoading daily data from {combined_path}...")
    all_daily = pd.read_csv(combined_path, parse_dates=['date'])
    print(f"  Loaded {len(all_daily)} rows, {all_daily['ticker'].nunique()} tickers")
    print(f"  Date range: {all_daily['date'].min()} to {all_daily['date'].max()}")

    # Split into dict by ticker
    daily_data = {}
    for ticker, grp in all_daily.groupby('ticker'):
        daily_data[ticker] = grp.sort_values('date').reset_index(drop=True)

    # Load SPY
    spy_daily = daily_data.get('SPY')
    if spy_daily is None:
        print("ERROR: SPY data not found in daily_prices_all.csv")
        return {}

    ticker_list = sorted([t for t in daily_data.keys() if t != 'SPY'])

    # Get sector mapping
    sector_map = fund_df[['ticker', 'sector']].drop_duplicates()
    sector_map = dict(zip(sector_map['ticker'], sector_map['sector']))

    # Get quarter-end dates from fundamental data
    quarter_dates = pd.to_datetime(fund_df['quarter_end'].unique()).sort_values()

    # Compute technical features
    print("\n" + "-" * 40)
    print("Computing technical features...")
    print("-" * 40)
    tech_df = compute_all_features_vectorized(
        daily_data, spy_daily, quarter_dates, sector_map
    )

    # Save raw technical features
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    tech_df.to_csv(output_path / 'technical_features.csv', index=False)
    print(f"Saved technical features to {output_path / 'technical_features.csv'}")

    # Preprocess
    processed_df = preprocess_technical_data(tech_df, fund_df)

    # Determine training target
    rank_target_col = f'{target_col}_rank'
    if use_rank_target and rank_target_col in processed_df.columns:
        train_target_col = rank_target_col
        print(f"\nUsing rank-normalized target: {train_target_col}")
    else:
        train_target_col = target_col
        print(f"\nUsing raw target: {train_target_col}")

    # Get feature columns
    feature_cols = get_feature_columns(processed_df)
    print(f"\nTotal technical features: {len(feature_cols)}")

    # Check for target leakage
    leakage_issues = check_target_leakage(processed_df, feature_cols, target_col)
    if leakage_issues:
        print("\nWARNING: Potential target leakage detected:")
        for issue in leakage_issues:
            print(f"  - {issue}")

    # Split data
    train_df, val_df, test_df = train_val_test_split(processed_df)
    train_df, val_df, test_df = filter_rows_with_target(train_df, val_df, test_df, target_col)
    stats = get_split_stats(train_df, val_df, test_df, target_col)

    # ===== PASS 1: Feature pruning =====
    print("\n--- PASS 1: Feature pruning ---")
    print("Imputing missing values and scaling features (all features)...")
    train_transformed, val_transformed, test_transformed, imputer_scaler = impute_and_scale(
        train_df, val_df, test_df, feature_cols
    )

    X_train = train_transformed[feature_cols]
    y_train = train_transformed[train_target_col]
    X_val = val_transformed[feature_cols]
    y_val = val_transformed[train_target_col]
    X_test = test_transformed[feature_cols]
    y_test = test_transformed[target_col]

    print(f"\nTraining features shape (all): {X_train.shape}")

    print("\nTraining Pass 1 model (all features, no tuning)...")
    model_pass1 = LightGBMModel(target_col='excess_return_1y')
    model_pass1.fit(X_train, y_train, X_val=X_val, y_val=y_val, tune=False)

    importance_df = model_pass1.get_feature_importance(importance_type='gain')
    print(f"\nPass 1 Feature Importance (top 20):")
    print(importance_df.head(20).to_string())

    nonzero_features = importance_df[importance_df['importance'] > 0]['feature'].tolist()
    pruned_features = importance_df.head(n_top_features)['feature'].tolist()
    pruned_features = [f for f in pruned_features if f in nonzero_features]

    if len(pruned_features) < 15:
        print(f"\nOnly {len(pruned_features)} features with nonzero importance in top {n_top_features}.")
        print("Expanding to all features with nonzero importance...")
        pruned_features = nonzero_features[:n_top_features]

    print(f"\nFeature pruning: {len(feature_cols)} -> {len(pruned_features)} features")
    print(f"Pruned features: {pruned_features[:10]}...")

    importance_df.to_csv(output_path / 'feature_importance_pass1.csv', index=False)

    # ===== PASS 2: Final training =====
    print("\n--- PASS 2: Final training with pruned features ---")
    print("Re-imputing missing values and scaling features (pruned)...")
    train_transformed2, val_transformed2, test_transformed2, imputer_scaler2 = impute_and_scale(
        train_df, val_df, test_df, pruned_features
    )

    imputer_scaler2.save(str(output_path / 'imputer_scaler.pkl'))

    X_train2 = train_transformed2[pruned_features]
    y_train2 = train_transformed2[train_target_col]
    X_val2 = val_transformed2[pruned_features]
    y_val2 = val_transformed2[train_target_col]
    X_test2 = test_transformed2[pruned_features]
    y_test2 = test_transformed2[target_col]
    y_test_rank = test_transformed2[train_target_col]
    y_test_raw = test_transformed2[target_col]

    print(f"\nTraining features shape (pruned): {X_train2.shape}")

    print("\n" + "-" * 40)
    print("Training 1-year excess return model (pruned features)...")
    print("-" * 40)
    model_1y = LightGBMModel(target_col='excess_return_1y')
    model_1y.fit(
        X_train2, y_train2,
        X_val=X_val2, y_val=y_val2,
        tune=tune_hyperparams,
        n_trials=n_trials
    )
    model_1y.save(str(output_path / 'model_1y.pkl'))

    # Predictions
    print("\nMaking predictions...")
    pred_1y_train = model_1y.predict(X_train2)
    pred_1y_val = model_1y.predict(X_val2)
    pred_1y_test = model_1y.predict(X_test2)

    # Evaluate
    print("\n" + "=" * 60)
    print("MODEL EVALUATION")
    print("=" * 60)

    print("\n--- Training Set ---")
    train_metrics = evaluate_model(y_train2.values, pred_1y_train, "Train (1y)")

    print("\n--- Validation Set ---")
    val_metrics = evaluate_model(y_val2.values, pred_1y_val, "Validation (1y)")

    print("\n--- Test Set (Rank Target - Scale Consistent) ---")
    test_metrics = evaluate_model(y_test_rank.values, pred_1y_test, "Test (1y)")

    print("\n--- Test Set (Raw Returns - Signal Strength) ---")
    test_raw_metrics = evaluate_model(y_test_raw.values, pred_1y_test, "Test (1y) Raw")

    # Decile analysis
    test_with_pred = test_df.copy()
    test_with_pred['pred_excess_return'] = pred_1y_test
    decile_results = evaluate_top_bottom_decile(
        test_with_pred, 'pred_excess_return', target_col
    )

    # Feature importance
    print("\n" + "-" * 40)
    print("Top 20 Feature Importance (1y model, pruned):")
    print("-" * 40)
    final_importance_df = model_1y.get_feature_importance()
    print(final_importance_df.head(20).to_string())

    final_importance_df.to_csv(output_path / 'feature_importance.csv', index=False)

    metrics = {
        'train': train_metrics,
        'val': val_metrics,
        'test': test_metrics,
        'test_raw': test_raw_metrics,
        'decile': decile_results,
        'split_stats': stats,
        'n_features_pruned': len(pruned_features),
        'pruned_features': pruned_features,
    }
    save_metrics(metrics, str(output_path / 'model_metrics.json'))

    return {
        'model_1y': model_1y,
        'imputer_scaler': imputer_scaler2,
        'feature_cols': pruned_features,
        'train_df': train_transformed2,
        'val_df': val_transformed2,
        'test_df': test_transformed2,
        'pred_1y_test': pred_1y_test,
        'pred_1y_val': pred_1y_val,
        'pred_1y_train': pred_1y_train,
    }


def run_walk_forward_train(
    data_path: str,
    output_dir: str,
    cache_dir: str = CACHE_DIR,
    target_col: str = 'excess_return_1y',
    use_rank_target: bool = True,
    tune_hyperparams: bool = False,
    n_trials: int = 30,
    n_splits: int = 5,
    n_top_features: int = 40,
) -> dict:
    """
    Walk-forward cross-validation training.
    """
    print("\n" + "=" * 60)
    print("WALK-FORWARD CROSS-VALIDATION")
    print("=" * 60)

    # Load fundamental data (for targets and sector mapping)
    # Use preprocessed data which has rank-normalized targets
    preprocessed_path = Path(data_path).parent / 'output' / 'preprocessed_data.csv'
    if preprocessed_path.exists():
        fund_df = pd.read_csv(preprocessed_path)
        print(f"Loaded preprocessed fundamental data: {len(fund_df)} rows")
    else:
        fund_df = pd.read_csv(data_path)
        print(f"WARNING: Preprocessed data not found. Using raw fundamental data.")

    # Load cached daily data from combined CSV
    combined_path = Path(__file__).parent / 'daily_prices_all.csv'
    if not combined_path.exists():
        print("ERROR: daily_prices_all.csv not found. Run --step fetch first.")
        return {}

    print(f"\nLoading daily data from {combined_path}...")
    all_daily = pd.read_csv(combined_path, parse_dates=['date'])
    print(f"  Loaded {len(all_daily)} rows, {all_daily['ticker'].nunique()} tickers")
    print(f"  Date range: {all_daily['date'].min()} to {all_daily['date'].max()}")

    # Split into dict by ticker
    daily_data = {}
    for ticker, grp in all_daily.groupby('ticker'):
        daily_data[ticker] = grp.sort_values('date').reset_index(drop=True)

    # Load SPY
    spy_daily = daily_data.get('SPY')
    if spy_daily is None:
        print("ERROR: SPY data not found in daily_prices_all.csv")
        return {}

    ticker_list = sorted([t for t in daily_data.keys() if t != 'SPY'])

    sector_map = fund_df[['ticker', 'sector']].drop_duplicates()
    sector_map = dict(zip(sector_map['ticker'], sector_map['sector']))
    quarter_dates = pd.to_datetime(fund_df['quarter_end'].unique()).sort_values()

    tech_df = compute_all_features_vectorized(
        daily_data, spy_daily, quarter_dates, sector_map
    )
    processed_df = preprocess_technical_data(tech_df, fund_df)

    rank_target_col = f'{target_col}_rank'
    train_target_col = rank_target_col if (use_rank_target and rank_target_col in processed_df.columns) else target_col

    feature_cols = get_feature_columns(processed_df)

    fold_results = walk_forward_cv(
        processed_df, feature_cols, train_target_col, target_col,
        n_splits=n_splits, gap=4,
        tune=tune_hyperparams, n_trials=n_trials,
        n_top_features=n_top_features,
    )

    fold_ics = [r['val_ic'] for r in fold_results]
    fold_test_ics = [r['test_ic'] for r in fold_results]

    print("\n" + "=" * 60)
    print("WALK-FORWARD RESULTS")
    print("=" * 60)
    print(f"\nValidation IC: {np.mean(fold_ics):.4f} ± {np.std(fold_ics):.4f}")
    print(f"Test IC:       {np.mean(fold_test_ics):.4f} ± {np.std(fold_test_ics):.4f}")

    for i, r in enumerate(fold_results):
        print(f"  Fold {i+1}: Val IC={r['val_ic']:.4f}, Test IC={r['test_ic']:.4f}, Features={r['n_features']}")

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    wf_metrics = {
        'fold_results': fold_results,
        'mean_val_ic': float(np.mean(fold_ics)),
        'std_val_ic': float(np.std(fold_ics)),
        'mean_test_ic': float(np.mean(fold_test_ics)),
        'std_test_ic': float(np.std(fold_test_ics)),
        'n_splits': n_splits,
    }
    save_metrics(wf_metrics, str(output_path / 'walk_forward_metrics.json'))

    # Train final model
    print("\n" + "=" * 60)
    print("TRAINING FINAL MODEL ON ALL NON-TEST DATA")
    print("=" * 60)

    return run_train(data_path, output_dir, cache_dir, target_col, use_rank_target, tune_hyperparams, n_trials, n_top_features)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='SP500 Technical Model Pipeline')
    parser.add_argument('--step', type=str, choices=['fetch', 'train'],
                       help='Run specific step (default: all steps)')
    parser.add_argument('--data', type=str,
                       default='sp500_fundamental_dataset.csv',
                       help='Path to fundamental dataset (for ticker list and targets)')
    parser.add_argument('--cache', type=str, default=CACHE_DIR,
                       help=f'Cache directory for daily data (default: {CACHE_DIR})')
    parser.add_argument('--output', type=str, default='output_technical',
                       help='Output directory (default: output_technical)')
    parser.add_argument('--target', type=str, default='excess_return_1y',
                       help='Target column (default: excess_return_1y)')
    parser.add_argument('--tune', action='store_true',
                       help='Tune hyperparameters with Optuna')
    parser.add_argument('--n-trials', type=int, default=30,
                       help='Number of Optuna trials (default: 30)')
    parser.add_argument('--walk-forward', action='store_true',
                       help='Use walk-forward cross-validation')
    parser.add_argument('--n-splits', type=int, default=5,
                       help='Number of walk-forward splits (default: 5)')
    parser.add_argument('--force-fetch', action='store_true',
                       help='Re-download daily data even if cached')

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    data_path = script_dir / args.data
    output_dir = script_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Data path: {data_path}")
    print(f"Cache directory: {args.cache}")
    print(f"Output directory: {output_dir}")

    if args.step == 'fetch':
        run_fetch(str(data_path), args.cache, args.force_fetch)

    elif args.step == 'train':
        if args.walk_forward:
            run_walk_forward_train(
                str(data_path), str(output_dir), args.cache,
                args.target, True, args.tune, args.n_trials, args.n_splits
            )
        else:
            run_train(
                str(data_path), str(output_dir), args.cache,
                args.target, True, args.tune, args.n_trials
            )

    else:
        # Run all steps
        print("\n" + "=" * 60)
        print("SP500 TECHNICAL MODEL PIPELINE - FULL RUN")
        print("=" * 60)

        run_fetch(str(data_path), args.cache, args.force_fetch)

        if args.walk_forward:
            run_walk_forward_train(
                str(data_path), str(output_dir), args.cache,
                args.target, True, args.tune, args.n_trials, args.n_splits
            )
        else:
            run_train(
                str(data_path), str(output_dir), args.cache,
                args.target, True, args.tune, args.n_trials
            )

        print("\n" + "=" * 60)
        print("PIPELINE COMPLETE")
        print("=" * 60)
        print(f"\nResults saved to: {output_dir}")


if __name__ == '__main__':
    main()
