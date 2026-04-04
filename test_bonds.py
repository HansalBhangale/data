import sys
from bond_ml.fetch_data import main as fetch_data
from bond_ml.train_model import main as train_model
from bond_ml.predict import main as predict
import pandas as pd
from composite.portfolio_bonds import allocate_portfolio, print_bond_portfolio_report

def main():
    print("=== Testing Bond ML Pipeline ===")
    print("1. Fetching Data...")
    fetch_data()
    print("\n2. Training Model...")
    train_model()
    print("\n3. Generating Predictions...")
    predict()
    
    print("\n4. Testing Portfolio Allocation...")
    try:
        bond_scores_df = pd.read_csv('output/bond_scores.csv')
        bond_scores = bond_scores_df.set_index('ticker')['bond_score']
    except Exception as e:
        print(f"Failed to load bond scores: {e}")
        return
        
    # Dummy composite scores for testing since we just want to verify bond integration
    import numpy as np
    dummy_stocks = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'META', 'TSLA', 'NVDA', 'JPM', 'V', 'JNJ', 'WMT', 'UNH']
    composite_scores = pd.Series(np.random.uniform(50, 95, len(dummy_stocks)), index=dummy_stocks)
    
    for risk_score in [15, 40, 65, 90]:
        print(f"\n--- Testing Allocation for Risk Score: {risk_score} ---")
        portfolio = allocate_portfolio(risk_score, composite_scores, bond_scores, capital=100000)
        print_bond_portfolio_report(portfolio)

if __name__ == "__main__":
    main()
