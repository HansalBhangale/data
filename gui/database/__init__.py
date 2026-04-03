"""
Database Package

Public interface for all database operations.

Exports
-------
get_db          — MongoDB database singleton (db.py)
register_user   — Create a new user account (auth.py)
login_user      — Authenticate an existing user (auth.py)
save_portfolio  — Persist a generated portfolio (portfolio_db.py)
get_user_portfolios — Retrieve all portfolios for a user (portfolio_db.py)
delete_portfolio    — Remove a portfolio by ID with ownership check (portfolio_db.py)
"""

from .auth import login_user, register_user
from .db import get_db
from .portfolio_db import delete_portfolio, get_user_portfolios, save_portfolio

__all__ = [
    "get_db",
    "register_user",
    "login_user",
    "save_portfolio",
    "get_user_portfolios",
    "delete_portfolio",
]
