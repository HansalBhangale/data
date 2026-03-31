"""
Utility functions for SP500 ML pipeline.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import List, Dict, Optional, Any
import json
from datetime import datetime


def load_data(filepath: str) -> pd.DataFrame:
    """
    Load the SP500 fundamental dataset.

    Parameters
    ----------
    filepath : str
        Path to CSV file

    Returns
    -------
    pd.DataFrame
        Loaded data
    """
    print(f"Loading data from {filepath}...")
    df = pd.read_csv(filepath)
    print(f"  Loaded {len(df)} rows, {len(df.columns)} columns")
    print(f"  Companies: {df['ticker'].nunique()}")
    print(f"  Time range: {df['year'].min()} - {df['year'].max()}")

    return df


def save_data(df: pd.DataFrame, filepath: str) -> None:
    """
    Save DataFrame to file.

    Parameters
    ----------
    df : pd.DataFrame
        Data to save
    filepath : str
        Output path (extension determines format)
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    if path.suffix == '.csv':
        df.to_csv(path, index=False)
    elif path.suffix == '.parquet':
        df.to_parquet(path, index=False)
    else:
        raise ValueError(f"Unsupported format: {path.suffix}")

    print(f"Saved {len(df)} rows to {path}")


def check_target_leakage(df: pd.DataFrame, feature_cols: List[str], target_col: str) -> List[str]:
    """
    Check for potential target leakage in features.

    Parameters
    ----------
    df : pd.DataFrame
        Data to check
    feature_cols : List[str]
        Feature columns
    target_col : str
        Target column

    Returns
    -------
    List[str]
        List of potential leakage issues
    """
    issues = []

    # Check for perfect correlation
    for col in feature_cols:
        if col in df.columns:
            corr = df[col].corr(df[target_col])
            if abs(corr) > 0.9:
                issues.append(f"High correlation ({corr:.3f}) between {col} and {target_col}")

    # Check for forward-looking columns
    forward_keywords = ['fwd', 'forward', 'next', 'future', 'return_1y', 'return_3y']
    for col in feature_cols:
        for kw in forward_keywords:
            if kw in col.lower() and col != target_col:
                issues.append(f"Potential forward-looking column: {col}")

    return issues


def print_data_summary(df: pd.DataFrame, name: str = "Dataset") -> None:
    """
    Print summary statistics for a DataFrame.

    Parameters
    ----------
    df : pd.DataFrame
        Data to summarize
    name : str
        Name for display
    """
    print(f"\n{name} Summary:")
    print(f"  Shape: {df.shape}")
    print(f"  Companies: {df['ticker'].nunique() if 'ticker' in df.columns else 'N/A'}")

    if 'year' in df.columns:
        print(f"  Year range: {df['year'].min()} - {df['year'].max()}")

    if 'quarter' in df.columns:
        print(f"  Quarter distribution:")
        print(df['quarter'].value_counts().sort_index().to_string())

    # Missing values
    missing = df.isnull().sum()
    high_missing = missing[missing > len(df) * 0.5].sort_values(ascending=False)
    if len(high_missing) > 0:
        print(f"\n  Columns with >50% missing:")
        for col, cnt in high_missing.head(10).items():
            print(f"    {col}: {cnt/len(df)*100:.1f}%")


def ensure_directory(path: str) -> Path:
    """
    Ensure directory exists, create if not.

    Parameters
    ----------
    path : str
        Directory path

    Returns
    -------
    Path
        Path object
    """
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def save_metrics(metrics: Dict[str, Any], filepath: str) -> None:
    """
    Save metrics to JSON file.

    Parameters
    ----------
    metrics : Dict
        Metrics dictionary
    filepath : str
        Output path
    """
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Convert numpy types to Python types
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(i) for i in obj]
        return obj

    with open(path, 'w') as f:
        json.dump(convert(metrics), f, indent=2, default=str)

    print(f"Saved metrics to {path}")


def load_metrics(filepath: str) -> Dict[str, Any]:
    """
    Load metrics from JSON file.

    Parameters
    ----------
    filepath : str
        Path to metrics file

    Returns
    -------
    Dict
        Metrics dictionary
    """
    with open(filepath, 'r') as f:
        return json.load(f)


def get_timestamp() -> str:
    """Get current timestamp string."""
    return datetime.now().strftime('%Y%m%d_%H%M%S')


def merge_predictions_with_original(
    df: pd.DataFrame,
    predictions: np.ndarray,
    risk_scores: pd.DataFrame,
    pred_col: str = 'pred_excess_return'
) -> pd.DataFrame:
    """
    Merge predictions and risk scores back with original data.

    Parameters
    ----------
    df : pd.DataFrame
        Original data
    predictions : np.ndarray
        Model predictions
    risk_scores : pd.DataFrame
        Risk scores DataFrame
    pred_col : str
        Name for prediction column

    Returns
    -------
    pd.DataFrame
        Merged DataFrame
    """
    result = df.copy()
    result[pred_col] = predictions
    result['risk_score'] = risk_scores['risk_score'].values

    # Add component scores
    for col in ['leverage_risk', 'liquidity_risk', 'profitability_risk',
                'earnings_volatility', 'valuation_risk', 'model_uncertainty']:
        if col in risk_scores.columns:
            result[col] = risk_scores[col].values

    return result