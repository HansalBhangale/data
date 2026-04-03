"""
User Authentication Module

Handles user registration and login for the portfolio app.
Passwords are hashed with bcrypt — plain-text passwords are never stored.
Users are persisted in the MongoDB 'users' collection.

Schema
------
{
    email         : str   (unique, lowercase)
    password_hash : bytes (bcrypt hash)
    name          : str
    created_at    : datetime (UTC)
}
"""

import logging
from datetime import datetime, timezone

import bcrypt
from pymongo.errors import DuplicateKeyError, PyMongoError

from .db import get_db

logger = logging.getLogger(__name__)

USERS_COLLECTION = "users"


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _ensure_indexes() -> None:
    """
    Create the unique index on 'email' if it does not already exist.

    Called lazily before any write so the index is always present without
    requiring a separate migration step.
    """
    db = get_db()
    if db is None:
        return
    try:
        db[USERS_COLLECTION].create_index("email", unique=True)
    except PyMongoError as exc:
        logger.warning("Could not create users.email index: %s", exc)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def register_user(email: str, password: str, name: str) -> dict:
    """
    Register a new user account.

    The email is normalised to lowercase before storage.  The password is
    hashed with ``bcrypt`` using a freshly generated salt; the plain-text
    password is never written to the database.

    Parameters
    ----------
    email : str
        The user's email address.  Must be unique across all accounts.
    password : str
        Plain-text password chosen by the user.
    name : str
        Display name for the user.

    Returns
    -------
    dict
        On success: ``{"success": True, "user_id": str}``
        On failure: ``{"success": False, "error": str}``
    """
    # ---- Basic input validation ----------------------------------------
    if not email or not email.strip():
        return {"success": False, "error": "Email address is required."}
    if not password:
        return {"success": False, "error": "Password is required."}
    if not name or not name.strip():
        return {"success": False, "error": "Name is required."}
    if len(password) < 6:
        return {"success": False, "error": "Password must be at least 6 characters."}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    email = email.strip().lower()
    name = name.strip()

    # Ensure the unique index exists before attempting the insert.
    _ensure_indexes()

    try:
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

        user_doc = {
            "email": email,
            "password_hash": password_hash,
            "name": name,
            "created_at": datetime.now(timezone.utc),
        }

        result = db[USERS_COLLECTION].insert_one(user_doc)
        logger.info("New user registered: %s", email)
        return {"success": True, "user_id": str(result.inserted_id)}

    except DuplicateKeyError:
        return {"success": False, "error": "An account with that email already exists."}
    except PyMongoError as exc:
        logger.error("Database error during registration for %s: %s", email, exc)
        return {
            "success": False,
            "error": "A database error occurred. Please try again.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during registration: %s", exc)
        return {"success": False, "error": "An unexpected error occurred."}


def login_user(email: str, password: str) -> dict:
    """
    Authenticate a user by email and password.

    The supplied plain-text password is compared against the stored bcrypt
    hash.  A deliberately generic error message is returned for both
    "email not found" and "wrong password" cases to avoid account
    enumeration.

    Parameters
    ----------
    email : str
        The user's email address.
    password : str
        Plain-text password to verify.

    Returns
    -------
    dict
        On success: ``{"success": True, "user_id": str, "name": str, "email": str}``
        On failure: ``{"success": False, "error": str}``
    """
    # ---- Basic input validation ----------------------------------------
    if not email or not email.strip():
        return {"success": False, "error": "Email address is required."}
    if not password:
        return {"success": False, "error": "Password is required."}

    db = get_db()
    if db is None:
        return {"success": False, "error": "Database connection unavailable."}

    email = email.strip().lower()

    try:
        user = db[USERS_COLLECTION].find_one({"email": email})

        # Use the same error message for missing user vs wrong password to
        # prevent account enumeration attacks.
        if user is None:
            return {"success": False, "error": "Invalid email or password."}

        stored_hash = user.get("password_hash")
        if stored_hash is None:
            logger.error("User document for %s is missing password_hash field.", email)
            return {
                "success": False,
                "error": "Account data is corrupted. Please contact support.",
            }

        # bcrypt.checkpw expects bytes on both sides.
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return {"success": False, "error": "Invalid email or password."}

        logger.info("User authenticated: %s", email)
        return {
            "success": True,
            "user_id": str(user["_id"]),
            "name": user.get("name", ""),
            "email": user["email"],
        }

    except PyMongoError as exc:
        logger.error("Database error during login for %s: %s", email, exc)
        return {
            "success": False,
            "error": "A database error occurred. Please try again.",
        }
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error during login: %s", exc)
        return {"success": False, "error": "An unexpected error occurred."}
