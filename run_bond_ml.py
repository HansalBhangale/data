#!/usr/bin/env python
"""
Bond ML Pipeline Entry Point

Usage:
    python run_bond_ml.py --step fetch    # Step 1: Fetch macro data and ETF prices
    python run_bond_ml.py --step train     # Step 2: Train LightGBM model
    python run_bond_ml.py --step predict   # Step 3: Generate bond scores
    python run_bond_ml.py                  # All steps
"""

import argparse
import pandas as pd
import numpy as np
from pathlib import Path
import sys
import warnings
import json
from datetime import datetime

warnings.filterwarnings('ignore')

sys.path.insert(0, str(Path(__file__).parent))

from bond_ml import fetch_data, train_model, predict


def save_metrics(metrics: dict, filepath: str) -> None:
    """Save metrics to JSON file."""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    def convert(obj):
        if isinstance(obj, (np.integer, np.floating)):
            return obj.item()
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert(i) for i in obj]
        return obj
    
    with open(path, 'w') as f:
        json.dump(convert(metrics), f, indent=2, default=str)
    
    print(f"Saved metrics to {path}")


def run_fetch(output_dir: str) -> dict:
    """Step 1: Fetch macro data and bond ETF prices, build feature matrix."""
    print("\n" + "=" * 60)
    print("STEP 1: FETCHING DATA & BUILDING FEATURES")
    print("=" * 60)

    fetch_data.main()

    feature_path = Path('checkpoints/bond_features.csv')
    if feature_path.exists():
        df = pd.read_csv(feature_path, index_col=0)
        if isinstance(df.index, pd.DatetimeIndex):
            date_range = f"{df.index.min()} to {df.index.max()}"
        else:
            date_range = "Unknown"
        
        stats = {
            'step': 'fetch',
            'n_rows': int(len(df)),
            'n_etfs': int(df['ticker'].nunique()) if 'ticker' in df.columns else 0,
            'n_features': int(len([c for c in df.columns if c not in ['ticker', 'fwd_total_return_1y']])),
            'date_range': date_range,
            'etfs': df['ticker'].unique().tolist() if 'ticker' in df.columns else [],
            'feature_columns': [c for c in df.columns if c not in ['ticker', 'fwd_total_return_1y']],
            'timestamp': datetime.now().isoformat(),
        }
        return stats
    return {}


def run_train(output_dir: str) -> dict:
    """Step 2: Train LightGBM model on bond features."""
    print("\n" + "=" * 60)
    print("STEP 2: TRAINING MODEL")
    print("=" * 60)

    result = train_model.main()

    model_path = Path('checkpoints/bond_lgbm_model.pkl')
    feature_path = Path('checkpoints/bond_features.parquet')
    
    stats = {
        'step': 'train',
        'model_path': str(model_path),
        'features_path': str(feature_path),
        'cutoff_date': '2021-12-31',
        'timestamp': datetime.now().isoformat(),
    }
    
    if isinstance(result, dict) and 'train_metrics' in result:
        stats['train_metrics'] = result['train_metrics']
        stats['val_metrics'] = result['val_metrics']
        stats['n_train'] = result.get('n_train', 0)
        stats['n_val'] = result.get('n_val', 0)
        stats['feature_importance'] = result.get('feature_importance', [])[:15]
    
    if feature_path.exists():
        df = pd.read_parquet(feature_path)
        stats['training_samples'] = int(len(df))
        stats['n_features'] = int(len([c for c in df.columns if c not in ['ticker', 'fwd_total_return_1y']]))
    
    return stats


def run_predict(output_dir: str) -> dict:
    """Step 3: Generate bond scores and save to output."""
    print("\n" + "=" * 60)
    print("STEP 3: GENERATING PREDICTIONS")
    print("=" * 60)

    result = predict.main()

    scores_path = Path('output_bond_ml/bond_scores.csv')
    stats = {
        'step': 'predict',
        'output_path': str(scores_path),
        'timestamp': datetime.now().isoformat(),
    }
    
    if scores_path.exists():
        scores_df = pd.read_csv(scores_path)
        stats['n_bonds_scored'] = int(len(scores_df))
        stats['bond_scores'] = scores_df.to_dict('records')
        stats['score_summary'] = {
            'mean': float(scores_df['bond_score'].mean()),
            'std': float(scores_df['bond_score'].std()),
            'min': float(scores_df['bond_score'].min()),
            'max': float(scores_df['bond_score'].max()),
        }
        # Add macro context if available
        if result and 'macro' in result:
            stats['macro_context'] = result['macro']
    
    if isinstance(result, dict) and 'test_metrics' in result:
        stats['test_metrics'] = result['test_metrics']
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Bond ML Pipeline')
    parser.add_argument('--step', type=str, choices=['fetch', 'train', 'predict'],
                       help='Run specific step (default: all steps)')
    parser.add_argument('--output', type=str, default='output_bond_ml',
                       help='Output directory (default: output_bond_ml)')

    args = parser.parse_args()

    script_dir = Path(__file__).parent
    output_dir = script_dir / args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Output directory: {output_dir}")

    all_metrics = {}

    if args.step == 'fetch':
        fetch_stats = run_fetch(str(output_dir))
        all_metrics['fetch'] = fetch_stats

    elif args.step == 'train':
        train_stats = run_train(str(output_dir))
        all_metrics['train'] = train_stats

    elif args.step == 'predict':
        predict_stats = run_predict(str(output_dir))
        all_metrics['predict'] = predict_stats

    else:
        print("\n" + "=" * 60)
        print("BOND ML PIPELINE - FULL RUN")
        print("=" * 60)

        fetch_stats = run_fetch(str(output_dir))
        all_metrics['fetch'] = fetch_stats

        train_stats = run_train(str(output_dir))
        all_metrics['train'] = train_stats

        predict_stats = run_predict(str(output_dir))
        all_metrics['predict'] = predict_stats

    save_metrics(all_metrics, str(output_dir / 'pipeline_metrics.json'))

    print("\n" + "=" * 60)
    print("PIPELINE COMPLETE")
    print("=" * 60)
    print(f"Results saved to: {output_dir}")
    print(f"Metrics saved to: {output_dir / 'pipeline_metrics.json'}")


if __name__ == '__main__':
    main()