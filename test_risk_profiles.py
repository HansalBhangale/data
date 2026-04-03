#!/usr/bin/env python3
"""
Test script to verify risk tolerance model predictions for different investor profiles.
Tests conservative, moderate, and aggressive profiles through both:
1. Direct feature input (run_composite.py profiles)
2. GUI questionnaire simulation
"""

import pickle
import numpy as np
import pandas as pd
from pathlib import Path

# Stub classes for unpickling
class PCABasedRiskScorer:
    def __init__(self, df=None): self.df = df

class EmpiricalCorrelationScorer:
    def __init__(self, df=None): self.df = df


def load_risk_model():
    model_path = Path(__file__).parent / 'risk prediction' / 'risk_tolerance_model.pkl'
    with open(model_path, 'rb') as f:
        data = pickle.load(f)
    return data['model'], data['features']


def predict(features_dict, model, feature_names):
    """Predict risk score from feature dict."""
    X = pd.DataFrame([features_dict])
    X = X.reindex(columns=feature_names, fill_value=0)
    score = float(np.clip(model.predict(X)[0], 0, 100))
    return score


def get_category(score):
    if score <= 20:
        return "Ultra Conservative", [1], 0.40
    elif score <= 35:
        return "Conservative", [1, 2], 0.55
    elif score <= 50:
        return "Moderate", [2, 3], 0.70
    elif score <= 70:
        return "Growth", [3, 4], 0.85
    elif score <= 85:
        return "Aggressive", [4, 5], 0.90
    else:
        return "Ultra Aggressive", [5], 0.95


def test_cli_profiles(model, feature_names):
    """Test the predefined investor profiles from run_composite.py"""
    print("\n" + "=" * 80)
    print("TEST 1: CLI INVESTOR PROFILES (from run_composite.py)")
    print("=" * 80)

    profiles = {
        'ultra_conservative': {
            'name': 'Ultra Conservative (Retired Senior)',
            'features': {
                'EDUC': 12, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 0,
                'HRETQLIQ': 1, 'NWCAT': 2, 'INCCAT': 1, 'ASSETCAT': 2,
                'NINCCAT': 1, 'NINC2CAT': 1, 'NWPCTLECAT': 4, 'INCPCTLECAT': 2,
                'NINCPCTLECAT': 1, 'INCQRTCAT': 1, 'NINCQRTCAT': 1,
                'AGE': 72, 'AGECL': 6, 'OCCAT1': 4, 'OCCAT2': 3
            }
        },
        'conservative': {
            'name': 'Conservative (Risk-Averse Professional)',
            'features': {
                'EDUC': 13, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 0,
                'HRETQLIQ': 1, 'NWCAT': 3, 'INCCAT': 2, 'ASSETCAT': 3,
                'NINCCAT': 1, 'NINC2CAT': 1, 'NWPCTLECAT': 6, 'INCPCTLECAT': 4,
                'NINCPCTLECAT': 3, 'INCQRTCAT': 2, 'NINCQRTCAT': 2,
                'AGE': 58, 'AGECL': 5, 'OCCAT1': 1, 'OCCAT2': 2
            }
        },
        'moderate': {
            'name': 'Moderate (Balanced Investor)',
            'features': {
                'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
                'HRETQLIQ': 1, 'NWCAT': 3, 'INCCAT': 3, 'ASSETCAT': 3,
                'NINCCAT': 2, 'NINC2CAT': 2, 'NWPCTLECAT': 6, 'INCPCTLECAT': 6,
                'NINCPCTLECAT': 5, 'INCQRTCAT': 2, 'NINCQRTCAT': 2,
                'AGE': 45, 'AGECL': 4, 'OCCAT1': 1, 'OCCAT2': 2
            }
        },
        'growth': {
            'name': 'Growth (Young High Earner)',
            'features': {
                'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
                'HRETQLIQ': 1, 'NWCAT': 4, 'INCCAT': 4, 'ASSETCAT': 4,
                'NINCCAT': 3, 'NINC2CAT': 2, 'NWPCTLECAT': 8, 'INCPCTLECAT': 8,
                'NINCPCTLECAT': 7, 'INCQRTCAT': 3, 'NINCQRTCAT': 3,
                'AGE': 35, 'AGECL': 3, 'OCCAT1': 1, 'OCCAT2': 2
            }
        },
        'aggressive': {
            'name': 'Aggressive (Young Finance Professional)',
            'features': {
                'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
                'HRETQLIQ': 1, 'NWCAT': 4, 'INCCAT': 5, 'ASSETCAT': 5,
                'NINCCAT': 4, 'NINC2CAT': 3, 'NWPCTLECAT': 8, 'INCPCTLECAT': 10,
                'NINCPCTLECAT': 9, 'INCQRTCAT': 3, 'NINCQRTCAT': 3,
                'AGE': 30, 'AGECL': 2, 'OCCAT1': 1, 'OCCAT2': 2
            }
        },
        'ultra_aggressive': {
            'name': 'Ultra Aggressive (Wealthy Risk-Seeker)',
            'features': {
                'EDUC': 14, 'EMERGSAV': 0, 'HSAVFIN': 1, 'HNMMF': 1,
                'HRETQLIQ': 1, 'NWCAT': 5, 'INCCAT': 6, 'ASSETCAT': 6,
                'NINCCAT': 5, 'NINC2CAT': 3, 'NWPCTLECAT': 10, 'INCPCTLECAT': 12,
                'NINCPCTLECAT': 11, 'INCQRTCAT': 4, 'NINCQRTCAT': 4,
                'AGE': 25, 'AGECL': 2, 'OCCAT1': 2, 'OCCAT2': 1
            }
        }
    }

    results = []
    for key, profile in profiles.items():
        score = predict(profile['features'], model, feature_names)
        category, buckets, max_equity = get_category(score)
        results.append({
            'Profile': profile['name'],
            'Score': score,
            'Category': category,
            'Buckets': str(buckets),
            'Max Equity': f"{max_equity:.0%}"
        })

    df = pd.DataFrame(results)
    print(f"\n{'Profile':<45} {'Score':>6} {'Category':<18} {'Buckets':>8} {'Max Eq':>7}")
    print("-" * 85)
    for _, row in df.iterrows():
        print(f"{row['Profile']:<45} {row['Score']:>6.1f} {row['Category']:<18} {row['Buckets']:>8} {row['Max Equity']:>7}")

    return results


def test_gui_simulation(model, feature_names):
    """Simulate GUI questionnaire answers for 3 investor types."""
    print("\n" + "=" * 80)
    print("TEST 2: GUI QUESTIONNAIRE SIMULATION")
    print("=" * 80)

    def map_gui_to_features(age, education, occupation, income, networth, assets,
                           emergency, savings, mutual_funds, retirement):
        """Map GUI answers to model features (same logic as gui/app.py)"""
        features = {}

        # Age
        features['AGE'] = age
        if age <= 24: features['AGECL'] = 1
        elif age <= 34: features['AGECL'] = 2
        elif age <= 44: features['AGECL'] = 3
        elif age <= 54: features['AGECL'] = 4
        elif age <= 64: features['AGECL'] = 5
        else: features['AGECL'] = 6

        # Education (SCF years-of-education coding)
        educ_map = {
            "Less than High School": 10, "High School/GED": 12,
            "Some College": 13, "Bachelor's": 14,
            "Master's": 14, "Doctoral": 14
        }
        features['EDUC'] = educ_map.get(education, 12)

        # Occupation
        occ_map = {
            "Employee/Salaried": {"OCCAT1": 1, "OCCAT2": 2},
            "Self-Employed": {"OCCAT1": 2, "OCCAT2": 1},
            "Retired": {"OCCAT1": 3, "OCCAT2": 3},
            "Not Working/Student": {"OCCAT1": 4, "OCCAT2": 3}
        }
        features.update(occ_map.get(occupation, {"OCCAT1": 1, "OCCAT2": 2}))

        # Income
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

        # Net Worth
        nw_map = {"Under $50K": 1, "$50K-$150K": 2, "$150K-$500K": 3,
                  "$500K-$1M": 4, "Over $1M": 5}
        nwcat = nw_map.get(networth, 3)
        features['NWCAT'] = nwcat
        features['NWPCTLECAT'] = nwcat * 2

        # Assets
        asset_map = {"Under $50K": 1, "$50K-$150K": 2, "$150K-$500K": 3,
                     "$500K-$1M": 4, "$1M-$5M": 5, "Over $5M": 6}
        features['ASSETCAT'] = asset_map.get(assets, 3)

        # Savings
        features['EMERGSAV'] = int(emergency)
        features['HSAVFIN'] = int(savings)
        features['HNMMF'] = int(mutual_funds)
        features['HRETQLIQ'] = int(retirement)

        return features

    # Conservative investor via GUI
    conservative = map_gui_to_features(
        age=60, education="High School/GED", occupation="Retired",
        income="$25K-$50K", networth="$50K-$150K", assets="$50K-$150K",
        emergency=True, savings=True, mutual_funds=False, retirement=True
    )

    # Moderate investor via GUI
    moderate = map_gui_to_features(
        age=45, education="Bachelor's", occupation="Employee/Salaried",
        income="$100K-$250K", networth="$150K-$500K", assets="$150K-$500K",
        emergency=True, savings=True, mutual_funds=True, retirement=True
    )

    # Aggressive investor via GUI
    aggressive = map_gui_to_features(
        age=30, education="Bachelor's", occupation="Self-Employed",
        income="$250K-$500K", networth="$500K-$1M", assets="$1M-$5M",
        emergency=True, savings=True, mutual_funds=True, retirement=True
    )

    test_cases = [
        ("Conservative (60yo Retired, $25-50K income)", conservative),
        ("Moderate (45yo Employee, $100-250K income)", moderate),
        ("Aggressive (30yo Self-Employed, $250-500K income)", aggressive),
    ]

    print(f"\n{'Profile':<50} {'Score':>6} {'Category':<18} {'Buckets':>8} {'Max Eq':>7}")
    print("-" * 90)

    for name, features in test_cases:
        score = predict(features, model, feature_names)
        category, buckets, max_equity = get_category(score)
        print(f"{name:<50} {score:>6.1f} {category:<18} {str(buckets):>8} {max_equity:>7.0%}")

        # Show key feature values
        print(f"  Key features: AGE={features['AGE']}, EDUC={features['EDUC']}, "
              f"INCCAT={features['INCCAT']}, NWCAT={features['NWCAT']}, "
              f"ASSETCAT={features['ASSETCAT']}")


def test_feature_ranges(model, feature_names):
    """Test that derived features are within SCF ranges."""
    print("\n" + "=" * 80)
    print("TEST 3: FEATURE RANGE VALIDATION")
    print("=" * 80)

    scf_ranges = {
        'EDUC': (1, 14), 'AGE': (18, 85), 'AGECL': (1, 6),
        'INCCAT': (1, 6), 'NINCCAT': (1, 6), 'NINC2CAT': (1, 3),
        'INCPCTLECAT': (1, 12), 'NINCPCTLECAT': (1, 12),
        'INCQRTCAT': (1, 4), 'NINCQRTCAT': (1, 4),
        'NWCAT': (1, 5), 'NWPCTLECAT': (1, 12),
        'ASSETCAT': (1, 6), 'OCCAT1': (1, 4), 'OCCAT2': (1, 4),
        'EMERGSAV': (0, 1), 'HSAVFIN': (0, 1), 'HNMMF': (0, 1), 'HRETQLIQ': (0, 1),
    }

    # Test with moderate profile features
    moderate_features = {
        'EDUC': 14, 'EMERGSAV': 1, 'HSAVFIN': 1, 'HNMMF': 1,
        'HRETQLIQ': 1, 'NWCAT': 3, 'INCCAT': 3, 'ASSETCAT': 3,
        'NINCCAT': 2, 'NINC2CAT': 2, 'NWPCTLECAT': 6, 'INCPCTLECAT': 6,
        'NINCPCTLECAT': 5, 'INCQRTCAT': 2, 'NINCQRTCAT': 2,
        'AGE': 45, 'AGECL': 4, 'OCCAT1': 1, 'OCCAT2': 2
    }

    all_valid = True
    for feat, (min_val, max_val) in scf_ranges.items():
        if feat in moderate_features:
            val = moderate_features[feat]
            valid = min_val <= val <= max_val
            status = "OK" if valid else "OUT OF RANGE"
            if not valid:
                all_valid = False
            print(f"  {feat:<15} = {val:>3}  (SCF range: {min_val:>3}-{max_val:>3})  [{status}]")

    print(f"\n  {'All features within SCF ranges!' if all_valid else 'WARNING: Some features out of range!'}")


if __name__ == '__main__':
    print("\n" + "=" * 80)
    print("RISK TOLERANCE MODEL - VALIDATION TEST")
    print("=" * 80)

    model, feature_names = load_risk_model()
    print(f"\nModel loaded: {type(model).__name__}")
    print(f"Features ({len(feature_names)}): {feature_names}")

    test_cli_profiles(model, feature_names)
    test_gui_simulation(model, feature_names)
    test_feature_ranges(model, feature_names)

    print("\n" + "=" * 80)
    print("ALL TESTS COMPLETE")
    print("=" * 80 + "\n")
