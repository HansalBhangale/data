"""
Evaluation module for performance prediction and risk scores.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from scipy import stats


def evaluate_model(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    model_name: str = 'Model'
) -> Dict[str, float]:
    """
    Evaluate regression model predictions.

    Parameters
    ----------
    y_true : np.ndarray
        True values
    y_pred : np.ndarray
        Predicted values
    model_name : str
        Name for display

    Returns
    -------
    Dict[str, float]
        Evaluation metrics
    """
    # Remove NaN
    mask = ~(np.isnan(y_true) | np.isnan(y_pred))
    y_true = y_true[mask]
    y_pred = y_pred[mask]

    if len(y_true) == 0:
        return {'error': 'No valid predictions'}

    # RMSE
    rmse = np.sqrt(np.mean((y_true - y_pred) ** 2))

    # MAE
    mae = np.mean(np.abs(y_true - y_pred))

    # R²
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)
    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

    # Spearman rank correlation
    spearman_corr, spearman_p = stats.spearmanr(y_true, y_pred)

    # Information Coefficient (IC) - correlation between predictions and returns
    ic, ic_p = stats.pearsonr(y_pred, y_true)

    # IC Information Ratio (ICIR) - IC mean / IC std
    # Rolling IC would be better but we use overall IC here
    icir = ic / np.std(y_pred) if np.std(y_pred) > 0 else 0

    metrics = {
        'model': model_name,
        'rmse': rmse,
        'mae': mae,
        'r2': r2,
        'spearman': spearman_corr,
        'spearman_p': spearman_p,
        'ic': ic,
        'ic_p': ic_p,
        'icir': icir,
        'n_samples': len(y_true),
    }

    print(f"\n{model_name} Evaluation:")
    print(f"  RMSE: {rmse:.4f}")
    print(f"  MAE: {mae:.4f}")
    print(f"  R²: {r2:.4f}")
    print(f"  Spearman Correlation: {spearman_corr:.4f} (p={spearman_p:.4f})")
    print(f"  IC (Pearson): {ic:.4f} (p={ic_p:.4f})")
    print(f"  ICIR: {icir:.4f}")
    print(f"  Samples: {len(y_true)}")

    return metrics


def evaluate_top_bottom_decile(
    df: pd.DataFrame,
    pred_col: str,
    target_col: str,
    spy_col: Optional[str] = None
) -> Dict[str, float]:
    """
    Evaluate top/bottom decile hit rates.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with predictions and actual returns
    pred_col : str
        Prediction column name
    target_col : str
        Target column name
    spy_col : str, optional
        SPY return column for benchmark

    Returns
    -------
    Dict[str, float]
        Decile analysis results
    """
    df = df.copy()
    df = df.dropna(subset=[pred_col, target_col])

    # Rank by prediction
    df['pred_rank'] = df[pred_col].rank(pct=True)

    # Top decile
    top_decile = df[df['pred_rank'] >= 0.9]
    top_return = top_decile[target_col].mean()
    top_hit_rate = (top_decile[target_col] > 0).mean()

    # Bottom decile
    bottom_decile = df[df['pred_rank'] <= 0.1]
    bottom_return = bottom_decile[target_col].mean()
    bottom_hit_rate = (bottom_decile[target_col] < 0).mean()

    # Long-short spread
    spread = top_return - bottom_return

    # Benchmark comparison
    if spy_col and spy_col in df.columns:
        spy_return = df[spy_col].mean()
        top_excess = top_return - spy_return
        bottom_excess = bottom_return - spy_return
    else:
        top_excess = top_return
        bottom_excess = bottom_return

    results = {
        'top_decile_return': top_return,
        'bottom_decile_return': bottom_return,
        'spread': spread,
        'top_hit_rate': top_hit_rate,
        'bottom_hit_rate': bottom_hit_rate,
        'top_excess': top_excess,
        'bottom_excess': bottom_excess,
        'n_top': len(top_decile),
        'n_bottom': len(bottom_decile),
    }

    print("\nTop/Bottom Decile Analysis:")
    print(f"  Top Decile Return: {top_return:.4f} (Hit Rate: {top_hit_rate:.2%})")
    print(f"  Bottom Decile Return: {bottom_return:.4f} (Hit Rate: {bottom_hit_rate:.2%})")
    print(f"  Long-Short Spread: {spread:.4f}")

    return results


def evaluate_risk_scores(
    risk_df: pd.DataFrame,
    df: pd.DataFrame,
    target_col: str = 'excess_return_1y',
    volatility_col: Optional[str] = None
) -> Dict[str, float]:
    """
    Validate risk scores against realized outcomes.

    Parameters
    ----------
    risk_df : pd.DataFrame
        Risk scores DataFrame
    df : pd.DataFrame
        Original data with realized returns
    target_col : str
        Target column name
    volatility_col : str, optional
        Column with realized volatility

    Returns
    -------
    Dict[str, float]
        Validation metrics
    """
    # Merge risk scores with data
    merged = pd.concat([risk_df, df[[target_col]].reset_index(drop=True)], axis=1)
    merged = merged.dropna(subset=['risk_score', target_col])

    # Correlation with target return
    corr_return = merged['risk_score'].corr(merged[target_col])

    # Correlation with volatility (if available)
    if volatility_col and volatility_col in df.columns:
        merged['volatility'] = df[volatility_col].values
        corr_vol = merged['risk_score'].corr(merged['volatility'])
    else:
        corr_vol = None

    # Quartile analysis
    merged['risk_quartile'] = pd.qcut(merged['risk_score'], 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])

    quartile_stats = merged.groupby('risk_quartile').agg({
        target_col: ['mean', 'std', 'count'],
        'risk_score': 'mean'
    })

    # Check monotonicity: higher risk -> higher volatility (std of returns)
    quartile_stds = [quartile_stats.loc[q, (target_col, 'std')] for q in ['Q1', 'Q2', 'Q3', 'Q4']]
    monotonic = all(quartile_stds[i] <= quartile_stds[i+1] for i in range(3))

    metrics = {
        'corr_with_return': corr_return,
        'corr_with_volatility': corr_vol,
        'quartile_monotonic': monotonic,
        'quartile_stats': quartile_stats.to_dict(),
        'n_samples': len(merged),
    }

    print("\nRisk Score Validation:")
    print(f"  Correlation with Return: {corr_return:.4f}")
    if corr_vol is not None:
        print(f"  Correlation with Volatility: {corr_vol:.4f}")
    print(f"  Quartile Monotonic (vol increases with risk): {monotonic}")
    print("\n  Return Stats by Risk Quartile:")
    print(quartile_stats.to_string())

    return metrics


def backtest_portfolio(
    df: pd.DataFrame,
    pred_col: str,
    target_col: str,
    n_quintiles: int = 5,
    by_quarter: bool = True
) -> pd.DataFrame:
    """
    Simple backtest: long top quintile by predicted alpha.

    Parameters
    ----------
    df : pd.DataFrame
        DataFrame with predictions and returns
    pred_col : str
        Prediction column name
    target_col : str
        Target return column name
    n_quintiles : int
        Number of groups (default 5 for quintiles)
    by_quarter : bool
        Group by quarter for time-series analysis

    Returns
    -------
    pd.DataFrame
        Backtest results
    """
    df = df.copy()
    df = df.dropna(subset=[pred_col, target_col])

    if 'quarter' not in df.columns and 'year' not in df.columns:
        by_quarter = False

    if by_quarter and 'quarter_label' in df.columns:
        # Group by quarter
        results = []

        for quarter in df['quarter_label'].unique():
            q_df = df[df['quarter_label'] == quarter].copy()

            if len(q_df) < n_quintiles * 2:  # Need enough samples
                continue

            # Rank by prediction
            q_df['pred_rank'] = q_df[pred_col].rank(pct=True)
            q_df['quintile'] = pd.qcut(q_df['pred_rank'], n_quintiles, labels=False)

            # Compute returns by quintile
            for q in range(n_quintiles):
                quintile_df = q_df[q_df['quintile'] == q]
                results.append({
                    'quarter': quarter,
                    'quintile': q + 1,
                    'return': quintile_df[target_col].mean(),
                    'n_stocks': len(quintile_df),
                })

        results_df = pd.DataFrame(results)

        # Pivot to see quintile performance over time
        pivot = results_df.pivot(index='quarter', columns='quintile', values='return')

        print("\nPortfolio Backtest Results (by quarter):")
        print(f"  Top Quintile Mean Return: {results_df[results_df['quintile'] == n_quintiles]['return'].mean():.4f}")
        print(f"  Bottom Quintile Mean Return: {results_df[results_df['quintile'] == 1]['return'].mean():.4f}")
        print(f"  Long-Short Spread: {results_df[results_df['quintile'] == n_quintiles]['return'].mean() - results_df[results_df['quintile'] == 1]['return'].mean():.4f}")

        return results_df

    else:
        # Single-period analysis
        df['pred_rank'] = df[pred_col].rank(pct=True)
        df['quintile'] = pd.qcut(df['pred_rank'], n_quintiles, labels=False)

        results = df.groupby('quintile').agg({
            target_col: ['mean', 'std', 'count']
        }).reset_index()

        results.columns = ['quintile', 'mean_return', 'std_return', 'count']

        print("\nPortfolio Backtest Results:")
        for _, row in results.iterrows():
            print(f"  Quintile {int(row['quintile'])+1}: Return={row['mean_return']:.4f}, Std={row['std_return']:.4f}, N={int(row['count'])}")

        return results


def generate_evaluation_report(
    model_metrics: Dict,
    decile_results: Dict,
    risk_metrics: Optional[Dict] = None
) -> str:
    """
    Generate a text summary report of all evaluation results.

    Parameters
    ----------
    model_metrics : Dict
        Model evaluation metrics
    decile_results : Dict
        Top/bottom decile results
    risk_metrics : Dict, optional
        Risk score validation metrics

    Returns
    -------
    str
        Formatted report
    """
    report = []
    report.append("=" * 60)
    report.append("SP500 ML Model Evaluation Report")
    report.append("=" * 60)

    report.append("\n## Model Performance")
    report.append(f"  RMSE: {model_metrics['rmse']:.4f}")
    report.append(f"  MAE: {model_metrics['mae']:.4f}")
    report.append(f"  R²: {model_metrics['r2']:.4f}")
    report.append(f"  Spearman Correlation: {model_metrics['spearman']:.4f}")
    report.append(f"  IC (Information Coefficient): {model_metrics['ic']:.4f}")
    report.append(f"  ICIR (IC Information Ratio): {model_metrics['icir']:.4f}")

    report.append("\n## Decile Analysis")
    report.append(f"  Top Decile Return: {decile_results['top_decile_return']:.4f}")
    report.append(f"  Bottom Decile Return: {decile_results['bottom_decile_return']:.4f}")
    report.append(f"  Long-Short Spread: {decile_results['spread']:.4f}")
    report.append(f"  Top Hit Rate: {decile_results['top_hit_rate']:.2%}")
    report.append(f"  Bottom Hit Rate: {decile_results['bottom_hit_rate']:.2%}")

    if risk_metrics:
        report.append("\n## Risk Score Validation")
        report.append(f"  Correlation with Return: {risk_metrics['corr_with_return']:.4f}")
        if risk_metrics.get('corr_with_volatility') is not None:
            report.append(f"  Correlation with Volatility: {risk_metrics['corr_with_volatility']:.4f}")
        report.append(f"  Quartile Monotonic: {risk_metrics['quartile_monotonic']}")

    report.append("\n" + "=" * 60)

    return "\n".join(report)