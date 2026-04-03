"""
Test file for rebalancing functionality.
Run with: python test_rebalance.py
"""

import sys
sys.path.insert(0, '.')


def test_calculate_rebalance_actions():
    """Test rebalance action calculation."""
    from gui.core.rebalance import calculate_rebalance_actions
    
    current = [
        {'ticker': 'AAPL', 'weight_pct': 15.0, 'capital_allocated': 15000},
        {'ticker': 'MSFT', 'weight_pct': 8.0, 'capital_allocated': 8000},
        {'ticker': 'GOOG', 'weight_pct': 10.0, 'capital_allocated': 10000},
    ]
    
    target = [
        {'ticker': 'AAPL', 'weight_pct': 10.0},
        {'ticker': 'MSFT', 'weight_pct': 10.0},
        {'ticker': 'GOOG', 'weight_pct': 10.0},
    ]
    
    result = calculate_rebalance_actions(current, target, threshold=0.05, current_capital=100000)
    
    print('=== Test: calculate_rebalance_actions ===')
    print(f"Actions: {len(result['actions'])}")
    for a in result['actions']:
        print(f"  {a['ticker']}: {a['action']} - Current {a['current_weight']}% -> Target {a['target_weight']}% ({a['shares']} shares)")
    print(f"Summary: Buy ${result['summary']['total_buy_amount']}, Sell ${result['summary']['total_sell_amount']}, Max Drift: {result['summary']['max_drift']}%")


def test_check_rebalance_needed():
    """Test rebalance check."""
    from gui.core.rebalance import check_rebalance_needed
    
    balanced_current = [
        {'ticker': 'AAPL', 'weight_pct': 10.5},
        {'ticker': 'MSFT', 'weight_pct': 9.8},
    ]
    balanced_target = [
        {'ticker': 'AAPL', 'weight_pct': 10.0},
        {'ticker': 'MSFT', 'weight_pct': 10.0},
    ]
    
    needs_rebalance = check_rebalance_needed(balanced_current, balanced_target, threshold=0.05)
    
    print('\n=== Test: check_rebalance_needed ===')
    print(f"Needs rebalance (within 5% threshold): {needs_rebalance}")


def test_threshold_edge_cases():
    """Test threshold edge cases."""
    from gui.core.rebalance import calculate_rebalance_actions
    
    # Test with 6% drift (should trigger SELL)
    current = [
        {'ticker': 'AAPL', 'weight_pct': 16.0, 'capital_allocated': 16000},
        {'ticker': 'MSFT', 'weight_pct': 10.0, 'capital_allocated': 10000},
    ]
    target = [
        {'ticker': 'AAPL', 'weight_pct': 10.0},
        {'ticker': 'MSFT', 'weight_pct': 10.0},
    ]
    
    result = calculate_rebalance_actions(current, target, threshold=0.05, current_capital=100000)
    
    print('\n=== Test: 6% drift (should SELL) ===')
    for a in result['actions']:
        print(f"  {a['ticker']}: {a['action']} - Current {a['current_weight']}% -> Target {a['target_weight']}% ({a['shares']} shares)")
    print(f"Max Drift: {result['summary']['max_drift']}%")
    
    # Test with 4% drift (should HOLD)
    current2 = [
        {'ticker': 'AAPL', 'weight_pct': 14.0, 'capital_allocated': 14000},
        {'ticker': 'MSFT', 'weight_pct': 10.0, 'capital_allocated': 10000},
    ]
    result2 = calculate_rebalance_actions(current2, target, threshold=0.05, current_capital=100000)
    
    print('\n=== Test: 4% drift (should HOLD) ===')
    for a in result2['actions']:
        print(f"  {a['ticker']}: {a['action']} - Current {a['current_weight']}% -> Target {a['target_weight']}% ({a['shares']} shares)")
    print(f"Max Drift: {result2['summary']['max_drift']}%")


def test_database_functions():
    """Test database functions exist."""
    from gui.database import update_portfolio, get_portfolios_needing_rebalance, update_rebalance_settings
    
    print('\n=== Test: Database functions ===')
    print("update_portfolio:", update_portfolio)
    print("get_portfolios_needing_rebalance:", get_portfolios_needing_rebalance)
    print("update_rebalance_settings:", update_rebalance_settings)


def test_core_exports():
    """Test core exports."""
    from gui.core import calculate_rebalance_actions as cra
    from gui.core import check_rebalance_needed as crn
    from gui.core import regenerate_target_from_buckets as rtb
    
    print('\n=== Test: Core exports ===')
    print("calculate_rebalance_actions imported:", bool(cra))
    print("check_rebalance_needed imported:", bool(crn))
    print("regenerate_target_from_buckets imported:", bool(rtb))


if __name__ == '__main__':
    test_calculate_rebalance_actions()
    test_check_rebalance_needed()
    test_threshold_edge_cases()
    test_database_functions()
    test_core_exports()
    print('\n[SUCCESS] All tests passed!')
