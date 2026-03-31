"""
Train/validation/test splitting with time-based boundaries.
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict
from sklearn.model_selection import TimeSeriesSplit
from scipy import stats as scipy_stats
from .config import TIME_SPLIT
from .imputation import ImputerScaler


def train_val_test_split(
    df: pd.DataFrame,
    train_end_year: int = None,
    val_start_year: int = None,
    val_end_year: int = None,
    test_start_year: int = None
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Split data into train, validation, and test sets based on time.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed data with 'year' column
    train_end_year : int, optional
        Last year of training period (default from config: 2019)
    val_start_year : int, optional
        First year of validation period (default from config: 2020)
    val_end_year : int, optional
        Last year of validation period (default from config: 2021)
    test_start_year : int, optional
        First year of test period (default from config: 2022)

    Returns
    -------
    Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]
        train_df, val_df, test_df
    """
    # Use config defaults if not specified
    train_end_year = train_end_year or TIME_SPLIT['train_end_year']
    val_start_year = val_start_year or TIME_SPLIT['val_start_year']
    val_end_year = val_end_year or TIME_SPLIT['val_end_year']
    test_start_year = test_start_year or TIME_SPLIT['test_start_year']

    # Ensure year column exists
    if 'year' not in df.columns:
        raise ValueError("DataFrame must have 'year' column for time-based splitting")

    # Split
    train_mask = df['year'] <= train_end_year
    val_mask = (df['year'] >= val_start_year) & (df['year'] <= val_end_year)
    test_mask = df['year'] >= test_start_year

    train_df = df[train_mask].copy()
    val_df = df[val_mask].copy()
    test_df = df[test_mask].copy()

    print(f"\nTime-based split:")
    print(f"  Train: year <= {train_end_year} -> {len(train_df)} rows, {train_df['ticker'].nunique()} companies")
    print(f"  Val: {val_start_year} <= year <= {val_end_year} -> {len(val_df)} rows, {val_df['ticker'].nunique()} companies")
    print(f"  Test: year >= {test_start_year} -> {len(test_df)} rows, {test_df['ticker'].nunique()} companies")

    return train_df, val_df, test_df


def filter_rows_with_target(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Filter out rows where target is NaN.

    Parameters
    ----------
    train_df, val_df, test_df : pd.DataFrame
        Split data
    target_col : str
        Target column name

    Returns
    -------
    Tuple of filtered DataFrames
    """
    train_filtered = train_df.dropna(subset=[target_col])
    val_filtered = val_df.dropna(subset=[target_col])
    test_filtered = test_df.dropna(subset=[target_col])

    print(f"\nFiltered for target '{target_col}':")
    print(f"  Train: {len(train_filtered)}/{len(train_df)} rows with valid target")
    print(f"  Val: {len(val_filtered)}/{len(val_df)} rows with valid target")
    print(f"  Test: {len(test_filtered)}/{len(test_df)} rows with valid target")

    return train_filtered, val_filtered, test_filtered


def get_split_stats(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    target_col: str
) -> dict:
    """
    Get statistics for each split.

    Returns
    -------
    dict
        Statistics including row counts, company counts, target statistics
    """
    stats = {
        'train': {
            'n_rows': len(train_df),
            'n_companies': train_df['ticker'].nunique(),
            'year_range': (train_df['year'].min(), train_df['year'].max()),
            'target_mean': train_df[target_col].mean(),
            'target_std': train_df[target_col].std(),
        },
        'val': {
            'n_rows': len(val_df),
            'n_companies': val_df['ticker'].nunique(),
            'year_range': (val_df['year'].min(), val_df['year'].max()),
            'target_mean': val_df[target_col].mean(),
            'target_std': val_df[target_col].std(),
        },
        'test': {
            'n_rows': len(test_df),
            'n_companies': test_df['ticker'].nunique(),
            'year_range': (test_df['year'].min(), test_df['year'].max()),
            'target_mean': test_df[target_col].mean(),
            'target_std': test_df[target_col].std(),
        },
    }

    return stats


def walk_forward_cv(
    df: pd.DataFrame,
    feature_cols: List[str],
    train_target_col: str,
    eval_target_col: str,
    n_splits: int = 5,
    gap: int = 4,
    tune: bool = False,
    n_trials: int = 30,
    n_top_features: int = 40,
) -> List[Dict]:
    """
    Walk-forward cross-validation with purged gap.

    Uses expanding training window with a gap between train and validation
    to avoid lookahead bias. Each fold trains on all data up to year T,
    validates on year T+gap+1 to T+gap+val_years.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed data with 'year' column
    feature_cols : List[str]
        Feature columns to use
    train_target_col : str
        Target column for training (e.g., excess_return_1y_rank)
    eval_target_col : str
        Target column for evaluation (e.g., excess_return_1y)
    n_splits : int
        Number of walk-forward splits
    gap : int
        Number of quarters to skip between train and val (avoid lookahead)
    tune : bool
        Whether to tune hyperparameters
    n_trials : int
        Number of Optuna trials per fold
    n_top_features : int
        Number of top features to keep after pruning

    Returns
    -------
    List[Dict]
        List of fold results with metrics
    """
    from .model_lgbm import LightGBMModel

    years = sorted(df['year'].unique())
    min_train_years = 4

    # Calculate split points based on available years
    n_years = len(years)
    val_years_per_fold = max(1, (n_years - min_train_years - gap) // n_splits)

    fold_results = []

    print(f"\nWalk-forward CV: {n_splits} folds, gap={gap} quarters")
    print(f"Available years: {years[0]}-{years[-1]} ({n_years} years)")
    print(f"Val years per fold: ~{val_years_per_fold}")

    for fold in range(n_splits):
        # Calculate train/val/test year boundaries for this fold
        val_start_idx = min_train_years + fold * val_years_per_fold
        val_end_idx = min(val_start_idx + val_years_per_fold, n_years - 1)
        test_start_idx = val_end_idx + 1

        if val_start_idx >= n_years - 1:
            print(f"\nFold {fold+1}: Not enough data remaining, skipping.")
            break

        train_years = years[:val_start_idx]
        val_years = years[val_start_idx:val_end_idx + 1]
        test_years = years[test_start_idx:] if test_start_idx < n_years else []

        print(f"\n{'='*50}")
        print(f"Fold {fold+1}:")
        print(f"  Train years: {train_years[0]}-{train_years[-1]}")
        print(f"  Val years:   {val_years[0]}-{val_years[-1]}")
        if test_years:
            print(f"  Test years:  {test_years[0]}-{test_years[-1]}")
        else:
            print(f"  Test years:  N/A (last fold)")

        # Split data
        fold_train = df[df['year'].isin(train_years)].copy()
        fold_val = df[df['year'].isin(val_years)].copy()
        fold_test = df[df['year'].isin(test_years)].copy() if test_years else None

        # Filter for valid targets
        fold_train = fold_train.dropna(subset=[eval_target_col])
        fold_val = fold_val.dropna(subset=[eval_target_col])

        if len(fold_train) < 100 or len(fold_val) < 30:
            print(f"  Skipping fold: too few samples (train={len(fold_train)}, val={len(fold_val)})")
            continue

        # Simple median imputation + no scaling for speed
        X_train = fold_train[feature_cols].copy()
        X_val = fold_val[feature_cols].copy()
        y_train = fold_train[train_target_col]
        y_val = fold_val[train_target_col]

        # Replace inf with nan, then median impute
        X_train = X_train.replace([np.inf, -np.inf], np.nan)
        X_val = X_val.replace([np.inf, -np.inf], np.nan)

        medians = X_train.median()
        X_train = X_train.fillna(medians)
        X_val = X_val.fillna(medians)

        # Quick model (no tuning, no feature pruning for speed)
        model = LightGBMModel(target_col='excess_return_1y')
        model.fit(X_train, y_train, X_val=X_val, y_val=y_val, tune=False)

        # Evaluate on validation set
        pred_val = model.predict(X_val)
        val_ic, val_ic_p = scipy_stats.pearsonr(pred_val, y_val.values)
        val_spearman, _ = scipy_stats.spearmanr(pred_val, y_val.values)

        # Get feature count with nonzero importance
        importance_df = model.get_feature_importance()
        n_features = len(importance_df[importance_df['importance'] > 0])

        # Evaluate on test set if available
        test_ic = None
        test_spearman = None
        if fold_test is not None and len(fold_test) > 0:
            fold_test = fold_test.dropna(subset=[eval_target_col])
            if len(fold_test) > 0:
                X_test = fold_test[feature_cols].copy()
                X_test = X_test.replace([np.inf, -np.inf], np.nan)
                X_test = X_test.fillna(medians)
                y_test = fold_test[eval_target_col]

                pred_test = model.predict(X_test)
                test_ic, test_ic_p = scipy_stats.pearsonr(pred_test, y_test.values)
                test_spearman, _ = scipy_stats.spearmanr(pred_test, y_test.values)

        fold_result = {
            'fold': fold + 1,
            'train_years': f"{train_years[0]}-{train_years[-1]}",
            'val_years': f"{val_years[0]}-{val_years[-1]}",
            'test_years': f"{test_years[0]}-{test_years[-1]}" if test_years else "N/A",
            'n_train': len(fold_train),
            'n_val': len(fold_val),
            'n_test': len(fold_test) if fold_test is not None else 0,
            'n_features': n_features,
            'val_ic': float(val_ic),
            'val_ic_p': float(val_ic_p),
            'val_spearman': float(val_spearman),
            'test_ic': float(test_ic) if test_ic is not None else None,
            'test_ic_p': float(test_ic_p) if test_ic is not None else None,
            'test_spearman': float(test_spearman) if test_spearman is not None else None,
        }
        fold_results.append(fold_result)

        print(f"  Val IC: {val_ic:.4f} (p={val_ic_p:.4f}), Spearman: {val_spearman:.4f}")
        if test_ic is not None:
            print(f"  Test IC: {test_ic:.4f} (p={test_ic_p:.4f}), Spearman: {test_spearman:.4f}")

    return fold_results