"""
Imputation and scaling utilities.
KNN imputation + Robust scaling (IQR-based).
"""

import pandas as pd
import numpy as np
from sklearn.impute import KNNImputer
from sklearn.preprocessing import RobustScaler
import joblib
from pathlib import Path
from typing import Tuple, List, Optional


class ImputerScaler:
    """
    Combined KNN imputer and Robust scaler.
    Fit on training data, transform train/val/test.
    """

    def __init__(
        self,
        n_neighbors: int = 5,
        scaler_quantile_range: Tuple[float, float] = (25.0, 75.0)
    ):
        self.n_neighbors = n_neighbors
        self.scaler_quantile_range = scaler_quantile_range

        self.imputer_ = None
        self.scaler_ = None
        self.feature_names_ = None

    def fit(self, X: pd.DataFrame, feature_cols: List[str]) -> 'ImputerScaler':
        """
        Fit imputer and scaler on training data.

        Parameters
        ----------
        X : pd.DataFrame
            Training data
        feature_cols : List[str]
            Columns to use as features

        Returns
        -------
        self
        """
        self.feature_names_ = feature_cols

        # Extract features
        X_features = X[feature_cols].copy()

        # Handle inf values
        X_features = X_features.replace([np.inf, -np.inf], np.nan)

        print(f"Fitting imputer on {len(X_features)} samples, {len(feature_cols)} features...")

        # Fit KNN imputer
        self.imputer_ = KNNImputer(n_neighbors=self.n_neighbors)
        X_imputed = self.imputer_.fit_transform(X_features)

        print(f"Fitting scaler...")

        # Fit Robust scaler
        self.scaler_ = RobustScaler(quantile_range=self.scaler_quantile_range)
        self.scaler_.fit(X_imputed)

        print("Imputer and scaler fitted successfully.")

        return self

    def transform(self, X: pd.DataFrame) -> pd.DataFrame:
        """
        Transform data using fitted imputer and scaler.

        Parameters
        ----------
        X : pd.DataFrame
            Data to transform

        Returns
        -------
        pd.DataFrame
            Transformed data with feature columns
        """
        if self.imputer_ is None or self.scaler_ is None:
            raise ValueError("Must call fit() before transform()")

        # Extract features
        X_features = X[self.feature_names_].copy()

        # Handle inf values
        X_features = X_features.replace([np.inf, -np.inf], np.nan)

        # Transform
        X_imputed = self.imputer_.transform(X_features)
        X_scaled = self.scaler_.transform(X_imputed)

        # Return as DataFrame
        result = pd.DataFrame(X_scaled, columns=self.feature_names_, index=X.index)

        return result

    def fit_transform(self, X: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
        """
        Fit and transform in one step.

        Parameters
        ----------
        X : pd.DataFrame
            Training data
        feature_cols : List[str]
            Columns to use as features

        Returns
        -------
        pd.DataFrame
            Transformed training data
        """
        self.fit(X, feature_cols)
        return self.transform(X)

    def save(self, path: str) -> None:
        """Save imputer and scaler to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'imputer': self.imputer_,
            'scaler': self.scaler_,
            'feature_names': self.feature_names_,
            'n_neighbors': self.n_neighbors,
            'scaler_quantile_range': self.scaler_quantile_range,
        }, path)
        print(f"Saved ImputerScaler to {path}")

    def load(self, path: str) -> 'ImputerScaler':
        """Load imputer and scaler from file."""
        data = joblib.load(path)
        self.imputer_ = data['imputer']
        self.scaler_ = data['scaler']
        self.feature_names_ = data['feature_names']
        self.n_neighbors = data['n_neighbors']
        self.scaler_quantile_range = data['scaler_quantile_range']
        return self


def impute_and_scale(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    test_df: pd.DataFrame,
    feature_cols: List[str],
    n_neighbors: int = 5
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, ImputerScaler]:
    """
    Impute missing values and scale features for train/val/test.

    Parameters
    ----------
    train_df, val_df, test_df : pd.DataFrame
        Split data
    feature_cols : List[str]
        Feature columns
    n_neighbors : int
        Number of neighbors for KNN imputation

    Returns
    -------
    Tuple of transformed DataFrames and fitted ImputerScaler
    """
    # Initialize imputer/scaler
    imputer_scaler = ImputerScaler(n_neighbors=n_neighbors)

    # Fit on train, transform all
    train_transformed = imputer_scaler.fit_transform(train_df, feature_cols)
    val_transformed = imputer_scaler.transform(val_df)
    test_transformed = imputer_scaler.transform(test_df)

    # Add back non-feature columns (target, identifiers)
    for col in train_df.columns:
        if col not in feature_cols:
            train_transformed[col] = train_df[col].values
            val_transformed[col] = val_df[col].values
            test_transformed[col] = test_df[col].values

    return train_transformed, val_transformed, test_transformed, imputer_scaler