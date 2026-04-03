"""
MongoDB Connection Module

Singleton pattern for MongoDB database access.
Reads MONGO_URI from environment variables and exposes a get_db() function
that returns the connected database object.
"""

import logging
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env from the gui/ directory (one level above this file's package folder)
load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

from pymongo import MongoClient
from pymongo.database import Database
from pymongo.errors import (
    ConfigurationError,
    ConnectionFailure,
    ServerSelectionTimeoutError,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Module-level singletons — one client, one db reference per process
# ---------------------------------------------------------------------------
_client: Optional[MongoClient] = None
_db: Optional[Database] = None

DB_NAME = "portfolio_app"


def get_db() -> Optional[Database]:
    """
    Return the MongoDB database singleton.

    On the first call the function reads ``MONGO_URI`` from the environment,
    establishes a MongoClient, verifies the connection with a *ping*, and
    caches both the client and the database object for all subsequent calls.

    Returns
    -------
    Optional[pymongo.database.Database]
        The ``portfolio_app`` database object, or ``None`` when the
        connection cannot be established (error is logged, no exception
        is raised to the caller).
    """
    global _client, _db

    # Fast-path: already connected.
    if _db is not None:
        return _db

    mongo_uri = os.getenv("MONGO_URI")
    if not mongo_uri:
        logger.error(
            "MONGO_URI environment variable is not set. "
            "Database features will be unavailable."
        )
        return None

    try:
        client = MongoClient(
            mongo_uri,
            serverSelectionTimeoutMS=5_000,  # 5 s connection timeout
            connectTimeoutMS=5_000,
            socketTimeoutMS=10_000,
        )

        # Verify the connection is actually reachable before caching.
        client.admin.command("ping")

        _client = client
        _db = _client[DB_NAME]
        logger.info("Connected to MongoDB — database: '%s'", DB_NAME)
        return _db

    except ServerSelectionTimeoutError as exc:
        logger.error(
            "MongoDB server selection timed out. "
            "Check that MONGO_URI is correct and the host is reachable. Error: %s",
            exc,
        )
    except ConnectionFailure as exc:
        logger.error("MongoDB connection failed: %s", exc)
    except ConfigurationError as exc:
        logger.error("MongoDB configuration error (check MONGO_URI format): %s", exc)
    except Exception as exc:  # noqa: BLE001
        logger.error("Unexpected error while connecting to MongoDB: %s", exc)

    # Ensure we don't cache a broken client.
    _client = None
    _db = None
    return None


def close_db() -> None:
    """
    Close the MongoDB client connection and reset the singleton state.

    Useful for graceful shutdown or when reconnecting with a new URI
    (e.g. during testing).
    """
    global _client, _db

    if _client is not None:
        try:
            _client.close()
            logger.info("MongoDB connection closed.")
        except Exception as exc:  # noqa: BLE001
            logger.warning("Error while closing MongoDB connection: %s", exc)
        finally:
            _client = None
            _db = None
