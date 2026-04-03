"""
Core package - Business logic modules
"""

from .mappings import (
    map_age_to_features,
    map_education_to_features,
    map_occupation_to_features,
    map_income_to_features,
    map_networth_to_features,
    map_assets_to_features,
    build_model_features,
    validate_user_inputs,
)

from .data_loader import (
    load_risk_model,
    load_fundamental_model,
    load_technical_model,
    load_daily_prices,
    load_stock_risk_scores,
    predict_risk_score,
    predict_stock_scores,
    get_enhanced_investor_params,
    get_bucket_config,
)

from .portfolio_builder import (
    load_model_predictions,
    build_investor_portfolio,
)

from .backtest import (
    calculate_real_backtest,
    format_percentage,
    format_ratio,
)

__all__ = [
    # Mappings
    'map_age_to_features',
    'map_education_to_features',
    'map_occupation_to_features',
    'map_income_to_features',
    'map_networth_to_features',
    'map_assets_to_features',
    'build_model_features',
    'validate_user_inputs',
    # Data Loader
    'load_risk_model',
    'load_fundamental_model',
    'load_technical_model',
    'load_daily_prices',
    'load_stock_risk_scores',
    'predict_risk_score',
    'predict_stock_scores',
    'get_enhanced_investor_params',
    'get_bucket_config',
    # Portfolio Builder
    'load_model_predictions',
    'build_investor_portfolio',
    # Backtest
    'calculate_real_backtest',
    'format_percentage',
    'format_ratio',
]
