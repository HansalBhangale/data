"""
Portfolio Database Module — CRUD Operations

Handles saving, retrieving, and deleting portfolios from MongoDB.
Portfolios are stored in the 'portfolios' collection.

Schema
------
{
    user_id          : str
    name             : str
    created_at       : datetime (UTC)
    risk_score       : float
    capital          : float
    risk_category    : str
    equity_weight    : float
    cash_weight      : float
    n_holdings       : int
    allocations      : list[dict]
    buckets          : list
    bucket_weights   : list[float]
    backtest_summary : dict
    rebalance_settings: {
        auto_rebalance     : bool
        rebalance_frequency: str  ("quarterly", "monthly", "manual")
        last_rebalanced   : datetime
        rebalance_threshold: float
    }
    rebalance_history: [
        {
            date              : datetime
            stocks_replaced   : [{"ticker": str, "composite_score": float}]
            stocks_added      : [{"ticker": str, "composite_score": float}]
            reason            : str  ("scheduled" or "risk_profile_change")
        }
    ]
}

backtest_summary sub-document
------------------------------
{
    annual_return    : float
    annual_volatility: float
    sharpe_ratio     : float
    alpha            : float
    beta             : float
    beat_spy         : bool
    total_return     : float   (derived from cumulative_portfolio series)
    spy_total_return : float   (derived from cumulative_spy series)
}
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List

from bson import ObjectId
from bson.errors import InvalidId
from pymongo import DESCENDING
from pymongo.errors import PyMongoError

from .db import get_db

logger = logging.getLogger(__name__)

PORTFOLIOS_COLLECTION = "portfolios"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _derive_total_return(cumulative_series) -> float:
    """
    Derive a total-return scalar from a cumulative-growth pandas Series.

    The series is produced by ``(1 + daily_returns).cumprod()``, so the last
    value represents the growth factor (e.g. 1.12 = +12 %).  We subtract 1
    to obtain the plain return.

    Returns 0.0 safely if the series is None, empty, or raises any error.
    """
    if cumulative_series is None:
        return 0.0
    try:
        if hasattr(cumulative_series, "__len__") and len(cumulative_series) > 0:
            return float(cumulative_series.iloc[-1]) - 1.0
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not derive total return from cumulative series: %s", exc)
    return 0.0


def _build_backtest_summary(backtest: dict) -> dict:
    """
    Extract only the serializable scalar fields we want to persist.

    The raw backtest dict contains pandas Series objects
    (``cumulative_portfolio``, ``cumulative_spy``) that cannot be stored in
    MongoDB directly.  Those are converted to scalar total-return values.
    """
    return {
        "annual_return": float(backtest.get("annual_return", 0.0)),
        "annual_volatility": float(backtest.get("annual_volatility", 0.0)),
        "sharpe_ratio": float(backtest.get("sharpe_ratio", 0.0)),
        "alpha": float(backtest.get("alpha", 0.0)),
        "beta": float(backtest.get("beta", 1.0)),
        "beat_spy": bool(backtest.get("beat_spy", False)),
        "total_return": _derive_total_return(backtest.get("cumulative_portfolio")),
        "spy_total_return": _derive_total_return(backtest.get("cumulative_spy")),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def save_portfolio(
    user_id: str,
    portfolio: dict,
    risk_score: float,
    risk_category: str,
    capital: float,
    backtest: dict,
    name: str = None,
) -> dict:
    """
    Persist a portfolio to the database.

    Parameters
    ----------
    user_id : str
        MongoDB ObjectId string of the owning user.
    portfolio : dict
        Portfolio dict as returned by ``build_portfolio_enhanced``.
        Must contain an ``'allocations'`` key.
    risk_score : float
        Investor risk score (0–100).
    risk_category : str
        Human-readable risk category (e.g. ``"Moderate Growth"``).
    capital : float
        Total investment capital in USD.
    backtest : dict
        Backtest result dict as returned by ``calculate_real_backtest``.
        Pandas Series values are extracted and converted to scalars before
        storage — the raw series objects are never written to MongoDB.
    name : str, optional
        Portfolio display name.  Defaults to
        ``"Portfolio YYYY-MM-DD HH:MM"`` (local wall-clock time).

    Returns
    -------
    dict
        ``{"success": True, "portfolio_id": str}`` on success, or
        ``{"success": False, "error": str}`` on failure.
    """
    # ---- Input validation --------------------------------------------------
    if not user_id:
        return {"success": False, "error": "user_id is required."}
    if not portfolio or "allocations" not in portfolio:
        return {
            "success": False,
            "error": "Invalid portfolio data: missing 'allocations'.",
        }
    if not backtest:
        backtest = {}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    # ---- Default name ------------------------------------------------------
    if not name:
        name = f"Portfolio {datetime.now().strftime('%Y-%m-%d %H:%M')}"

    # ---- Extract fields from portfolio dict --------------------------------
    allocations = portfolio.get("allocations", [])
    equity_weight = portfolio.get("equity_weight", 0.0)
    cash_weight = portfolio.get("cash_weight", 0.0)
    n_holdings = portfolio.get("n_holdings", len(allocations))
    buckets = portfolio.get("buckets", [])
    bucket_weights = portfolio.get("bucket_weights", [])

    # ---- Build serializable backtest summary --------------------------------
    backtest_summary = _build_backtest_summary(backtest)

    # ---- Default rebalance settings ------------------------------------------
    rebalance_settings = {
        "auto_rebalance": False,
        "rebalance_frequency": "quarterly",
        "last_rebalanced": datetime.now(timezone.utc),
        "rebalance_threshold": 0.05,
    }

    # ---- Assemble document -------------------------------------------------
    portfolio_doc = {
        "user_id": user_id,
        "name": name,
        "created_at": datetime.now(timezone.utc),
        "risk_score": float(risk_score),
        "capital": float(capital),
        "risk_category": risk_category,
        "equity_weight": float(equity_weight),
        "cash_weight": float(cash_weight),
        "n_holdings": int(n_holdings),
        "allocations": allocations,
        "buckets": buckets,
        "bucket_weights": bucket_weights,
        "backtest_summary": backtest_summary,
        "rebalance_settings": rebalance_settings,
    }

    try:
        result = db[PORTFOLIOS_COLLECTION].insert_one(portfolio_doc)
        logger.info(
            "Portfolio saved — id: %s  user: %s  name: '%s'",
            result.inserted_id,
            user_id,
            name,
        )
        return {"success": True, "portfolio_id": str(result.inserted_id)}

    except PyMongoError as exc:
        logger.error("Database error saving portfolio for user %s: %s", user_id, exc)
        return {
            "success": False,
            "error": "A database error occurred while saving. Please try again.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error saving portfolio: %s", exc)
        return {"success": False, "error": "An unexpected error occurred while saving."}


def get_user_portfolios(user_id: str) -> list:
    """
    Retrieve all portfolios belonging to a user, newest first.

    Parameters
    ----------
    user_id : str
        MongoDB ObjectId string of the user.

    Returns
    -------
    list[dict]
        List of portfolio documents with ``_id`` converted to ``str``.
        Returns an empty list when the user has no portfolios, the
        connection is unavailable, or any error occurs.
    """
    if not user_id:
        logger.warning("get_user_portfolios called with empty user_id.")
        return []

    db = get_db()
    if db is None:
        logger.error("Database connection unavailable when fetching portfolios.")
        return []

    try:
        cursor = (
            db[PORTFOLIOS_COLLECTION]
            .find({"user_id": user_id})
            .sort("created_at", DESCENDING)
        )

        portfolios = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            portfolios.append(doc)

        return portfolios

    except PyMongoError as exc:
        logger.error("Database error fetching portfolios for user %s: %s", user_id, exc)
        return []
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error fetching portfolios: %s", exc)
        return []


def delete_portfolio(portfolio_id: str, user_id: str) -> dict:
    """
    Delete a portfolio by ID, verifying that the caller owns it.

    The delete filter includes *both* ``_id`` and ``user_id`` so that a
    user can never delete another user's portfolio, even with a valid ID.

    Parameters
    ----------
    portfolio_id : str
        The portfolio's MongoDB ObjectId as a hex string.
    user_id : str
        The requesting user's MongoDB ObjectId string (ownership check).

    Returns
    -------
    dict
        ``{"success": True}`` on success, or
        ``{"success": False, "error": str}`` on failure.
    """
    if not portfolio_id:
        return {"success": False, "error": "portfolio_id is required."}
    if not user_id:
        return {"success": False, "error": "user_id is required."}

    # ---- Validate ObjectId format early ------------------------------------
    try:
        oid = ObjectId(portfolio_id)
    except (InvalidId, Exception):
        return {"success": False, "error": "Invalid portfolio ID format."}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    try:
        result = db[PORTFOLIOS_COLLECTION].delete_one({"_id": oid, "user_id": user_id})

        if result.deleted_count == 0:
            # Either the portfolio doesn't exist or belongs to another user —
            # return the same message in both cases to avoid information leakage.
            return {
                "success": False,
                "error": (
                    "Portfolio not found or you do not have permission to delete it."
                ),
            }

        logger.info("Portfolio deleted — id: %s  user: %s", portfolio_id, user_id)
        return {"success": True}

    except PyMongoError as exc:
        logger.error(
            "Database error deleting portfolio %s for user %s: %s",
            portfolio_id,
            user_id,
            exc,
        )
        return {
            "success": False,
            "error": "A database error occurred while deleting. Please try again.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error deleting portfolio %s: %s", portfolio_id, exc)
        return {
            "success": False,
            "error": "An unexpected error occurred while deleting.",
        }


def update_portfolio(
    portfolio_id: str,
    user_id: str,
    allocations: List[Dict],
    rebalance_settings: Dict = None,
) -> dict:
    """
    Update portfolio allocations and/or rebalance settings.

    Parameters
    ----------
    portfolio_id : str
        MongoDB ObjectId string of the portfolio.
    user_id : str
        MongoDB ObjectId string of the owning user.
    allocations : list[dict]
        New allocations list.
    rebalance_settings : dict, optional
        New rebalance settings. If not provided, the existing settings are kept.

    Returns
    -------
    dict
        {"success": True} on success, or {"success": False, "error": str} on failure.
    """
    if not portfolio_id:
        return {"success": False, "error": "portfolio_id is required."}
    if not user_id:
        return {"success": False, "error": "user_id is required."}

    try:
        oid = ObjectId(portfolio_id)
    except (InvalidId, Exception):
        return {"success": False, "error": "Invalid portfolio ID format."}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    update_fields = {
        "allocations": allocations,
        "n_holdings": len(allocations),
    }

    if rebalance_settings:
        update_fields["rebalance_settings"] = rebalance_settings

    try:
        result = db[PORTFOLIOS_COLLECTION].update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": update_fields}
        )

        if result.matched_count == 0:
            return {
                "success": False,
                "error": "Portfolio not found or you do not have permission to update it.",
            }

        logger.info("Portfolio updated — id: %s  user: %s", portfolio_id, user_id)
        return {"success": True}

    except PyMongoError as exc:
        logger.error("Database error updating portfolio %s for user %s: %s", portfolio_id, user_id, exc)
        return {
            "success": False,
            "error": "A database error occurred while updating. Please try again.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error updating portfolio %s: %s", portfolio_id, exc)
        return {
            "success": False,
            "error": "An unexpected error occurred while updating.",
        }


def get_portfolios_needing_rebalance(user_id: str, days_threshold: int = 90) -> list:
    """
    Get portfolios that haven't been rebalanced within the specified days.

    Parameters
    ----------
    user_id : str
        MongoDB ObjectId string of the user.
    days_threshold : int
        Number of days after which rebalancing is recommended (default 90).

    Returns
    -------
    list[dict]
        List of portfolio documents that need rebalancing.
    """
    if not user_id:
        logger.warning("get_portfolios_needing_rebalance called with empty user_id.")
        return []

    db = get_db()
    if db is None:
        logger.error("Database connection unavailable when checking rebalance.")
        return []

    try:
        from datetime import timedelta
        threshold_date = datetime.now(timezone.utc) - timedelta(days=days_threshold)

        cursor = db[PORTFOLIOS_COLLECTION].find({
            "user_id": user_id,
            "$or": [
                {"rebalance_settings.last_rebalanced": {"$lt": threshold_date}},
                {"rebalance_settings.last_rebalanced": {"$exists": False}},
            ]
        }).sort("created_at", DESCENDING)

        portfolios = []
        for doc in cursor:
            doc["_id"] = str(doc["_id"])
            portfolios.append(doc)

        return portfolios

    except Exception as exc:  # noqa: BLE001
        logger.error("Error checking portfolios needing rebalance for user %s: %s", user_id, exc)
        return []


def update_rebalance_settings(
    portfolio_id: str,
    user_id: str,
    auto_rebalance: bool = None,
    rebalance_frequency: str = None,
    rebalance_threshold: float = None,
) -> dict:
    """
    Update rebalance settings for a portfolio.

    Parameters
    ----------
    portfolio_id : str
        MongoDB ObjectId string of the portfolio.
    user_id : str
        MongoDB ObjectId string of the owning user.
    auto_rebalance : bool, optional
        Whether to auto-rebalance.
    rebalance_frequency : str, optional
        Frequency: "quarterly", "monthly", "manual".
    rebalance_threshold : float, optional
        Threshold as decimal (e.g., 0.05 for 5%).

    Returns
    -------
    dict
        {"success": True} on success, or {"success": False, "error": str} on failure.
    """
    if not portfolio_id:
        return {"success": False, "error": "portfolio_id is required."}
    if not user_id:
        return {"success": False, "error": "user_id is required."}

    try:
        oid = ObjectId(portfolio_id)
    except (InvalidId, Exception):
        return {"success": False, "error": "Invalid portfolio ID format."}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    try:
        existing = db[PORTFOLIOS_COLLECTION].find_one({"_id": oid, "user_id": user_id})
        if not existing:
            return {"success": False, "error": "Portfolio not found."}

        current_settings = existing.get("rebalance_settings", {})
        updated_settings = {
            "auto_rebalance": auto_rebalance if auto_rebalance is not None else current_settings.get("auto_rebalance", False),
            "rebalance_frequency": rebalance_frequency or current_settings.get("rebalance_frequency", "quarterly"),
            "rebalance_threshold": rebalance_threshold if rebalance_threshold is not None else current_settings.get("rebalance_threshold", 0.05),
            "last_rebalanced": current_settings.get("last_rebalanced", datetime.now(timezone.utc)),
        }

        result = db[PORTFOLIOS_COLLECTION].update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": {"rebalance_settings": updated_settings}}
        )

        if result.matched_count == 0:
            return {"success": False, "error": "Portfolio not found or permission denied."}

        logger.info("Rebalance settings updated — id: %s", portfolio_id)
        return {"success": True}

    except Exception as exc:  # noqa: BLE001
        logger.error("Error updating rebalance settings for %s: %s", portfolio_id, exc)
        return {"success": False, "error": str(exc)}


def record_rebalance_history(
    portfolio_id: str,
    user_id: str,
    stocks_replaced: List[Dict],
    stocks_added: List[Dict],
    reason: str = "scheduled",
) -> dict:
    """
    Record a rebalance event in the portfolio history.

    Parameters
    ----------
    portfolio_id : str
        MongoDB ObjectId string of the portfolio.
    user_id : str
        MongoDB ObjectId string of the owning user.
    stocks_replaced : list[dict]
        List of stocks that were replaced.
        Each dict: {"ticker": str, "composite_score": float}
    stocks_added : list[dict]
        List of stocks that were added.
        Each dict: {"ticker": str, "composite_score": float}
    reason : str
        Reason for rebalance: "scheduled" or "risk_profile_change"

    Returns
    -------
    dict
        {"success": True} on success, or {"success": False, "error": str} on failure.
    """
    if not portfolio_id:
        return {"success": False, "error": "portfolio_id is required."}
    if not user_id:
        return {"success": False, "error": "user_id is required."}

    try:
        oid = ObjectId(portfolio_id)
    except (InvalidId, Exception):
        return {"success": False, "error": "Invalid portfolio ID format."}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    try:
        existing = db[PORTFOLIOS_COLLECTION].find_one({"_id": oid, "user_id": user_id})
        if not existing:
            return {"success": False, "error": "Portfolio not found."}

        # Get current history or initialize empty
        current_history = existing.get("rebalance_history", [])
        
        # Create new history entry
        history_entry = {
            "date": datetime.now(timezone.utc),
            "stocks_replaced": stocks_replaced,
            "stocks_added": stocks_added,
            "reason": reason,
        }
        
        # Append to history
        updated_history = current_history + [history_entry]

        result = db[PORTFOLIOS_COLLECTION].update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": {"rebalance_history": updated_history}}
        )

        if result.matched_count == 0:
            return {"success": False, "error": "Portfolio not found or permission denied."}

        logger.info(
            "Rebalance history recorded — id: %s, replaced: %d, added: %d",
            portfolio_id,
            len(stocks_replaced),
            len(stocks_added),
        )
        return {"success": True}

    except Exception as exc:  # noqa: BLE001
        logger.error("Error recording rebalance history for %s: %s", portfolio_id, exc)
        return {"success": False, "error": str(exc)}


def get_rebalance_history(portfolio_id: str, user_id: str) -> dict:
    """
    Get rebalance history for a portfolio.

    Parameters
    ----------
    portfolio_id : str
        MongoDB ObjectId string of the portfolio.
    user_id : str
        MongoDB ObjectId string of the owning user.

    Returns
    -------
    dict
        {"success": True, "history": list} on success, or {"success": False, "error": str}
    """
    if not portfolio_id:
        return {"success": False, "error": "portfolio_id is required.", "history": []}
    if not user_id:
        return {"success": False, "error": "user_id is required.", "history": []}

    try:
        oid = ObjectId(portfolio_id)
    except (InvalidId, Exception):
        return {"success": False, "error": "Invalid portfolio ID format.", "history": []}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable.", "history": []}

    try:
        existing = db[PORTFOLIOS_COLLECTION].find_one({"_id": oid, "user_id": user_id})
        if not existing:
            return {"success": False, "error": "Portfolio not found.", "history": []}

        history = existing.get("rebalance_history", [])
        return {"success": True, "history": history}

    except Exception as exc:  # noqa: BLE001
        logger.error("Error fetching rebalance history for %s: %s", portfolio_id, exc)
        return {"success": False, "error": str(exc), "history": []}
