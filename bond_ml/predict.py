import os
import pandas as pd
import numpy as np

FEATURES_PATH = 'checkpoints/bond_features.parquet'

ETF_CHARACTERISTICS = {
    'BIL':  (0.2,  5, 'short_govt'),
    'SHV':  (0.5,  5, 'short_govt'),
    'FLOT': (0.5,  4, 'short_govt'),
    'FLRN': (0.5,  4, 'short_govt'),
    'SCHO': (2.0,  5, 'short_govt'),
    'SHY':  (1.9,  5, 'short_govt'),
    'VGSH': (1.8,  5, 'short_govt'),
    'NEAR': (2.0,  4, 'short_corp'),
    'SUB':  (2.0,  4, 'short_muni'),
    'VCSH': (3.0,  4, 'short_corp'),
    'IGSB': (3.0,  4, 'short_corp'),
    'SPSB': (3.0,  4, 'short_corp'),
    'VTIP': (3.0,  5, 'tips'),
    'STIP': (2.5,  5, 'tips'),
    'SJNK': (2.5,  2, 'high_yield'),
    'SCHR': (5.0,  5, 'inter_govt'),
    'VGIT': (5.5,  5, 'inter_govt'),
    'IEF':  (7.5,  5, 'inter_govt'),
    'SPIB': (6.5,  4, 'inter_corp'),
    'VCIT': (6.5,  4, 'inter_corp'),
    'USIG': (6.5,  4, 'inter_corp'),
    'IGIB': (6.0,  4, 'inter_corp'),
    'BOND': (5.5,  4, 'inter_corp'),
    'MBB':  (5.0,  5, 'mortgage'),
    'VMBS': (5.0,  5, 'mortgage'),
    'VTEB': (5.5,  4, 'muni'),
    'MUB':  (6.0,  4, 'muni'),
    'HYD':  (8.0,  2, 'muni_hy'),
    'AGG':  (6.0,  4, 'broad'),
    'BND':  (6.5,  4, 'broad'),
    'GBF':  (6.0,  4, 'broad'),
    'IUSB': (6.0,  4, 'broad'),
    'GOVT': (8.0,  5, 'broad_govt'),
    'TLT':  (17.0, 5, 'long_govt'),
    'VGLT': (15.0, 5, 'long_govt'),
    'SPTL': (16.0, 5, 'long_govt'),
    'EDV':  (20.0, 5, 'long_govt'),
    'ZROZ': (25.0, 5, 'long_govt'),
    'TIP':  (7.0,  5, 'tips'),
    'SCHP': (7.0,  5, 'tips'),
    'LTPZ': (15.0, 5, 'tips_long'),
    'LQD':  (8.5,  3, 'ig_corp'),
    'QLTA': (7.0,  4, 'ig_corp'),
    'HYG':  (3.5,  2, 'high_yield'),
    'JNK':  (4.0,  2, 'high_yield'),
    'USHY': (4.0,  2, 'high_yield'),
    'HYLB': (4.0,  2, 'high_yield'),
    'HYDB': (4.5,  2, 'high_yield'),
    'FALN': (4.0,  2, 'high_yield'),
    'ANGL': (4.5,  2, 'high_yield'),
    'BNDX': (7.0,  4, 'intl'),
    'BWX':  (8.0,  4, 'intl_govt'),
    'IAGG': (7.5,  4, 'intl'),
    'IGOV': (8.0,  5, 'intl_govt'),
    'EMB':  (8.5,  2, 'em_bond'),
    'VWOB': (8.0,  2, 'em_bond'),
    'PCY':  (8.0,  2, 'em_bond'),
    'PFF':  (4.0,  2, 'preferred'),
    'PFFD': (4.0,  2, 'preferred'),
    'JEPI': (3.0,  3, 'equity_income'),
}

WEIGHTS = {
    'duration':  0.35,
    'credit':    0.25,
    'momentum':  0.25,
    'yield':     0.15,
}


def get_latest_macro(df):
    macro_cols = [
        'fed_funds_rate', 'treasury_10y', 'treasury_2y',
        'yield_curve_slope', 'ig_credit_spread', 'hy_credit_spread',
        'inflation_cpi', 'fed_rate_change', 'ig_spread_change',
        'hy_spread_change', 'yield_curve_change'
    ]
    latest = df.sort_index().iloc[-1]
    return {col: latest[col] for col in macro_cols if col in latest}


def get_latest_momentum(df):
    momentum = {}
    for ticker, group in df.groupby('ticker'):
        latest = group.sort_index().iloc[-1]
        momentum[ticker] = {
            'momentum_6m': latest.get('momentum_6m', 0),
            'momentum_3m': latest.get('momentum_3m', 0),
        }
    return momentum


def compute_duration_score(duration, macro):
    fed_rate_change = macro.get('fed_rate_change', 0)
    rate_direction = -np.sign(fed_rate_change)
    rate_magnitude = min(abs(fed_rate_change) / 2.0, 1.0)

    if abs(fed_rate_change) < 0.25:
        neutral_score = 50 - abs(duration - 6) * 2
        return neutral_score

    if rate_direction > 0:
        score = 30 + (duration / 25) * 70 * rate_magnitude
    else:
        score = 30 + ((25 - duration) / 25) * 70 * rate_magnitude

    return np.clip(score, 5, 95)


def compute_credit_score(credit_quality, macro):
    ig_spread_change = macro.get('ig_spread_change', 0)
    hy_spread_change = macro.get('hy_spread_change', 0)

    ig_trend = -np.sign(ig_spread_change)
    hy_trend = -np.sign(hy_spread_change)

    ig_level = macro.get('ig_credit_spread', 1.5)
    hy_level = macro.get('hy_credit_spread', 4.0)

    if credit_quality == 5:
        credit_score = 50 + (-ig_trend) * 15
    elif credit_quality == 4:
        credit_score = 50 + ig_trend * 15
    elif credit_quality == 3:
        credit_score = 50 + ig_trend * 20
    elif credit_quality == 2:
        credit_score = 50 + hy_trend * 25
    else:
        credit_score = 50 + hy_trend * 30

    if hy_level > 6.0:
        credit_score -= (credit_quality == 2) * 10

    return np.clip(credit_score, 5, 95)


def compute_momentum_score(ticker, momentum_data):
    mom = momentum_data.get(ticker, {})
    mom_6m = mom.get('momentum_6m', 0)
    mom_3m = mom.get('momentum_3m', 0)

    combined = 0.6 * mom_6m + 0.4 * mom_3m
    score = 50 + combined * 250
    return np.clip(score, 5, 95)


def compute_yield_score(duration, credit_quality, macro):
    treasury_10y = macro.get('treasury_10y', 3.0)
    fed_rate = macro.get('fed_funds_rate', 2.0)

    if duration < 2:
        current_yield = fed_rate
    elif duration < 7:
        current_yield = (fed_rate + treasury_10y) / 2
    else:
        current_yield = treasury_10y

    credit_premium = {5: 0, 4: 0.5, 3: 1.0, 2: 2.5, 1: 4.0}
    total_yield = current_yield + credit_premium.get(credit_quality, 0)

    score = 10 + (total_yield / 8.0) * 80
    return np.clip(score, 10, 90)


def generate_bond_scores(df, macro, momentum_data):
    results = []

    for ticker, characteristics in ETF_CHARACTERISTICS.items():
        duration, credit_quality, category = characteristics

        dur_score  = compute_duration_score(duration, macro)
        cred_score = compute_credit_score(credit_quality, macro)
        mom_score  = compute_momentum_score(ticker, momentum_data)
        yld_score  = compute_yield_score(duration, credit_quality, macro)

        composite = (
            WEIGHTS['duration']  * dur_score  +
            WEIGHTS['credit']    * cred_score +
            WEIGHTS['momentum']  * mom_score  +
            WEIGHTS['yield']     * yld_score
        )

        results.append({
            'ticker':           ticker,
            'bond_score':       round(composite, 2),
            'duration_score':   round(dur_score, 2),
            'credit_score':     round(cred_score, 2),
            'momentum_score':   round(mom_score, 2),
            'yield_score':      round(yld_score, 2),
            'duration':         duration,
            'credit_quality':   credit_quality,
            'category':         category,
            'pred_return':      round(composite / 100 * 0.12, 4),
        })

    df_scores = pd.DataFrame(results)
    df_scores = df_scores.sort_values('bond_score', ascending=False)
    df_scores = df_scores.reset_index(drop=True)

    return df_scores


def print_scores(df_scores, macro):
    fed_rate  = macro.get('fed_funds_rate', 0)
    rate_chg  = macro.get('fed_rate_change', 0)
    ig_spread = macro.get('ig_credit_spread', 0)

    regime = "EASING" if rate_chg < -0.25 else \
             "HIKING" if rate_chg > 0.25 else "NEUTRAL"

    print("\n" + "=" * 75)
    print(f"  BOND SCORES — Rules-Based Factor Model")
    print(f"  Rate Regime: {regime}  |  Fed Rate: {fed_rate:.2f}%  "
          f"|  Rate Change: {rate_chg:+.2f}%  |  IG Spread: {ig_spread:.2f}%")
    print("=" * 75)
    print(f"  {'Ticker':<7} {'Score':>6} {'Duration':>9} "
          f"{'Credit':>7} {'Momentum':>9} {'Yield':>6} {'Category'}")
    print("  " + "-" * 70)

    for _, row in df_scores.iterrows():
        print(f"  {row['ticker']:<7} {row['bond_score']:>6.1f} "
              f"{row['duration_score']:>9.1f} {row['credit_score']:>7.1f} "
              f"{row['momentum_score']:>9.1f} {row['yield_score']:>6.1f} "
              f"{row['category']}")

    print("=" * 75)


def main():
    if not os.path.exists(FEATURES_PATH):
        print("Feature matrix not found. Run fetch_data.py first.")
        return

    print("Loading feature matrix...")
    df = pd.read_parquet(FEATURES_PATH)

    macro = get_latest_macro(df)
    momentum_data = get_latest_momentum(df)

    print(f"\nCurrent macro snapshot:")
    print(f"  Fed funds rate:    {macro.get('fed_funds_rate', 0):.2f}%")
    print(f"  10Y Treasury:      {macro.get('treasury_10y', 0):.2f}%")
    print(f"  Rate change (4Q):  {macro.get('fed_rate_change', 0):+.2f}%")
    print(f"  IG spread:         {macro.get('ig_credit_spread', 0):.2f}%")
    print(f"  HY spread:         {macro.get('hy_credit_spread', 0):.2f}%")

    print("\nComputing bond scores...")
    df_scores = generate_bond_scores(df, macro, momentum_data)

    print_scores(df_scores, macro)

    os.makedirs('output_bond_ml', exist_ok=True)
    output_path = 'output_bond_ml/bond_scores.csv'
    df_scores.to_csv(output_path, index=False)
    print(f"\nSaved to {output_path}")

    return {
        'scores': df_scores,
        'macro': macro,
    }


if __name__ == '__main__':
    main()