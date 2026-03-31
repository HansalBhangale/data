"""
Central configuration for SP500 ML pipeline.
"""

import pandas as pd
from typing import Dict, List, Tuple

# =============================================================================
# GICS Sector Mapping (sub_industry -> sector)
# =============================================================================
GICS_SECTOR_MAPPING = {
    # Energy
    'Oil & Gas Exploration & Production': 'Energy',
    'Oil & Gas Refining & Marketing': 'Energy',
    'Oil & Gas Storage & Transportation': 'Energy',
    'Coal & Consumable Fuels': 'Energy',
    'Integrated Oil & Gas': 'Energy',
    'Oil & Gas Equipment & Services': 'Energy',

    # Materials
    'Chemicals': 'Materials',
    'Construction Materials': 'Materials',
    'Containers & Packaging': 'Materials',
    'Metals & Mining': 'Materials',
    'Paper & Forest Products': 'Materials',

    # Industrials
    'Aerospace & Defense': 'Industrials',
    'Building Products': 'Industrials',
    'Construction & Engineering': 'Industrials',
    'Electrical Components & Equipment': 'Industrials',
    'Heavy Electrical Equipment': 'Industrials',
    'Industrial Conglomerates': 'Industrials',
    'Industrial Machinery': 'Industrials',
    'Trading Companies & Distributors': 'Industrials',
    'Airlines': 'Industrials',
    'Ground Transportation': 'Industrials',
    'Marine Transportation': 'Industrials',
    'Railroads': 'Industrials',
    'Transportation Infrastructure': 'Industrials',
    'Trucking': 'Industrials',
    'Air Freight & Logistics': 'Industrials',
    'Commercial Printing': 'Industrials',
    'Environmental & Waste Services': 'Industrials',
    'Office Services & Supplies': 'Industrials',
    'Diversified Support Services': 'Industrials',
    'Human Resource & Employment Services': 'Industrials',
    'Research & Consulting Services': 'Industrials',
    'Security & Alarm Services': 'Industrials',
    'Diversified Industrial Goods': 'Industrials',
    'Distributors': 'Industrials',

    # Consumer Discretionary
    'Automobile Manufacturers': 'Consumer Discretionary',
    'Auto Parts & Equipment': 'Consumer Discretionary',
    'Tires & Rubber': 'Consumer Discretionary',
    'Automotive Retail': 'Consumer Discretionary',
    'Apparel, Accessories & Luxury Goods': 'Consumer Discretionary',
    'Footwear': 'Consumer Discretionary',
    'Internet & Direct Marketing Retail': 'Consumer Discretionary',
    'Department Stores': 'Consumer Discretionary',
    'Apparel Retail': 'Consumer Discretionary',
    'Computer & Electronics Retail': 'Consumer Discretionary',
    'Specialty Stores': 'Consumer Discretionary',
    'General Merchandise Stores': 'Consumer Discretionary',
    'Home Improvement Retail': 'Consumer Discretionary',
    'Hotels, Resorts & Cruise Lines': 'Consumer Discretionary',
    'Restaurants': 'Consumer Discretionary',
    'Leisure Facilities': 'Consumer Discretionary',
    'Leisure Products': 'Consumer Discretionary',
    'Broadcasting': 'Consumer Discretionary',
    'Cable & Satellite': 'Consumer Discretionary',
    'Movies & Entertainment': 'Consumer Discretionary',
    'Publishing': 'Consumer Discretionary',
    'Consumer Electronics': 'Consumer Discretionary',
    'Home Furnishings': 'Consumer Discretionary',
    'Housewares': 'Consumer Discretionary',
    'Toys & Games': 'Consumer Discretionary',
    'Casinos & Gaming': 'Consumer Discretionary',
    'Homebuilding': 'Consumer Discretionary',

    # Consumer Staples
    'Brewers': 'Consumer Staples',
    'Distillers & Wineries': 'Consumer Staples',
    'Soft Drinks': 'Consumer Staples',
    'Agricultural Products': 'Consumer Staples',
    'Packaged Foods & Meats': 'Consumer Staples',
    'Tobacco': 'Consumer Staples',
    'Food Retail': 'Consumer Staples',
    'Drug Retail': 'Consumer Staples',
    'Hypermarkets & Super Centers': 'Consumer Staples',
    'Personal Products': 'Consumer Staples',
    'Household Products': 'Consumer Staples',

    # Health Care
    'Biotechnology': 'Health Care',
    'Pharmaceuticals': 'Health Care',
    'Life Sciences Tools & Services': 'Health Care',
    'Health Care Distributors': 'Health Care',
    'Health Care Services': 'Health Care',
    'Health Care Facilities': 'Health Care',
    'Managed Health Care': 'Health Care',
    'Health Care Equipment': 'Health Care',
    'Health Care Supplies': 'Health Care',

    # Financials
    'Asset Management & Custody Banks': 'Financials',
    'Investment Banking & Brokerage': 'Financials',
    'Diversified Financial Services': 'Financials',
    'Consumer Finance': 'Financials',
    'Capital Markets': 'Financials',
    'Mortgage Real Estate Investment Trusts (REITs)': 'Financials',
    'Diversified Banks': 'Financials',
    'Regional Banks': 'Financials',
    'Thrifts & Mortgage Finance': 'Financials',
    'Diversified Insurance': 'Financials',
    'Insurance Brokers': 'Financials',
    'Life & Health Insurance': 'Financials',
    'Multi-line Insurance': 'Financials',
    'Property & Casualty Insurance': 'Financials',
    'Reinsurance': 'Financials',
    'Financial Exchanges & Data': 'Financials',
    'Data Processing & Outsourced Services': 'Financials',
    'Transaction & Payment Processing Services': 'Financials',
    'Commercial REITs': 'Financials',
    'Diversified REITs': 'Financials',
    'Industrial REITs': 'Financials',
    'Office REITs': 'Financials',
    'Residential REITs': 'Financials',
    'Retail REITs': 'Financials',
    'Specialized REITs': 'Financials',
    'Health Care REITs': 'Financials',
    'Hotel & Resort REITs': 'Financials',
    'Mortgage Finance': 'Financials',

    # Information Technology
    'Application Software': 'Information Technology',
    'Data Processing & Outsourced Services': 'Information Technology',
    'Systems Software': 'Information Technology',
    'Internet Software & Services': 'Information Technology',
    'IT Consulting & Other Services': 'Information Technology',
    'Communications Equipment': 'Information Technology',
    'Networking Equipment': 'Information Technology',
    'Technology Hardware, Storage & Peripherals': 'Information Technology',
    'Electronic Equipment & Instruments': 'Information Technology',
    'Electronic Manufacturing Services': 'Information Technology',
    'Technology Distributors': 'Information Technology',
    'Semiconductors': 'Information Technology',
    'Semiconductor Equipment': 'Information Technology',
    'Electronic Components': 'Information Technology',
    'Semiconductor Materials & Equipment': 'Information Technology',

    # Communication Services
    'Integrated Telecommunication Services': 'Communication Services',
    'Wireless Telecommunication Services': 'Communication Services',
    'Advertising': 'Communication Services',
    'Broadcasting': 'Communication Services',
    'Cable & Satellite': 'Communication Services',
    'Movies & Entertainment': 'Communication Services',
    'Publishing': 'Communication Services',
    'Interactive Media & Services': 'Communication Services',
    'Data Processing & Outsourced Services': 'Communication Services',

    # Utilities
    'Electric Utilities': 'Utilities',
    'Gas Utilities': 'Utilities',
    'Multi-Utilities': 'Utilities',
    'Water Utilities': 'Utilities',
    'Independent Power Producers': 'Utilities',

    # Real Estate
    'Commercial REITs': 'Real Estate',
    'Diversified REITs': 'Real Estate',
    'Industrial REITs': 'Real Estate',
    'Office REITs': 'Real Estate',
    'Residential REITs': 'Real Estate',
    'Retail REITs': 'Real Estate',
    'Specialized REITs': 'Real Estate',
    'Health Care REITs': 'Real Estate',
    'Hotel & Resort REITs': 'Real Estate',
    'Real Estate Operating Companies': 'Real Estate',
    'Real Estate Development': 'Real Estate',
    'Real Estate Services': 'Real Estate',
}

# =============================================================================
# Feature Categories
# =============================================================================

BALANCE_SHEET_COLS = [
    'total_assets', 'total_liabilities', 'stockholders_equity',
    'current_assets', 'current_liabilities', 'short_term_debt',
    'cash_and_equivalents', 'long_term_debt', 'total_debt'
]

INCOME_STATEMENT_COLS = [
    'revenue', 'cost_of_revenue', 'gross_profit', 'operating_income',
    'net_income', 'ebit', 'ebitda', 'interest_expense',
    'depreciation_amortization', 'shares_outstanding'
]

CASH_FLOW_COLS = [
    'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
    'capital_expenditures', 'free_cash_flow'
]

PROFITABILITY_COLS = [
    'gross_margin', 'operating_margin', 'net_margin', 'roa', 'roe'
]

LIQUIDITY_COLS = [
    'debt_to_equity', 'current_ratio', 'cash_ratio'
]

GROWTH_COLS = [
    'revenue_qoq_growth', 'revenue_yoy_growth', 'net_income_yoy_growth',
    'operating_income_yoy_growth', 'total_assets_yoy_growth'
]

VALUATION_COLS = [
    'pe_ratio', 'pb_ratio', 'ps_ratio', 'enterprise_value', 'ev_ebitda'
]

TTM_COLS = [
    'net_income_ttm', 'revenue_ttm', 'ebitda_ttm'
]

MARKET_COLS = [
    'market_cap', 'avg_daily_volume', 'stock_price'
]

# =============================================================================
# Target Columns (NOT features)
# =============================================================================

TARGET_COLS = [
    'fwd_return_1y', 'fwd_return_3y',
    'spy_fwd_return_1y', 'spy_fwd_return_3y',
    'excess_return_1y', 'excess_return_3y',
    'excess_return_1y_rank', 'excess_return_3y_rank'
]

# =============================================================================
# Columns to Exclude from Features (identifiers, dates, text, etc.)
# =============================================================================

EXCLUDE_COLS = [
    'ticker', 'cik', 'entity_name', 'quarter_end', 'quarter_end_std',
    'quarter_label', 'fp', 'fy', 'sector', 'sub_industry',
    'year', 'quarter',
    *TARGET_COLS,
    'stock_price', 'avg_daily_volume', 'spy_fwd_return_1y', 'spy_fwd_return_3y'
]

# =============================================================================
# Outlier Clipping Bounds
# =============================================================================

CLIP_BOUNDS = {
    'pe_ratio': (0, 200),
    'pb_ratio': (0, 50),
    'ps_ratio': (0, 50),
    'ev_ebitda': (0, 100),
    'debt_to_equity': (0, 20),
    'roe': (-5, 5),
    'roa': (-2, 2),
    'current_ratio': (0, 20),
    'revenue_qoq_growth': (-5, 5),
    'revenue_yoy_growth': (-5, 5),
    'net_income_yoy_growth': (-10, 10),
    'operating_income_yoy_growth': (-10, 10),
    'total_assets_yoy_growth': (-5, 5),
}

# =============================================================================
# Columns for Annual-Only Forward Fill
# =============================================================================

ANNUAL_FFILL_COLS = [
    'operating_cash_flow', 'investing_cash_flow', 'financing_cash_flow',
    'capital_expenditures', 'free_cash_flow', 'depreciation_amortization',
    'cost_of_revenue', 'revenue'
]

# =============================================================================
# Columns for Sector Normalization (z-score)
# =============================================================================

SECTOR_NORMALIZE_COLS = [
    'pe_ratio', 'pb_ratio', 'roe', 'roa',
    'debt_to_equity', 'operating_margin', 'net_margin', 'ev_ebitda',
    'revenue_yoy_growth',
    'total_assets_yoy_growth',
    'fcf_yield',
    'gross_margin',
]

# =============================================================================
# Temporal Lag Configuration
# =============================================================================

TEMPORAL_LAGS = {
    # Feature lags: t-1, t-2, t-4 (1 quarter, 2 quarters, 1 year back)
    'feature_lags': [1, 2, 4],

    # Columns to create lags for
    'lag_features': [
        'revenue', 'net_income', 'operating_income', 'ebitda',
        'gross_margin', 'operating_margin', 'net_margin', 'roa', 'roe',
        'debt_to_equity', 'current_ratio', 'pe_ratio', 'pb_ratio',
        'revenue_qoq_growth', 'revenue_yoy_growth'
        # REMOVED: stock_price - causes target leakage
    ],

    # Momentum features (ratio of current to lagged value)
    'momentum_features': [
        'revenue', 'net_income', 'ebitda'
        # REMOVED: stock_price - causes target leakage
    ]
}

# =============================================================================
# Time Split Configuration
# =============================================================================

TIME_SPLIT = {
    'train_end_year': 2019,
    'val_start_year': 2020,
    'val_end_year': 2021,
    'test_start_year': 2022
}

# =============================================================================
# LightGBM Hyperparameters (base config, tuned by Optuna)
# =============================================================================

LGBM_BASE_PARAMS = {
    'objective': 'regression',
    'metric': 'rmse',
    'verbosity': -1,
    'boosting_type': 'gbdt',
    'num_leaves': 63,
    'learning_rate': 0.03,
    'n_estimators': 1500,
    'min_child_samples': 30,
    'reg_alpha': 0.1,
    'reg_lambda': 0.1,
    'subsample': 0.8,
    'colsample_bytree': 0.8,
    'random_state': 42,
}

OPTUNA_PARAMS = {
    'num_leaves': (8, 31),
    'learning_rate': (0.005, 0.05),
    'n_estimators': (500, 3000),
    'min_child_samples': (80, 200),
    'reg_alpha': (0.5, 5.0),
    'reg_lambda': (0.5, 5.0),
    'subsample': (0.4, 0.7),
    'colsample_bytree': (0.4, 0.7),
    'max_depth': (3, 6),
    'min_gain_to_split': (0.05, 0.5),
}

# =============================================================================
# Risk Score Weights
# =============================================================================

RISK_WEIGHTS = {
    'leverage_risk': 0.25,
    'liquidity_risk': 0.15,
    'profitability_risk': 0.15,
    'earnings_volatility': 0.20,
    'valuation_risk': 0.10,
    'model_uncertainty': 0.15,
}