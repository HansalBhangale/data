"""
Configuration & Constants
=========================
Central configuration for the S&P 500 fundamental analysis pipeline.
Contains SEC EDGAR API settings, XBRL tag mappings, and pipeline parameters.
"""

import os
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Project Paths
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
CACHE_DIR = BASE_DIR / "cache"
CACHE_COMPANY_FACTS_DIR = CACHE_DIR / "company_facts"
CACHE_SUBMISSIONS_DIR = CACHE_DIR / "submissions"
CACHE_MARKET_DATA_DIR = CACHE_DIR / "market_data"
CHECKPOINT_DIR = BASE_DIR / "checkpoints"
OUTPUT_DIR = BASE_DIR

# Create directories
for d in [CACHE_COMPANY_FACTS_DIR, CACHE_SUBMISSIONS_DIR, CACHE_MARKET_DATA_DIR, CHECKPOINT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ─────────────────────────────────────────────────────────────
# SEC EDGAR API Configuration
# ─────────────────────────────────────────────────────────────
# The SEC requires a descriptive User-Agent header with contact email.
# We rotate between two emails if one gets rate-limited.
SEC_USER_AGENTS = [
    "SP500Pipeline bhangalehansal@gmail.com",
    "SP500Pipeline hansal.17167@sakec.ac.in",
]
SEC_USER_AGENT = SEC_USER_AGENTS[0]  # Primary

SEC_BASE_URL = "https://data.sec.gov"
SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_COMPANY_FACTS_URL = f"{SEC_BASE_URL}/api/xbrl/companyfacts/CIK{{cik}}.json"
SEC_SUBMISSIONS_URL = f"{SEC_BASE_URL}/submissions/CIK{{cik}}.json"

# ─────────────────────────────────────────────────────────────
# Rate Limiting
# ─────────────────────────────────────────────────────────────
SEC_MAX_REQUESTS_PER_SECOND = 10  # SEC hard limit
SEC_REQUESTS_PER_SECOND = 8      # We stay safely below the limit
SEC_MAX_RETRIES = 5
SEC_BACKOFF_BASE = 1.0            # Base for exponential backoff (seconds)
SEC_BACKOFF_MAX = 60.0            # Max backoff wait (seconds)

# ─────────────────────────────────────────────────────────────
# Cache Settings
# ─────────────────────────────────────────────────────────────
CACHE_EXPIRY_HOURS = 168  # 7 days - EDGAR data doesn't change fast
CACHE_ENABLED = True

# ─────────────────────────────────────────────────────────────
# Pipeline Settings
# ─────────────────────────────────────────────────────────────
START_YEAR = 2000
DATA_START_DATE = "2000-01-01"
TEST_TICKERS = ["AAPL", "MSFT", "JNJ", "JPM", "XOM", "PG", "UNH", "V", "HD", "MA"]
OUTPUT_FILENAME = "sp500_fundamental_dataset.csv"

# ─────────────────────────────────────────────────────────────
# XBRL Tag Mapping (Priority-Ordered Fallbacks)
# ─────────────────────────────────────────────────────────────
# Each financial concept maps to a list of XBRL tags to try in order.
# The first tag found in the company's facts will be used.
# Tags are from the 'us-gaap' taxonomy unless prefixed with 'dei:'.

XBRL_TAG_MAP = {
    # ── Income Statement ──
    "revenue": [
        "Revenues",
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "RevenueFromContractWithCustomerIncludingAssessedTax",
        "SalesRevenueNet",
        "SalesRevenueGoodsNet",
        "SalesRevenueServicesNet",
        "InterestAndDividendIncomeOperating",  # For banks/financials
    ],
    "cost_of_revenue": [
        "CostOfRevenue",
        "CostOfGoodsAndServicesSold",
        "CostOfGoodsSold",
        "CostOfServices",
    ],
    "gross_profit": [
        "GrossProfit",
    ],
    "operating_income": [
        "OperatingIncomeLoss",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesExtraordinaryItemsNoncontrollingInterest",
        "IncomeLossFromContinuingOperationsBeforeIncomeTaxesMinorityInterestAndIncomeLossFromEquityMethodInvestments",
    ],
    "net_income": [
        "NetIncomeLoss",
        "ProfitLoss",
        "NetIncomeLossAvailableToCommonStockholdersBasic",
        "NetIncomeLossAvailableToCommonStockholdersDiluted",
    ],
    "ebit": [
        "OperatingIncomeLoss",  # Often same as operating income
    ],
    "depreciation_amortization": [
        "DepreciationDepletionAndAmortization",
        "DepreciationAndAmortization",
        "Depreciation",
        "AmortizationOfIntangibleAssets",
    ],
    "interest_expense": [
        "InterestExpense",
        "InterestExpenseDebt",
        "InterestIncomeExpenseNet",
    ],

    # ── Balance Sheet ──
    "total_assets": [
        "Assets",
    ],
    "total_liabilities": [
        "Liabilities",
        "LiabilitiesAndStockholdersEquity",  # Need to subtract equity
    ],
    "stockholders_equity": [
        "StockholdersEquity",
        "StockholdersEquityIncludingPortionAttributableToNoncontrollingInterest",
    ],
    "cash_and_equivalents": [
        "CashAndCashEquivalentsAtCarryingValue",
        "CashCashEquivalentsAndShortTermInvestments",
        "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents",
        "Cash",
    ],
    "current_assets": [
        "AssetsCurrent",
    ],
    "current_liabilities": [
        "LiabilitiesCurrent",
    ],
    "long_term_debt": [
        "LongTermDebt",
        "LongTermDebtNoncurrent",
        "LongTermDebtAndCapitalLeaseObligations",
    ],
    "short_term_debt": [
        "ShortTermBorrowings",
        "DebtCurrent",
        "CommercialPaper",
    ],
    "total_debt": [
        "LongTermDebt",
        "DebtAndCapitalLeaseObligations",
    ],
    "book_value_per_share": [
        "BookValuePerShareDiluted",
    ],

    # -- Cash Flow Statement --
    "operating_cash_flow": [
        "NetCashProvidedByUsedInOperatingActivities",
        "NetCashProvidedByUsedInOperatingActivitiesContinuingOperations",
        "NetCashProvidedByOperatingActivities",
        "NetCashProvidedByOperatingActivitiesContinuingOperations",
    ],
    "investing_cash_flow": [
        "NetCashProvidedByUsedInInvestingActivities",
        "NetCashProvidedByUsedInInvestingActivitiesContinuingOperations",
        "NetCashProvidedByInvestingActivities",
        "NetCashProvidedByInvestingActivitiesContinuingOperations",
    ],
    "financing_cash_flow": [
        "NetCashProvidedByUsedInFinancingActivities",
        "NetCashProvidedByUsedInFinancingActivitiesContinuingOperations",
        "NetCashProvidedByFinancingActivities",
        "NetCashProvidedByFinancingActivitiesContinuingOperations",
    ],
    "capital_expenditures": [
        "PaymentsToAcquirePropertyPlantAndEquipment",
        "PaymentsToAcquireProductiveAssets",
        "PaymentsForCapitalImprovements",
        "CapitalExpenditureDiscontinuedOperations",
    ],

    # ── Shares ──
    "shares_outstanding": [
        "CommonStockSharesOutstanding",
        "WeightedAverageNumberOfShareOutstandingBasicAndDiluted",
        "WeightedAverageNumberOfSharesOutstandingBasic",
        "WeightedAverageNumberOfDilutedSharesOutstanding",
    ],
    "shares_outstanding_dei": [
        "EntityCommonStockSharesOutstanding",  # This is in 'dei' taxonomy
    ],
}

# Which tags live in the 'dei' taxonomy instead of 'us-gaap'
DEI_TAGS = {
    "EntityCommonStockSharesOutstanding",
}

# ─────────────────────────────────────────────────────────────
# Fiscal Period Mapping
# ─────────────────────────────────────────────────────────────
# Map SEC fiscal period codes to standard quarter labels
FP_MAP = {
    "Q1": "Q1",
    "Q2": "Q2",
    "Q3": "Q3",
    "Q4": "Q4",  # Sometimes appears in 10-Q for Q4 data
    "FY": "FY",  # Annual (10-K)
}

# ─────────────────────────────────────────────────────────────
# Winsorization Percentiles
# ─────────────────────────────────────────────────────────────
WINSORIZE_LOWER = 0.01  # 1st percentile
WINSORIZE_UPPER = 0.99  # 99th percentile

# Columns to winsorize (ratio/growth columns)
WINSORIZE_COLUMNS = [
    "revenue_qoq_growth", "revenue_yoy_growth", "net_income_yoy_growth",
    "gross_margin", "operating_margin", "net_margin", "roa", "roe",
    "debt_to_equity", "current_ratio", "cash_ratio",
    "fcf_margin", "cf_quality",
    "pe_ratio", "pb_ratio", "ps_ratio", "ev_ebitda",
]
