"""
Rebalance Performance Test Script

Analyzes whether rebalancing adds value by comparing performance of
replaced stocks vs newly added stocks over subsequent quarters.

Usage: python test_rebalance_performance.py

Requirements:
- Must have portfolios with rebalance_history in MongoDB
- daily_prices_all.csv for price data

This script:
1. Loads all portfolios from MongoDB
2. For each rebalance event:
   - Gets replaced stocks and added stocks
   - Fetches their prices from daily_prices_all.csv
   - Calculates return over subsequent quarter (90 days)
3. Compares: new_stocks_return - old_stocks_return
4. Outputs report
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from gui.database import get_db


def load_daily_prices():
    """Load daily prices from CSV."""
    path = Path("daily_prices_all.csv")
    if not path.exists():
        print("ERROR: daily_prices_all.csv not found")
        return pd.DataFrame()
    
    df = pd.read_csv(path, parse_dates=["date"])
    return df


def calculate_stock_return(prices_df, ticker, start_date, end_date):
    """
    Calculate return for a single stock over a period.
    
    Parameters
    ----------
    prices_df : pd.DataFrame
        Daily prices data
    ticker : str
        Stock ticker
    start_date : datetime
        Start date for calculation
    end_date : datetime
        End date for calculation
    
    Returns
    -------
    float
        Return as decimal (e.g., 0.15 = 15% return), or None if insufficient data
    """
    ticker_prices = prices_df[
        (prices_df['ticker'].str.upper() == ticker.upper()) &
        (prices_df['date'] >= start_date) &
        (prices_df['date'] <= end_date)
    ].sort_values('date')
    
    if len(ticker_prices) < 10:  # Need at least 10 days of data
        return None
    
    start_price = ticker_prices.iloc[0]['adj_close']
    end_price = ticker_prices.iloc[-1]['adj_close']
    
    if start_price <= 0:
        return None
    
    return (end_price - start_price) / start_price


def analyze_rebalance_event(event, prices_df, quarter_days=90):
    """
    Analyze a single rebalance event.
    
    Returns dict with performance metrics, or None if insufficient data.
    """
    # Get the rebalance date
    rebalance_date = event.get('date')
    if isinstance(rebalance_date, str):
        rebalance_date = datetime.fromisoformat(rebalance_date.replace('Z', '+00:00'))
    
    # Calculate end date (90 days after rebalance)
    end_date = rebalance_date + timedelta(days=quarter_days)
    
    # Get stocks
    replaced = event.get('stocks_replaced', [])
    added = event.get('stocks_added', [])
    
    # Calculate returns for replaced stocks
    replaced_returns = []
    for stock in replaced:
        ticker = stock.get('ticker')
        ret = calculate_stock_return(prices_df, ticker, rebalance_date, end_date)
        if ret is not None:
            replaced_returns.append(ret)
    
    # Calculate returns for added stocks
    added_returns = []
    for stock in added:
        ticker = stock.get('ticker')
        ret = calculate_stock_return(prices_df, ticker, rebalance_date, end_date)
        if ret is not None:
            added_returns.append(ret)
    
    if not replaced_returns or not added_returns:
        return None
    
    replaced_avg = np.mean(replaced_returns)
    added_avg = np.mean(added_returns)
    outperformance = added_avg - replaced_avg
    
    return {
        'date': rebalance_date,
        'n_replaced': len(replaced),
        'n_added': len(added),
        'replaced_returns': replaced_returns,
        'added_returns': added_returns,
        'replaced_avg': replaced_avg,
        'added_avg': added_avg,
        'outperformance': outperformance,
        'reason': event.get('reason', 'unknown'),
    }


def run_analysis():
    """Main analysis function."""
    print("=" * 60)
    print("REBALANCE PERFORMANCE ANALYSIS")
    print("=" * 60)
    print()
    
    # Load price data
    print("Loading daily prices...")
    prices_df = load_daily_prices()
    if prices_df.empty:
        print("ERROR: No price data available")
        return
    
    print(f"Loaded {len(prices_df)} price records")
    print()
    
    # Connect to database
    db = get_db()
    if db is None:
        print("ERROR: Could not connect to MongoDB")
        return
    
    # Get all portfolios with rebalance_history
    print("Fetching portfolios with rebalance history...")
    portfolios = list(db['portfolios'].find({"rebalance_history": {"$exists": True, "$ne": []}}))
    
    if not portfolios:
        print("ERROR: No portfolios with rebalance history found")
        print("Please create portfolios and perform at least one rebalance")
        return
    
    print(f"Found {len(portfolios)} portfolios with rebalance history")
    print()
    
    # Analyze each portfolio
    all_results = []
    
    for portfolio in portfolios:
        portfolio_id = str(portfolio.get('_id', 'unknown'))
        portfolio_name = portfolio.get('name', 'Unnamed')
        risk_score = portfolio.get('risk_score', 0)
        
        print(f"Analyzing: {portfolio_name} (Risk: {risk_score})")
        
        history = portfolio.get('rebalance_history', [])
        
        for i, event in enumerate(history):
            result = analyze_rebalance_event(event, prices_df)
            
            if result:
                result['portfolio_id'] = portfolio_id
                result['portfolio_name'] = portfolio_name
                all_results.append(result)
                
                print(f"  Event {i+1}: {result['date'].strftime('%Y-%m-%d')}")
                print(f"    Replaced: {result['n_replaced']} stocks, Avg return: {result['replaced_avg']*100:.1f}%")
                print(f"    Added:    {result['n_added']} stocks, Avg return: {result['added_avg']*100:.1f}%")
                print(f"    Outperformance: {result['outperformance']*100:+.1f}%")
                print()
            else:
                print(f"  Event {i+1}: Insufficient data for analysis")
                print()
    
    # Summary statistics
    if not all_results:
        print("ERROR: No rebalance events could be analyzed")
        return
    
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    n_events = len(all_results)
    wins = sum(1 for r in all_results if r['outperformance'] > 0)
    losses = sum(1 for r in all_results if r['outperformance'] < 0)
    ties = n_events - wins - losses
    
    avg_outperformance = np.mean([r['outperformance'] for r in all_results])
    total_replaced = sum(r['n_replaced'] for r in all_results)
    total_added = sum(r['n_added'] for r in all_results)
    
    print(f"Total rebalance events analyzed: {n_events}")
    print(f"Win rate: {wins/n_events*100:.1f}% ({wins} wins, {losses} losses, {ties} ties)")
    print(f"Average outperformance: {avg_outperformance*100:+.2f}%")
    print(f"Total stocks replaced: {total_replaced}")
    print(f"Total stocks added: {total_added}")
    print()
    
    # Breakdown by reason
    scheduled = [r for r in all_results if r['reason'] == 'scheduled']
    risk_change = [r for r in all_results if r['reason'] == 'risk_profile_change']
    
    if scheduled:
        scheduled_avg = np.mean([r['outperformance'] for r in scheduled])
        print(f"Scheduled rebalances: {len(scheduled)}, Avg: {scheduled_avg*100:+.2f}%")
    
    if risk_change:
        risk_change_avg = np.mean([r['outperformance'] for r in risk_change])
        print(f"Risk profile changes: {len(risk_change)}, Avg: {risk_change_avg*100:+.2f}%")
    
    print()
    
    # Verdict
    if avg_outperformance > 0.02:
        print("[VERDICT] REBALANCING ADDS VALUE")
        print("New stocks consistently outperform replaced stocks.")
    elif avg_outperformance > -0.02:
        print("[VERDICT] REBALANCING IS NEUTRAL")
        print("New stocks perform similarly to replaced stocks.")
    else:
        print("[VERDICT] REBALANCING MAY HURT PERFORMANCE")
        print("Consider reducing rebalancing frequency.")
    
    print()
    print("=" * 60)


if __name__ == "__main__":
    run_analysis()
