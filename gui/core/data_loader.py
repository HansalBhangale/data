"""
Data Loader Module - Model and Data Loading

Loads risk tolerance model, ML models, and price data with caching.
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Tuple, Dict, Optional
import streamlit as st


# =============================================================================
# STUB CLASSES - Required for unpickling risk tolerance model
# =============================================================================

class PCABasedRiskScorer:
    """Stub for PCA-based risk scorer."""
    def __init__(self, df=None):
        self.df = df


class EmpiricalCorrelationScorer:
    """Stub for empirical correlation scorer."""
    def __init__(self, df=None):
        self.df = df


# =============================================================================
# PATH CONFIGURATION
# =============================================================================

def get_base_path() -> Path:
    """Get the base project path."""
    return Path(__file__).parent.parent.parent


def get_risk_model_path() -> Path:
    """Get path to risk tolerance model."""
    return get_base_path() / 'risk prediction' / 'risk_tolerance_model.pkl'


def get_fundamental_model_path() -> Path:
    """Get path to fundamental ML model."""
    return get_base_path() / 'output' / 'model_1y.pkl'


def get_technical_model_path() -> Path:
    """Get path to technical ML model."""
    return get_base_path() / 'output_technical' / 'model_1y.pkl'


def get_fundamental_data_path() -> Path:
    """Get path to preprocessed fundamental data."""
    return get_base_path() / 'output' / 'preprocessed_data.csv'


def get_technical_data_path() -> Path:
    """Get path to technical features (preprocessed or raw)."""
    path = get_base_path() / 'output_technical' / 'technical_features_preprocessed.csv'
    if not path.exists():
        path = get_base_path() / 'output_technical' / 'technical_features.csv'
    return path


def get_daily_prices_path() -> Path:
    """Get path to daily prices data."""
    return get_base_path() / 'daily_prices_all.csv'


# =============================================================================
# MODEL LOADING
# =============================================================================

@st.cache_resource
def load_risk_model() -> Tuple[Optional[object], Optional[list]]:
    """
    Load the risk tolerance prediction model.
    
    Returns
    -------
    Tuple[model, feature_names]
        - model: The trained risk tolerance model
        - feature_names: List of feature names expected by the model
    """
    path = get_risk_model_path()
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
        return data.get('model'), data.get('features', [])
    except Exception as e:
        st.error(f"Failed to load risk model: {e}")
        return None, []


@st.cache_resource
def load_fundamental_model() -> Tuple[Optional[object], Optional[list], pd.DataFrame]:
    """
    Load the fundamental analysis ML model and data.
    
    Returns
    -------
    Tuple[model, feature_names, dataframe]
    """
    model_path = get_fundamental_model_path()
    data_path = get_fundamental_data_path()
    
    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data.get('model')
        feature_names = model_data.get('feature_names', [])
        
        df = pd.read_csv(data_path)
        
        return model, feature_names, df
    except Exception as e:
        st.error(f"Failed to load fundamental model: {e}")
        return None, [], pd.DataFrame()


@st.cache_resource
def load_technical_model() -> Tuple[Optional[object], Optional[list], pd.DataFrame]:
    """
    Load the technical analysis ML model and data.
    
    Returns
    -------
    Tuple[model, feature_names, dataframe]
    """
    model_path = get_technical_model_path()
    data_path = get_technical_data_path()
    
    try:
        with open(model_path, 'rb') as f:
            model_data = pickle.load(f)
        model = model_data.get('model')
        feature_names = model_data.get('feature_names', [])
        
        df = pd.read_csv(data_path)
        
        return model, feature_names, df
    except Exception as e:
        st.error(f"Failed to load technical model: {e}")
        return None, [], pd.DataFrame()


@st.cache_data
def load_daily_prices() -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load daily prices and separate SPY.
    
    Returns
    -------
    Tuple[stock_prices, spy_prices]
        - stock_prices: DataFrame with columns [date, ticker, adj_close, ...]
        - spy_prices: DataFrame with SPY price data
    """
    path = get_daily_prices_path()
    
    try:
        df = pd.read_csv(path, parse_dates=['date'])
        spy = df[df['ticker'] == 'SPY'].copy()
        stocks = df[df['ticker'] != 'SPY'].copy()
        
        return stocks, spy
    except Exception as e:
        st.error(f"Failed to load daily prices: {e}")
        return pd.DataFrame(), pd.DataFrame()


@st.cache_data
def load_stock_risk_scores() -> pd.DataFrame:
    """Load stock risk scores from precomputed data."""
    path = get_base_path() / 'output_composite' / 'stock_risk_scores.csv'
    if path.exists():
        return pd.read_csv(path)
    return pd.DataFrame()


# =============================================================================
# PREDICTION FUNCTIONS
# =============================================================================

def predict_risk_score(features: Dict, model: object, feature_names: list) -> float:
    """
    Predict investor risk score from features.
    
    Parameters
    ----------
    features : Dict
        Feature dictionary from build_model_features()
    model : object
        Trained risk tolerance model
    feature_names : list
        Expected feature names
    
    Returns
    -------
    float
        Risk score (0-100)
    """
    if not model or not feature_names:
        return 50.0
    
    try:
        # Create feature vector in correct order
        feature_vector = [features.get(feat, 0) for feat in feature_names]
        X = np.array([feature_vector])
        
        # Predict and clip to 0-100
        score = float(np.clip(model.predict(X)[0], 0, 100))
        return score
    except Exception as e:
        st.error(f"Risk prediction failed: {e}")
        return 50.0


def predict_stock_scores(df: pd.DataFrame, model: object, feature_names: list) -> Dict[str, float]:
    """
    Predict stock scores for all tickers using a model.
    
    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with ticker and feature columns
    model : object
        Trained ML model
    feature_names : list
        Feature column names
    
    Returns
    -------
    Dict[str, float]
        {ticker: score}
    """
    if not model or not feature_names:
        return {}
    
    try:
        # Prepare features
        X = df[feature_names].copy()
        X = X.replace([np.inf, -np.inf], np.nan)
        X = X.fillna(X.median())
        
        # Predict
        preds = model.predict(X)
        
        # Map to ticker
        scores = dict(zip(df['ticker'].values, preds.astype(float)))
        return scores
    except Exception as e:
        st.error(f"Stock prediction failed: {e}")
        return {}


# =============================================================================
# INVESTOR PARAMETERS
# =============================================================================

def get_enhanced_investor_params(risk_score: float) -> Dict:
    """
    Get investor parameters from enhanced portfolio system.
    
    Uses the same params as portfolio_enhanced.py
    """
    from composite.portfolio_enhanced import get_enhanced_params
    return get_enhanced_params(risk_score)


def get_bucket_config(risk_score: float) -> Dict:
    """
    Get bucket configuration for investor.
    
    Uses the same logic as portfolio_enhanced.py
    """
    from composite.portfolio_enhanced import calculate_bucket_weights
    return calculate_bucket_weights(risk_score)
