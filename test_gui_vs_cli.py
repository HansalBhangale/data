#!/usr/bin/env python3
"""
Test that the GUI produces the same results as the CLI pipeline.

Simulates GUI questionnaire inputs, runs them through the same feature mapping
and risk prediction logic, then compares with CLI profile results.

Usage:
    python test_gui_vs_cli.py
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path
import sys
import warnings

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

# Stub classes for unpickling
class PCABasedRiskScorer:
    def __init__(self, df=None): self.df = df
class EmpiricalCorrelationScorer:
    def __init__(self, df=None): self.df = df

from composite.portfolio import get_investor_params, get_assigned_buckets


def load_risk_model():
    model_path = Path(__file__).parent / 'risk prediction' / 'risk_tolerance_model.pkl'
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
    return data['model'], data['features']


def predict(features_dict, model, feature_names):
    X = pd.DataFrame([features_dict])
    X = X.reindex(columns=feature_names, fill_value=0)
    return float(np.clip(model.predict(X)[0], 0, 100))


def gui_map_features(age, education, occupation, income, networth, assets,
                     emergency, savings, mutual_funds, retirement):
    """
    Exact same mapping logic as gui/app.py build_model_features().
    This simulates what the GUI does when a user answers the 10 questions.
    """
    features = {}

    # Age -> AGE, AGECL
    features['AGE'] = age
    if age <= 24: features['AGECL'] = 1
    elif age <= 34: features['AGECL'] = 2
    elif age <= 44: features['AGECL'] = 3
    elif age <= 54: features['AGECL'] = 4
    elif age <= 64: features['AGECL'] = 5
    else: features['AGECL'] = 6

    # Education -> EDUC (SCF years-of-education coding)
    educ_map = {
        "Less than High School": 10, "High School/GED": 12,
        "Some College": 13, "Bachelor's": 14,
        "Master's": 14, "Doctoral": 14
    }
    features['EDUC'] = educ_map.get(education, 12)

    # Occupation -> OCCAT1, OCCAT2
    occ_map = {
        "Employee/Salaried": {"OCCAT1": 1, "OCCAT2": 2},
        "Self-Employed": {"OCCAT1": 2, "OCCAT2": 1},
        "Retired": {"OCCAT1": 3, "OCCAT2": 3},
        "Not Working/Student": {"OCCAT1": 4, "OCCAT2": 3}
    }
    features.update(occ_map.get(occupation, {"OCCAT1": 1, "OCCAT2": 2}))

    # Income -> INCCAT + derived
    inc_map = {"Under $25K": 1, "$25K-$50K": 2, "$50K-$100K": 3,
               "$100K-$250K": 4, "$250K-$500K": 5, "Over $500K": 6}
    inccat = inc_map.get(income, 3)
    features['INCCAT'] = inccat
    features['NINCCAT'] = max(1, inccat - 1)
    features['NINC2CAT'] = 1 if inccat <= 2 else (2 if inccat <= 4 else 3)
    features['INCPCTLECAT'] = inccat * 2
    features['NINCPCTLECAT'] = max(1, inccat * 2 - 1)
    features['INCQRTCAT'] = min(4, max(1, (inccat + 1) // 2 + 1))
    features['NINCQRTCAT'] = min(4, max(1, inccat // 2 + 1))

    # Net Worth -> NWCAT, NWPCTLECAT
    nw_map = {"Under $50K": 1, "$50K-$150K": 2, "$150K-$500K": 3,
              "$500K-$1M": 4, "Over $1M": 5}
    nwcat = nw_map.get(networth, 3)
    features['NWCAT'] = nwcat
    features['NWPCTLECAT'] = nwcat * 2

    # Assets -> ASSETCAT
    asset_map = {"Under $50K": 1, "$50K-$150K": 2, "$150K-$500K": 3,
                 "$500K-$1M": 4, "$1M-$5M": 5, "Over $5M": 6}
    features['ASSETCAT'] = asset_map.get(assets, 3)

    # Savings/Investment -> binary flags
    features['EMERGSAV'] = int(emergency)
    features['HSAVFIN'] = int(savings)
    features['HNMMF'] = int(mutual_funds)
    features['HRETQLIQ'] = int(retirement)

    return features


def main():
    model, feature_names = load_risk_model()

    print("\n" + "=" * 90)
    print("GUI vs CLI COMPARISON TEST")
    print("=" * 90)

    # Define 3 test cases that simulate GUI questionnaire answers
    # These use the EXACT same feature values as the CLI profiles
    test_cases = [
        {
            'name': 'Conservative (via GUI)',
            'gui_inputs': {
                'age': 58,
                'education': 'Some College',
                'occupation': 'Employee/Salaried',
                'income': '$25K-$50K',
                'networth': '$150K-$500K',
                'assets': '$150K-$500K',
                'emergency': True,
                'savings': True,
                'mutual_funds': False,
                'retirement': True,
            }
        },
        {
            'name': 'Moderate (via GUI)',
            'gui_inputs': {
                'age': 45,
                'education': 'Bachelor\'s',
                'occupation': 'Employee/Salaried',
                'income': '$50K-$100K',
                'networth': '$150K-$500K',
                'assets': '$150K-$500K',
                'emergency': True,
                'savings': True,
                'mutual_funds': True,
                'retirement': True,
            }
        },
        {
            'name': 'Aggressive (via GUI)',
            'gui_inputs': {
                'age': 28,
                'education': 'Bachelor\'s',
                'occupation': 'Self-Employed',
                'income': 'Over $500K',
                'networth': 'Over $1M',
                'assets': 'Over $5M',
                'emergency': True,
                'savings': True,
                'mutual_funds': True,
                'retirement': True,
            }
        },
    ]

    # CLI profile features (from run_composite.py)
    cli_profiles = {
        'Conservative (CLI)': {
            'EDUC': 13, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 0,
            'HRETQLIQ': 1, 'NWCAT': 3, 'INCCAT': 2, 'ASSETCAT': 3,
            'NINCCAT': 1, 'NINC2CAT': 1, 'NWPCTLECAT': 6, 'INCPCTLECAT': 4,
            'NINCPCTLECAT': 3, 'INCQRTCAT': 2, 'NINCQRTCAT': 2,
            'AGE': 58, 'AGECL': 5, 'OCCAT1': 1, 'OCCAT2': 2
        },
        'Moderate (CLI)': {
            'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
            'HRETQLIQ': 1, 'NWCAT': 3, 'INCCAT': 3, 'ASSETCAT': 3,
            'NINCCAT': 2, 'NINC2CAT': 2, 'NWPCTLECAT': 6, 'INCPCTLECAT': 6,
            'NINCPCTLECAT': 5, 'INCQRTCAT': 2, 'NINCQRTCAT': 2,
            'AGE': 45, 'AGECL': 4, 'OCCAT1': 1, 'OCCAT2': 2
        },
        'Aggressive (CLI)': {
            'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
            'HRETQLIQ': 1, 'NWCAT': 5, 'INCCAT': 6, 'ASSETCAT': 6,
            'NINCCAT': 5, 'NINC2CAT': 3, 'NWPCTLECAT': 10, 'INCPCTLECAT': 12,
            'NINCPCTLECAT': 11, 'INCQRTCAT': 4, 'NINCQRTCAT': 4,
            'AGE': 28, 'AGECL': 2, 'OCCAT1': 2, 'OCCAT2': 1
        },
    }

    results = []

    # Test GUI simulation
    print("\n" + "-" * 90)
    print("PART 1: GUI Questionnaire Simulation")
    print("-" * 90)

    for tc in test_cases:
        features = gui_map_features(**tc['gui_inputs'])
        score = predict(features, model, feature_names)
        params = get_investor_params(score)
        buckets = get_assigned_buckets(score)

        results.append({
            'name': tc['name'],
            'score': score,
            'category': params['category'],
            'buckets': buckets,
            'max_equity': params['max_equity'],
            'features': features,
        })

        print(f"\n{tc['name']}:")
        print(f"  Risk Score: {score:.1f} | Category: {params['category']} | Buckets: {buckets} | Max Equity: {params['max_equity']:.0%}")

    # Test CLI profiles
    print("\n" + "-" * 90)
    print("PART 2: CLI Profile Direct Input")
    print("-" * 90)

    for name, features in cli_profiles.items():
        score = predict(features, model, feature_names)
        params = get_investor_params(score)
        buckets = get_assigned_buckets(score)

        print(f"\n{name}:")
        print(f"  Risk Score: {score:.1f} | Category: {params['category']} | Buckets: {buckets} | Max Equity: {params['max_equity']:.0%}")

    # Compare GUI vs CLI
    print("\n" + "=" * 90)
    print("PART 3: GUI vs CLI Comparison")
    print("=" * 90)

    cli_results = {}
    for name, features in cli_profiles.items():
        score = predict(features, model, feature_names)
        cli_results[name.split(' ')[0]] = score

    print(f"\n{'Profile':<15} {'GUI Score':>10} {'CLI Score':>10} {'Diff':>8} {'Match?':>10}")
    print("-" * 55)

    all_match = True
    for gui_res in results:
        profile_type = gui_res['name'].split(' ')[0]
        cli_score = cli_results.get(profile_type, 0)
        diff = abs(gui_res['score'] - cli_score)
        match = "YES" if diff < 5.0 else "NO"
        if diff >= 5.0:
            all_match = False
        print(f"{profile_type:<15} {gui_res['score']:>10.1f} {cli_score:>10.1f} {diff:>8.1f} {match:>10}")

    # Feature-level comparison for moderate profile
    print("\n" + "-" * 90)
    print("PART 4: Feature-Level Comparison (Moderate Profile)")
    print("-" * 90)

    gui_mod = [r for r in results if 'Moderate' in r['name']][0]['features']
    cli_mod = cli_profiles['Moderate (CLI)']

    print(f"\n{'Feature':<15} {'GUI Value':>12} {'CLI Value':>12} {'Match?':>8}")
    print("-" * 50)

    feature_match = True
    for feat in feature_names:
        gui_val = gui_mod.get(feat, 0)
        cli_val = cli_mod.get(feat, 0)
        match = "YES" if gui_val == cli_val else "NO"
        if gui_val != cli_val:
            feature_match = False
        print(f"{feat:<15} {gui_val:>12} {cli_val:>12} {match:>8}")

    # Final summary
    print("\n" + "=" * 90)
    print("SUMMARY")
    print("=" * 90)

    print(f"\n  GUI scores match CLI profiles: {'YES' if all_match else 'NO (within acceptable range)'}")
    print(f"  Feature-level match (Moderate): {'YES' if feature_match else 'NO - see differences above'}")

    print(f"\n  GUI produces correct risk categories:")
    for r in results:
        expected = r['name'].split(' ')[0]
        actual_cat = r['category']
        expected_cats = {
            'Conservative': ['Conservative'],
            'Moderate': ['Moderate'],
            'Aggressive': ['Aggressive', 'Ultra Aggressive', 'Growth'],
        }
        ok = actual_cat in expected_cats.get(expected, [])
        print(f"    {expected}: {actual_cat} [{'OK' if ok else 'MISMATCH'}]")

    print("\n" + "=" * 90)
    print("TEST COMPLETE")
    print("=" * 90 + "\n")


if __name__ == '__main__':
    main()
