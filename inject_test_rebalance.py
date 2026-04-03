"""
Script to inject test rebalance history into MongoDB.
Run with: python inject_test_rebalance.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from datetime import datetime, timezone, timedelta
from gui.database import get_db


def inject_test_rebalance_history():
    """Inject a test rebalance history entry for testing."""
    
    db = get_db()
    if db is None:
        print("ERROR: Could not connect to MongoDB")
        return
    
    # Find a portfolio to update
    portfolio = db['portfolios'].find_one({})
    
    if not portfolio:
        print("ERROR: No portfolios found in database")
        return
    
    portfolio_id = portfolio['_id']
    portfolio_name = portfolio.get('name', 'Unnamed')
    
    print(f"Found portfolio: {portfolio_name} (ID: {portfolio_id})")
    
    # Use Oct 1, 2025 as rebalance date - this gives 90 days of data until Dec 30, 2025
    rebalance_date = datetime(2025, 10, 1, tzinfo=timezone.utc)
    
    # Realistic composite scores from output_composite/composite_scores.csv
    test_history = [{
        "date": rebalance_date,
        "stocks_replaced": [
            {"ticker": "VST", "composite_score": 0.541},
            {"ticker": "LITE", "composite_score": 0.489},
            {"ticker": "APP", "composite_score": 0.608},
            {"ticker": "ARES", "composite_score": 0.603},
            {"ticker": "LULU", "composite_score": 0.575},
            {"ticker": "INTC", "composite_score": 0.481},
            {"ticker": "LII", "composite_score": 0.536},
            {"ticker": "EQT", "composite_score": 0.560}
        ],
        "stocks_added": [
            {"ticker": "META", "composite_score": 0.653},
            {"ticker": "COIN", "composite_score": 0.643},
            {"ticker": "NFLX", "composite_score": 0.637},
            {"ticker": "SWKS", "composite_score": 0.643},
            {"ticker": "ANET", "composite_score": 0.625},
            {"ticker": "VMC", "composite_score": 0.625},
            {"ticker": "ZBRA", "composite_score": 0.623},
            {"ticker": "IBKR", "composite_score": 0.621}
        ],
        "reason": "scheduled"
    }]
    
    # Update the portfolio
    result = db['portfolios'].update_one(
        {"_id": portfolio_id},
        {"$set": {"rebalance_history": test_history}}
    )
    
    if result.modified_count > 0:
        end_date = rebalance_date + timedelta(days=90)
        print(f"SUCCESS: Added rebalance history to {portfolio_name}")
        print(f"  - Rebalance date: {rebalance_date.strftime('%Y-%m-%d')}")
        print(f"  - End date for analysis: {end_date.strftime('%Y-%m-%d')}")
        print(f"  - Stocks replaced: 8")
        print(f"  - Stocks added: 8")
        print(f"  - Reason: scheduled")
    else:
        print("ERROR: Could not update portfolio")


if __name__ == "__main__":
    inject_test_rebalance_history()
