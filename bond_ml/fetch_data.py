import os
import pandas as pd
import numpy as np
import yfinance as yf
from fredapi import Fred
from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

FRED_API_KEY = os.environ.get('FRED_API_KEY', 'your_free_api_key')

BOND_ETFS = {
    # Government Bonds (14) - removed ARCA
    'SHY':   {'duration': 1.9, 'credit_quality': 5, 'category': 'govt_short'},
    'IEF':   {'duration': 7.5, 'credit_quality': 5, 'category': 'govt_intermediate'},
    'TLT':   {'duration': 17.0, 'credit_quality': 5, 'category': 'govt_long'},
    'SCHO':  {'duration': 2.0, 'credit_quality': 5, 'category': 'govt_short'},
    'SCHR':  {'duration': 5.0, 'credit_quality': 5, 'category': 'govt_intermediate'},
    'VGSH':  {'duration': 1.8, 'credit_quality': 5, 'category': 'govt_short'},
    'VGIT':  {'duration': 5.5, 'credit_quality': 5, 'category': 'govt_intermediate'},
    'VGLT':  {'duration': 15.0, 'credit_quality': 5, 'category': 'govt_long'},
    'GOVT':  {'duration': 8.0, 'credit_quality': 5, 'category': 'govt_all'},
    'BIL':   {'duration': 0.2, 'credit_quality': 5, 'category': 't_bill'},
    'SHV':   {'duration': 0.5, 'credit_quality': 5, 'category': 't_bill'},
    'EDV':   {'duration': 20.0, 'credit_quality': 5, 'category': 'govt_long_extended'},
    'ZROZ':  {'duration': 25.0, 'credit_quality': 5, 'category': 'govt_long_zero'},
    'SPTL':  {'duration': 16.0, 'credit_quality': 5, 'category': 'govt_long'},
    
    # Inflation Protected (5)
    'TIP':   {'duration': 7.0, 'credit_quality': 5, 'category': 'tips'},
    'SCHP':  {'duration': 7.0, 'credit_quality': 5, 'category': 'tips'},
    'VTIP':  {'duration': 3.0, 'credit_quality': 5, 'category': 'tips_short'},
    'STIP':  {'duration': 2.5, 'credit_quality': 5, 'category': 'tips_short'},
    'LTPZ':  {'duration': 15.0, 'credit_quality': 5, 'category': 'tips_long'},
    
    # Total / Broad Bond Market (5)
    'AGG':   {'duration': 6.0, 'credit_quality': 4, 'category': 'broad'},
    'BND':   {'duration': 6.5, 'credit_quality': 4, 'category': 'broad'},
    'BOND':  {'duration': 5.5, 'credit_quality': 4, 'category': 'broad_active'},
    'GBF':   {'duration': 6.0, 'credit_quality': 4, 'category': 'govt_credit'},
    'IUSB':  {'duration': 6.0, 'credit_quality': 4, 'category': 'broad_core'},
    
    # Investment Grade Corporate (9)
    'LQD':   {'duration': 8.5, 'credit_quality': 3, 'category': 'ig_corp'},
    'VCIT':  {'duration': 6.5, 'credit_quality': 3, 'category': 'ig_corp_intermediate'},
    'VCSH':  {'duration': 3.0, 'credit_quality': 3, 'category': 'ig_corp_short'},
    'IGIB':  {'duration': 6.0, 'credit_quality': 3, 'category': 'ig_corp_intermediate'},
    'IGSB':  {'duration': 3.0, 'credit_quality': 3, 'category': 'ig_corp_short'},
    'SPIB':  {'duration': 6.5, 'credit_quality': 3, 'category': 'ig_corp_sp'},
    'SPSB':  {'duration': 3.0, 'credit_quality': 3, 'category': 'ig_corp_sp_short'},
    'USIG':  {'duration': 6.5, 'credit_quality': 3, 'category': 'ig_corp_us'},
    'QLTA':  {'duration': 7.0, 'credit_quality': 3, 'category': 'ig_corp_quality'},
    
    # High Yield / Junk Bonds (8)
    'HYG':   {'duration': 3.5, 'credit_quality': 1, 'category': 'high_yield'},
    'JNK':   {'duration': 4.0, 'credit_quality': 1, 'category': 'high_yield'},
    'FALN':  {'duration': 4.0, 'credit_quality': 1, 'category': 'fallen_angel'},
    'ANGL':  {'duration': 4.5, 'credit_quality': 1, 'category': 'fallen_angel'},
    'USHY':  {'duration': 4.0, 'credit_quality': 1, 'category': 'high_yield'},
    'SJNK':  {'duration': 2.5, 'credit_quality': 1, 'category': 'high_yield_short'},
    'HYDB':  {'duration': 4.5, 'credit_quality': 1, 'category': 'high_yield'},
    'HYLB':  {'duration': 4.0, 'credit_quality': 1, 'category': 'high_yield_low_beta'},
    
    # Dividend / Income Focus (3)
    'PFF':   {'duration': 4.0, 'credit_quality': 2, 'category': 'preferred'},
    'PFFD':  {'duration': 4.0, 'credit_quality': 2, 'category': 'preferred'},
    'JEPI':  {'duration': 3.0, 'credit_quality': 2, 'category': 'equity_income'},
    
    # International / Global Bonds (6)
    'BNDX':  {'duration': 7.0, 'credit_quality': 4, 'category': 'intl_bond'},
    'BWX':   {'duration': 8.0, 'credit_quality': 4, 'category': 'intl_treasury'},
    'EMB':   {'duration': 8.5, 'credit_quality': 3, 'category': 'emerging'},
    'VWOB':  {'duration': 8.0, 'credit_quality': 3, 'category': 'emerging_vanguard'},
    'PCY':   {'duration': 8.0, 'credit_quality': 3, 'category': 'emerging_sov'},
    'IGOV':  {'duration': 8.0, 'credit_quality': 4, 'category': 'intl_govt'},
    'IAGG':  {'duration': 7.5, 'credit_quality': 4, 'category': 'intl_agg'},
    
    # Sector / Specialty (9)
    'MBB':   {'duration': 5.0, 'credit_quality': 4, 'category': 'mbs'},
    'VMBS':  {'duration': 5.0, 'credit_quality': 4, 'category': 'mbs'},
    'MUB':   {'duration': 6.0, 'credit_quality': 4, 'category': 'muni'},
    'HYD':   {'duration': 8.0, 'credit_quality': 2, 'category': 'muni_high_yield'},
    'VTEB':  {'duration': 5.5, 'credit_quality': 4, 'category': 'muni_vanguard'},
    'SUB':   {'duration': 2.0, 'credit_quality': 4, 'category': 'muni_short'},
    'NEAR':  {'duration': 2.0, 'credit_quality': 4, 'category': 'short_bond_active'},
    'FLOT':  {'duration': 0.5, 'credit_quality': 3, 'category': 'floating'},
    'FLRN':  {'duration': 0.5, 'credit_quality': 4, 'category': 'floating_ig'},
    'USFR':  {'duration': 0.2, 'credit_quality': 5, 'category': 'floating_treasury'},
    
    # Multi-Asset / Conservative Allocation (3)
    'AOK':   {'duration': 4.0, 'credit_quality': 4, 'category': 'conservative'},
    'AOM':   {'duration': 5.0, 'credit_quality': 4, 'category': 'moderate'},
    'ARCA':  {'duration': 3.5, 'credit_quality': 4, 'category': 'conservative_income'},
}


def fetch_macro_features(fred):
    series = {
        'treasury_10y':       'GS10',
        'treasury_2y':        'GS2', 
        'yield_curve_slope':  'T10Y2Y',
        'fed_funds_rate':     'FEDFUNDS',
        'inflation_cpi':      'CPIAUCSL',
        'ig_credit_spread':   'BAMLC0A0CM',
        'hy_credit_spread':   'BAMLH0A0HYM2',
        'inflation_breakeven':'T10YIE',
        'unemployment':       'UNRATE',
    }
    
    print("Fetching macro data from FRED...")
    dfs = []
    for name, code in series.items():
        s = fred.get_series(code, observation_start='2000-01-01')
        s.name = name
        dfs.append(s)
        
    macro_df = pd.concat(dfs, axis=1)
    
    # Add rate of change features
    macro_df['yield_curve_change'] = macro_df['yield_curve_slope'].diff(1).fillna(0)
    macro_df['fed_rate_change'] = macro_df['fed_funds_rate'].diff(1).fillna(0)
    macro_df['inflation_yoy_change'] = macro_df['inflation_cpi'].pct_change(4).fillna(0)
    macro_df['unemployment_change'] = macro_df['unemployment'].diff(1).fillna(0)
    macro_df['treasury_10y_change'] = macro_df['treasury_10y'].diff(1).fillna(0)
    macro_df['ig_spread_change'] = macro_df['ig_credit_spread'].diff(1).fillna(0)
    macro_df['hy_spread_change'] = macro_df['hy_credit_spread'].diff(1).fillna(0)
    
    # Add rate direction explicit features
    macro_df['rate_direction'] = np.sign(macro_df['fed_funds_rate'].diff(4)).fillna(0)
    
    # Rate regime: easing (-1), neutral (0), tightening (+1)
    rate_change_4q = macro_df['fed_funds_rate'].diff(4)
    macro_df['rate_regime'] = pd.cut(
        rate_change_4q,
        bins=[-np.inf, -0.25, 0.25, np.inf],
        labels=[-1, 0, 1]
    ).astype(float).fillna(0)
    
    # Yield curve regime: steepening (-1), flat (0), flattening (1)
    yc_change = macro_df['yield_curve_slope'].diff(4)
    macro_df['yc_regime'] = pd.cut(
        yc_change,
        bins=[-np.inf, -0.2, 0.2, np.inf],
        labels=[-1, 0, 1]
    ).astype(float).fillna(0)
    
    return macro_df.resample('QE').last()


def fetch_bond_etf_prices(tickers):
    print(f"Fetching ETF prices from Yahoo Finance: {len(tickers)} ETFs...")
    
    all_prices = []
    batch_size = 20
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i+batch_size]
        try:
            data = yf.download(batch, start='2000-01-01', progress=False)
            
            if isinstance(data.columns, pd.MultiIndex):
                price_cols = [c for c in ['Adj Close', 'Close'] if c in data.columns.get_level_values(0)]
                if price_cols:
                    prices = data.xs(price_cols[0], level=0, axis=1)
                else:
                    prices = data
            elif 'Adj Close' in data.columns:
                prices = data['Adj Close']
            elif 'Close' in data.columns:
                prices = data['Close']
            else:
                prices = data
                
            if not prices.empty:
                all_prices.append(prices)
                valid_batch = [t for t in batch if t in prices.columns and prices[t].notna().sum() > 10]
                print(f"  Batch {i//batch_size + 1}: {len(valid_batch)}/{len(batch)} valid")
        except Exception as e:
            print(f"  Batch {i//batch_size + 1} failed: {e}")
    
    if all_prices:
        combined = pd.concat(all_prices, axis=1)
        return combined
    return pd.DataFrame()


def build_bond_feature_matrix():
    if FRED_API_KEY == 'your_free_api_key':
        print("WARNING: Using dummy FRED_API_KEY. Please set FRED_API_KEY environment variable.")
    
    try:
        fred = Fred(api_key=FRED_API_KEY)
        macro = fetch_macro_features(fred)
    except Exception as e:
        print(f"Failed to fetch FRED data: {e}")
        print("Falling back to dummy macro data for pipeline testing...")
        macro = pd.DataFrame(index=pd.date_range(start='2000-01-01', end='2024-01-01', freq='QE'))
        for col in ['treasury_10y', 'treasury_2y', 'yield_curve_slope', 'fed_funds_rate', 
                    'inflation_cpi', 'ig_credit_spread', 'hy_credit_spread', 
                    'inflation_breakeven', 'unemployment', 'yield_curve_change', 
                    'fed_rate_change', 'inflation_yoy_change', 'unemployment_change',
                    'treasury_10y_change', 'ig_spread_change', 'hy_spread_change',
                    'rate_direction', 'rate_regime', 'yc_regime']:
            macro[col] = 0.0

    tickers = list(BOND_ETFS.keys())
    prices = fetch_bond_etf_prices(tickers).resample('QE').last()
    
    valid_tickers = [t for t in tickers if t in prices.columns and prices[t].notna().sum() > 10]
    print(f"Valid tickers with sufficient data: {len(valid_tickers)}")
    
    if len(valid_tickers) == 0:
        print("ERROR: No valid tickers found. Check ETF symbols.")
        return pd.DataFrame()
    
    # Correct forward 1-year return calculation
    fwd_returns = prices.shift(-4) / prices - 1
    
    # Multi-period momentum
    momentum_1y = prices / prices.shift(4) - 1
    momentum_6m = prices / prices.shift(2) - 1
    momentum_3m = prices / prices.shift(1) - 1
    
    # Daily prices for volatility
    if len(valid_tickers) > 0:
        daily_prices = fetch_bond_etf_prices(valid_tickers)
        vol_60d = daily_prices.pct_change().rolling(60).std() * (252**0.5)
        vol_20d = daily_prices.pct_change().rolling(20).std() * (252**0.5)
        vol_ratio = vol_20d / vol_60d
        
        vol_60d_q = vol_60d.resample('QE').last()
        vol_20d_q = vol_20d.resample('QE').last()
        vol_ratio_q = vol_ratio.resample('QE').last()
    else:
        vol_60d_q = pd.DataFrame()
        vol_20d_q = pd.DataFrame()
        vol_ratio_q = pd.DataFrame()
    
    # Build long format feature matrix
    df_long = []
    for ticker in valid_tickers:
        if ticker not in BOND_ETFS:
            continue
            
        etf_info = BOND_ETFS[ticker]
        df_ticker = pd.DataFrame(index=prices.index)
        df_ticker['ticker'] = ticker
        
        # Static ETF features
        df_ticker['duration'] = etf_info['duration']
        df_ticker['credit_quality'] = etf_info['credit_quality']
        
        # Momentum features
        df_ticker['momentum_1y'] = momentum_1y[ticker]
        df_ticker['momentum_6m'] = momentum_6m[ticker]
        df_ticker['momentum_3m'] = momentum_3m[ticker]
        
        # Volatility features
        if not vol_60d_q.empty and ticker in vol_60d_q.columns:
            df_ticker['volatility_60d'] = vol_60d_q[ticker]
            df_ticker['volatility_20d'] = vol_20d_q[ticker]
            df_ticker['vol_ratio'] = vol_ratio_q[ticker]
        else:
            df_ticker['volatility_60d'] = np.nan
            df_ticker['volatility_20d'] = np.nan
            df_ticker['vol_ratio'] = np.nan
        
        # Target (forward 1-year return)
        df_ticker['fwd_total_return_1y'] = fwd_returns[ticker]
        
        # Add macro features
        df_ticker = df_ticker.join(macro, how='left')
        
        df_long.append(df_ticker)
    
    feature_matrix = pd.concat(df_long)
    feature_matrix = feature_matrix.dropna(subset=['fwd_total_return_1y'])
    
    print(f"Feature matrix shape: {feature_matrix.shape}")
    print(f"Features: {list(feature_matrix.columns)}")
    
    return feature_matrix


def main():
    print("Building Bond ML Feature Matrix with 62 ETFs...")
    df = build_bond_feature_matrix()
    
    if df.empty:
        print("ERROR: No data fetched. Exiting.")
        return
    
    os.makedirs('checkpoints', exist_ok=True)
    
    print("\nFeature Matrix Sample:")
    print(df.head())
    
    df.to_csv('checkpoints/bond_features.csv')
    df.to_parquet('checkpoints/bond_features.parquet')
    
    print("\nData saved to checkpoints/bond_features.csv and .parquet")
    print(f"Shape: {df.shape}")
    print(f"Unique ETFs: {df['ticker'].nunique()}")


if __name__ == '__main__':
    main()