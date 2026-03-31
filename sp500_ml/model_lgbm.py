"""
LightGBM regression model for performance prediction.
Includes hyperparameter tuning with Optuna and SHAP feature importance.
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
import lightgbm as lgb
from pathlib import Path
import joblib
import warnings

# Suppress LightGBM warnings
warnings.filterwarnings('ignore', category=UserWarning)

try:
    import optuna
    OPTUNA_AVAILABLE = True
except ImportError:
    OPTUNA_AVAILABLE = False
    print("Optuna not available. Using default hyperparameters.")

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    print("SHAP not available. Feature importance will use built-in methods.")


class LightGBMModel:
    """
    LightGBM regression model with Optuna tuning and SHAP explanations.
    """

    def __init__(
        self,
        target_col: str,
        params: Optional[Dict] = None,
        random_state: int = 42
    ):
        """
        Initialize LightGBM model.

        Parameters
        ----------
        target_col : str
            Target column name ('excess_return_1y' or 'excess_return_3y')
        params : Dict, optional
            LightGBM parameters (uses defaults if not provided)
        random_state : int
            Random seed
        """
        self.target_col = target_col
        self.random_state = random_state
        self.params = params or {}
        self.model_ = None
        self.feature_names_ = None
        self.best_params_ = None

    def _get_default_params(self) -> Dict:
        """Get default LightGBM parameters with stronger regularization."""
        return {
            'objective': 'regression',
            'metric': 'rmse',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'num_leaves': 16,
            'learning_rate': 0.01,
            'n_estimators': 2000,
            'min_child_samples': 100,
            'reg_alpha': 1.0,
            'reg_lambda': 2.0,
            'subsample': 0.5,
            'colsample_bytree': 0.5,
            'min_gain_to_split': 0.1,
            'max_depth': 5,
            'random_state': self.random_state,
        }

    def tune_hyperparameters(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: pd.DataFrame,
        y_val: pd.Series,
        n_trials: int = 50,
        timeout: int = 600
    ) -> Dict:
        """
        Tune hyperparameters using Optuna.

        Parameters
        ----------
        X_train, y_train : Training data
        X_val, y_val : Validation data
        n_trials : int
            Number of Optuna trials
        timeout : int
            Timeout in seconds

        Returns
        -------
        Dict
            Best parameters found
        """
        if not OPTUNA_AVAILABLE:
            print("Optuna not available. Using default parameters.")
            return self._get_default_params()

        print(f"Tuning hyperparameters with {n_trials} trials...")

        def objective(trial):
            params = {
                'objective': 'regression',
                'metric': 'rmse',
                'verbosity': -1,
                'boosting_type': 'gbdt',
                'random_state': self.random_state,
                'num_leaves': trial.suggest_int('num_leaves', 8, 31),
                'learning_rate': trial.suggest_float('learning_rate', 0.005, 0.05, log=True),
                'n_estimators': trial.suggest_int('n_estimators', 500, 3000),
                'min_child_samples': trial.suggest_int('min_child_samples', 80, 200),
                'reg_alpha': trial.suggest_float('reg_alpha', 0.5, 5.0),
                'reg_lambda': trial.suggest_float('reg_lambda', 0.5, 5.0),
                'subsample': trial.suggest_float('subsample', 0.4, 0.7),
                'colsample_bytree': trial.suggest_float('colsample_bytree', 0.4, 0.7),
                'max_depth': trial.suggest_int('max_depth', 3, 6),
                'min_gain_to_split': trial.suggest_float('min_gain_to_split', 0.05, 0.5),
            }

            model = lgb.LGBMRegressor(**params)
            model.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                callbacks=[lgb.early_stopping(50), lgb.log_evaluation(0)]
            )
            return model.best_score_['valid_0']['rmse']

        study = optuna.create_study(direction='minimize')
        study.optimize(objective, n_trials=n_trials, timeout=timeout, show_progress_bar=True)

        self.best_params_ = study.best_params
        self.best_params_.update({
            'objective': 'regression',
            'metric': 'rmse',
            'verbosity': -1,
            'boosting_type': 'gbdt',
            'random_state': self.random_state,
        })

        print(f"Best RMSE: {study.best_value:.4f}")
        print(f"Best params: {self.best_params_}")

        return self.best_params_

    def fit(
        self,
        X_train: pd.DataFrame,
        y_train: pd.Series,
        X_val: Optional[pd.DataFrame] = None,
        y_val: Optional[pd.Series] = None,
        tune: bool = False,
        n_trials: int = 30
    ) -> 'LightGBMModel':
        """
        Fit LightGBM model.

        Parameters
        ----------
        X_train : pd.DataFrame
            Training features
        y_train : pd.Series
            Training target
        X_val, y_val : Optional validation data for early stopping
        tune : bool
            Whether to tune hyperparameters with Optuna
        n_trials : int
            Number of Optuna trials (if tuning)

        Returns
        -------
        self
        """
        self.feature_names_ = list(X_train.columns)

        # Get parameters
        if tune and X_val is not None and y_val is not None:
            params = self.tune_hyperparameters(X_train, y_train, X_val, y_val, n_trials=n_trials)
        else:
            params = {**self._get_default_params(), **self.params}

        # Train model
        print(f"Training LightGBM for target: {self.target_col}")
        print(f"  Features: {len(self.feature_names_)}")
        print(f"  Training samples: {len(X_train)}")

        self.model_ = lgb.LGBMRegressor(**params)

        callbacks = [lgb.log_evaluation(100)]

        if X_val is not None and y_val is not None:
            callbacks.append(lgb.early_stopping(50))
            self.model_.fit(
                X_train, y_train,
                eval_set=[(X_val, y_val)],
                callbacks=callbacks
            )
        else:
            self.model_.fit(X_train, y_train, callbacks=callbacks)

        print(f"Model trained. Best iteration: {self.model_.best_iteration_}")

        return self

    def predict(self, X: pd.DataFrame) -> np.ndarray:
        """
        Predict target values.

        Parameters
        ----------
        X : pd.DataFrame
            Features

        Returns
        -------
        np.ndarray
            Predictions
        """
        if self.model_ is None:
            raise ValueError("Model not fitted. Call fit() first.")

        return self.model_.predict(X)

    def get_feature_importance(self, importance_type: str = 'gain') -> pd.DataFrame:
        """
        Get feature importance from trained model.

        Parameters
        ----------
        importance_type : str
            'gain' or 'split'

        Returns
        -------
        pd.DataFrame
            Feature importance sorted by importance
        """
        if self.model_ is None:
            raise ValueError("Model not fitted. Call fit() first.")

        importance = self.model_.feature_importances_
        df = pd.DataFrame({
            'feature': self.feature_names_,
            'importance': importance
        }).sort_values('importance', ascending=False)

        return df

    def get_shap_values(
        self,
        X: pd.DataFrame,
        max_samples: int = 1000
    ) -> Tuple[np.ndarray, pd.DataFrame]:
        """
        Compute SHAP values for feature importance.

        Parameters
        ----------
        X : pd.DataFrame
            Data to explain
        max_samples : int
            Maximum samples to use for SHAP (for speed)

        Returns
        -------
        Tuple[np.ndarray, pd.DataFrame]
            SHAP values and mean absolute SHAP per feature
        """
        if not SHAP_AVAILABLE:
            print("SHAP not available. Use get_feature_importance() instead.")
            return None, None

        if self.model_ is None:
            raise ValueError("Model not fitted. Call fit() first.")

        # Sample for speed
        if len(X) > max_samples:
            X_sample = X.sample(n=max_samples, random_state=self.random_state)
        else:
            X_sample = X

        print(f"Computing SHAP values for {len(X_sample)} samples...")

        # Use TreeExplainer for LightGBM
        explainer = shap.TreeExplainer(self.model_)
        shap_values = explainer.shap_values(X_sample)

        # Mean absolute SHAP values
        mean_shap = np.abs(shap_values).mean(axis=0)
        shap_df = pd.DataFrame({
            'feature': self.feature_names_,
            'mean_abs_shap': mean_shap
        }).sort_values('mean_abs_shap', ascending=False)

        return shap_values, shap_df

    def save(self, path: str) -> None:
        """Save model to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump({
            'model': self.model_,
            'feature_names': self.feature_names_,
            'target_col': self.target_col,
            'params': self.params,
            'best_params': self.best_params_,
        }, path)
        print(f"Model saved to {path}")

    def load(self, path: str) -> 'LightGBMModel':
        """Load model from file."""
        data = joblib.load(path)
        self.model_ = data['model']
        self.feature_names_ = data['feature_names']
        self.target_col = data['target_col']
        self.params = data.get('params', {})
        self.best_params_ = data.get('best_params')
        return self


def train_excess_return_model(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    feature_cols: List[str],
    target_col: str = 'excess_return_1y',
    tune: bool = False,
    n_trials: int = 30
) -> Tuple[LightGBMModel, pd.DataFrame, pd.Series]:
    """
    Train a model for predicting excess returns.

    Parameters
    ----------
    train_df, val_df : pd.DataFrame
        Training and validation data
    feature_cols : List[str]
        Feature columns
    target_col : str
        Target column ('excess_return_1y' or 'excess_return_3y')
    tune : bool
        Whether to tune hyperparameters
    n_trials : int
        Number of Optuna trials

    Returns
    -------
    Tuple[LightGBMModel, pd.DataFrame, pd.Series]
        Trained model, features, and target
    """
    # Prepare data
    X_train = train_df[feature_cols]
    y_train = train_df[target_col]
    X_val = val_df[feature_cols]
    y_val = val_df[target_col]

    # Initialize model
    model = LightGBMModel(target_col=target_col)

    # Train
    model.fit(
        X_train, y_train,
        X_val=X_val, y_val=y_val,
        tune=tune, n_trials=n_trials
    )

    return model, X_train, y_train


def predict_with_model(
    model: LightGBMModel,
    df: pd.DataFrame,
    feature_cols: List[str]
) -> np.ndarray:
    """
    Make predictions with a trained model.

    Parameters
    ----------
    model : LightGBMModel
        Trained model
    df : pd.DataFrame
        Data to predict
    feature_cols : List[str]
        Feature columns

    Returns
    -------
    np.ndarray
        Predictions
    """
    X = df[feature_cols]
    return model.predict(X)