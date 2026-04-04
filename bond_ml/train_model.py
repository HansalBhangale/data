import os
import pandas as pd
import numpy as np
import lightgbm as lgb
import joblib
from scipy.stats import spearmanr

TRAIN_CUTOFF = pd.Timestamp('2021-12-31')

def prepare_data(df):
    if not isinstance(df.index, pd.DatetimeIndex):
        try:
            df.index = pd.to_datetime(df.index)
        except Exception:
            pass
            
    df = df.dropna(subset=['fwd_total_return_1y'])
    
    exclude_cols = ['ticker', 'fwd_total_return_1y']
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    
    for col in feature_cols:
        if df[col].isnull().any():
            df[col] = df[col].fillna(df[col].median())
            
    X = df[feature_cols]
    y = df['fwd_total_return_1y']
    
    return X, y, feature_cols

def compute_metrics(y_true, y_pred, set_name=""):
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))
    mae = np.mean(np.abs(y_true - y_pred))
    
    y_mean = np.mean(y_true)
    if y_mean != 0 and not np.isnan(y_mean):
        ss_res = np.sum((y_true - y_pred) ** 2)
        ss_tot = np.sum((y_true - y_mean) ** 2)
        r2 = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0
    else:
        r2 = 0.0
    
    ic = 0.0
    try:
        if len(y_true) > 10 and len(np.unique(y_true)) > 2:
            ic, _ = spearmanr(y_true, y_pred)
            if np.isnan(ic):
                ic = 0.0
    except:
        ic = 0.0
    
    metrics = {
        'rmse': float(rmse),
        'mae': float(mae),
        'r2': float(r2),
        'ic': float(ic),
    }
    
    print(f"  {set_name} - RMSE: {rmse:.4f}, MAE: {mae:.4f}, R²: {r2:.4f}, IC: {ic:.4f}")
    return metrics

def train_lgbm(X, y, feature_cols):
    print(f"Training LightGBM on {X.shape[0]} samples with {X.shape[1]} features...")
    
    # Time-based split (2021-12-31 cutoff)
    train_mask = X.index <= TRAIN_CUTOFF
    X_train = X[train_mask]
    y_train = y[train_mask]
    X_val = X[~train_mask]
    y_val = y[~train_mask]
    
    print(f"  Train: {len(X_train)} samples (up to {TRAIN_CUTOFF.date()})")
    print(f"  Validation: {len(X_val)} samples (after {TRAIN_CUTOFF.date()})")
    
    # Much simpler model with strong regularization
    params = {
        'objective': 'regression',
        'metric': 'rmse',
        'boosting_type': 'gbdt',
        'learning_rate': 0.005,
        'num_leaves': 4,
        'max_depth': 3,
        'min_child_samples': 50,
        'feature_fraction': 0.5,
        'bagging_fraction': 0.6,
        'bagging_freq': 5,
        'reg_alpha': 2.0,
        'reg_lambda': 2.0,
        'random_state': 42,
        'verbose': -1
    }
    
    train_data = lgb.Dataset(X_train, label=y_train)
    val_data = lgb.Dataset(X_val, label=y_val, reference=train_data)
    
    model = lgb.train(
        params,
        train_data,
        num_boost_round=30,
    )
    
    train_preds = model.predict(X_train)
    val_preds = model.predict(X_val)
    
    train_metrics = compute_metrics(y_train.values, train_preds, "Train")
    val_metrics = compute_metrics(y_val.values, val_preds, "Validation")
    
    return model, train_metrics, val_metrics, X_train, y_train, X_val, y_val

def main():
    data_path = 'checkpoints/bond_features.parquet'
    
    if not os.path.exists(data_path):
        print(f"Data not found at {data_path}. Please run fetch_data.py first.")
        return
        
    print("Loading feature matrix...")
    df = pd.read_parquet(data_path)
    
    X, y, feature_cols = prepare_data(df)
    
    model, train_metrics, val_metrics, X_train, y_train, X_val, y_val = train_lgbm(X, y, feature_cols)
    
    # Feature importance
    importance = model.feature_importance(importance_type='gain')
    importance_df = pd.DataFrame({
        'feature': feature_cols,
        'importance': importance
    }).sort_values('importance', ascending=False)
    
    print("\nTop 10 Feature Importance:")
    print(importance_df.head(10).to_string(index=False))
    
    output_path = 'checkpoints/bond_lgbm_model.pkl'
    joblib.dump((model, feature_cols), output_path)
    print(f"\nModel and feature columns saved to {output_path}")
    
    return {
        'train_metrics': train_metrics,
        'val_metrics': val_metrics,
        'feature_cols': feature_cols,
        'n_samples': len(X),
        'n_train': len(X_train),
        'n_val': len(X_val),
        'feature_importance': importance_df.to_dict('records'),
    }

if __name__ == '__main__':
    main()