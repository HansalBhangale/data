"""
Risk Score computation module.
Computes a continuous risk score (0-100) from 6 risk components.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from .config import RISK_WEIGHTS


class RiskScorer:
    """
    Compute continuous risk scores (0-100) from multiple risk components.

    Risk components (all mapped to 0-100 via percentile rank):
    1. Leverage Risk (25%): debt_to_equity, net_debt/EBITDA, leverage_ratio
    2. Liquidity Risk (15%): inverted current_ratio, inverted cash_ratio
    3. Profitability Risk (15%): inverted ROE, inverted ROA, inverted margins
    4. Earnings Volatility (20%): revenue_growth_vol, net_income_vol, operating_margin_vol
    5. Valuation Risk (10%): sector-normalized PE, PB, EV/EBITDA
    6. Model Uncertainty (15%): |pred_1y - pred_3y/3|, residual magnitude
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None
    ):
        """
        Initialize RiskScorer.

        Parameters
        ----------
        weights : Dict[str, float], optional
            Custom weights for risk components (default from config)
        """
        self.weights = weights or RISK_WEIGHTS
        self.fitted_ = False

    def _compute_leverage_risk(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute leverage risk component.
        Higher debt = higher risk.
        """
        risk_scores = pd.Series(0.0, index=df.index)
        n_components = 0

        # debt_to_equity (already in 0-20 range from clipping)
        if 'debt_to_equity' in df.columns:
            risk_scores += df['debt_to_equity'].fillna(0) / 20  # Normalize to 0-1
            n_components += 1

        # leverage_ratio (already in 0-5 range)
        if 'leverage_ratio' in df.columns:
            risk_scores += df['leverage_ratio'].fillna(0) / 5
            n_components += 1

        # net_debt / EBITDA (compute if possible)
        if 'net_debt' in df.columns and 'ebitda_ttm' in df.columns:
            # Handle negative EBITDA (highly risky)
            net_debt_ebitda = df['net_debt'] / df['ebitda_ttm'].replace(0, np.nan)
            net_debt_ebitda = net_debt_ebitda.clip(-10, 10)  # Cap extreme values
            # Higher ratio = higher risk
            risk_scores += (net_debt_ebitda.fillna(0) + 10) / 20  # Normalize
            n_components += 1

        # Average of components (scale to 0-100)
        if n_components > 0:
            risk_scores = (risk_scores / n_components) * 100

        return risk_scores.clip(0, 100)

    def _compute_liquidity_risk(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute liquidity risk component.
        Lower liquidity = higher risk (so we invert).
        """
        risk_scores = pd.Series(0.0, index=df.index)
        n_components = 0

        # current_ratio (higher = better liquidity = lower risk)
        # Invert: max(20 - current_ratio, 0) / 20
        if 'current_ratio' in df.columns:
            inverted = np.maximum(20 - df['current_ratio'].clip(0, 20), 0)
            risk_scores += inverted / 20
            n_components += 1

        # cash_ratio (higher = better = lower risk)
        if 'cash_ratio' in df.columns:
            inverted = np.maximum(5 - df['cash_ratio'].clip(0, 5), 0)
            risk_scores += inverted / 5
            n_components += 1

        # Average and scale
        if n_components > 0:
            risk_scores = (risk_scores / n_components) * 100

        return risk_scores.clip(0, 100)

    def _compute_profitability_risk(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute profitability risk component.
        Lower profitability = higher risk (so we invert).
        """
        risk_scores = pd.Series(0.0, index=df.index)
        n_components = 0

        # ROE (higher = better = lower risk)
        if 'roe' in df.columns:
            # ROE clipped to -5 to 5, so invert
            inverted = np.maximum(5 - df['roe'].clip(-5, 5), 0)
            risk_scores += inverted / 10
            n_components += 1

        # ROA (higher = better = lower risk)
        if 'roa' in df.columns:
            inverted = np.maximum(2 - df['roa'].clip(-2, 2), 0)
            risk_scores += inverted / 4
            n_components += 1

        # Operating margin (higher = better = lower risk)
        if 'operating_margin' in df.columns:
            # Typical range 0 to 0.5, invert
            inverted = np.maximum(0.5 - df['operating_margin'].clip(0, 0.5), 0)
            risk_scores += inverted / 0.5
            n_components += 1

        # Net margin (higher = better = lower risk)
        if 'net_margin' in df.columns:
            inverted = np.maximum(0.5 - df['net_margin'].clip(0, 0.5), 0)
            risk_scores += inverted / 0.5
            n_components += 1

        # Average and scale
        if n_components > 0:
            risk_scores = (risk_scores / n_components) * 100

        return risk_scores.clip(0, 100)

    def _compute_earnings_volatility(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute earnings volatility risk component.
        Higher volatility = higher risk.
        """
        risk_scores = pd.Series(0.0, index=df.index)
        n_components = 0

        # Revenue growth volatility
        if 'revenue_growth_vol' in df.columns:
            risk_scores += df['revenue_growth_vol'].fillna(0)
            n_components += 1

        # Net income volatility
        if 'net_income_vol' in df.columns:
            risk_scores += df['net_income_vol'].fillna(0)
            n_components += 1

        # Operating margin volatility
        if 'operating_margin_vol' in df.columns:
            risk_scores += df['operating_margin_vol'].fillna(0) * 10  # Scale up
            n_components += 1

        # Return volatility (if available)
        if 'return_volatility' in df.columns:
            risk_scores += df['return_volatility'].fillna(0) * 10  # Scale up
            n_components += 1

        if n_components > 0:
            # Normalize and scale to 0-100
            risk_scores = risk_scores / n_components
            # Percentile rank for normalization
            risk_scores = risk_scores.rank(pct=True) * 100

        return risk_scores.fillna(50)  # Default to median risk if missing

    def _compute_valuation_risk(self, df: pd.DataFrame) -> pd.Series:
        """
        Compute valuation risk component.
        Uses sector-normalized z-scores when available.
        Higher valuation = higher risk.
        """
        risk_scores = pd.Series(0.0, index=df.index)
        n_components = 0

        # PE sector z-score (if available, else raw)
        pe_col = 'pe_ratio_sector_zscore' if 'pe_ratio_sector_zscore' in df.columns else 'pe_ratio'
        if pe_col in df.columns:
            # Higher PE = higher risk
            risk_scores += df[pe_col].fillna(0).clip(-5, 5)
            n_components += 1

        # PB sector z-score
        pb_col = 'pb_ratio_sector_zscore' if 'pb_ratio_sector_zscore' in df.columns else 'pb_ratio'
        if pb_col in df.columns:
            risk_scores += df[pb_col].fillna(0).clip(-5, 5)
            n_components += 1

        # EV/EBITDA sector z-score
        ev_col = 'ev_ebitda_sector_zscore' if 'ev_ebitda_sector_zscore' in df.columns else 'ev_ebitda'
        if ev_col in df.columns:
            risk_scores += df[ev_col].fillna(0).clip(-5, 5)
            n_components += 1

        if n_components > 0:
            # Average and map from z-score to 0-100
            risk_scores = risk_scores / n_components
            # Map z-score (-5 to 5) to (0 to 100)
            risk_scores = ((risk_scores + 5) / 10) * 100

        return risk_scores.clip(0, 100)

    def _compute_model_uncertainty(
        self,
        df: pd.DataFrame,
        pred_1y: np.ndarray,
        pred_3y: np.ndarray
    ) -> pd.Series:
        """
        Compute model uncertainty risk component.
        Higher uncertainty = higher risk.
        """
        risk_scores = pd.Series(0.0, index=df.index)

        # Prediction divergence: |pred_1y - pred_3y/3|
        # Large divergence indicates uncertainty
        divergence = np.abs(pred_1y - pred_3y / 3)

        # Normalize by max divergence
        max_div = np.max(divergence) if np.max(divergence) > 0 else 1
        risk_scores += (divergence / max_div) * 100

        return risk_scores.clip(0, 100)

    def fit(
        self,
        df: pd.DataFrame,
        pred_1y: np.ndarray,
        pred_3y: np.ndarray
    ) -> 'RiskScorer':
        """
        Fit the risk scorer (compute baseline statistics).

        Parameters
        ----------
        df : pd.DataFrame
            Preprocessed data
        pred_1y : np.ndarray
            1-year return predictions
        pred_3y : np.ndarray
            3-year return predictions

        Returns
        -------
        self
        """
        # Store component data for later use
        self.component_cols_ = {
            'leverage': ['debt_to_equity', 'leverage_ratio', 'net_debt', 'ebitda_ttm'],
            'liquidity': ['current_ratio', 'cash_ratio'],
            'profitability': ['roe', 'roa', 'operating_margin', 'net_margin'],
            'volatility': ['revenue_growth_vol', 'net_income_vol', 'operating_margin_vol', 'return_volatility'],
            'valuation': ['pe_ratio_sector_zscore', 'pb_ratio_sector_zscore', 'ev_ebitda_sector_zscore'],
        }

        self.fitted_ = True
        return self

    def compute_risk_scores(
        self,
        df: pd.DataFrame,
        pred_1y: np.ndarray,
        pred_3y: np.ndarray
    ) -> pd.DataFrame:
        """
        Compute risk scores for each row.

        Parameters
        ----------
        df : pd.DataFrame
            Preprocessed data
        pred_1y : np.ndarray
            1-year return predictions
        pred_3y : np.ndarray
            3-year return predictions

        Returns
        -------
        pd.DataFrame
            DataFrame with risk scores and components
        """
        if not self.fitted_:
            self.fit(df, pred_1y, pred_3y)

        # Compute component scores
        leverage_risk = self._compute_leverage_risk(df)
        liquidity_risk = self._compute_liquidity_risk(df)
        profitability_risk = self._compute_profitability_risk(df)
        earnings_volatility = self._compute_earnings_volatility(df)
        valuation_risk = self._compute_valuation_risk(df)
        model_uncertainty = self._compute_model_uncertainty(df, pred_1y, pred_3y)

        # Combine with weights
        total_risk = (
            self.weights['leverage_risk'] * leverage_risk +
            self.weights['liquidity_risk'] * liquidity_risk +
            self.weights['profitability_risk'] * profitability_risk +
            self.weights['earnings_volatility'] * earnings_volatility +
            self.weights['valuation_risk'] * valuation_risk +
            self.weights['model_uncertainty'] * model_uncertainty
        )

        # Clip to 0-100
        total_risk = total_risk.clip(0, 100)

        # Return as DataFrame
        result = pd.DataFrame({
            'risk_score': total_risk,
            'leverage_risk': leverage_risk,
            'liquidity_risk': liquidity_risk,
            'profitability_risk': profitability_risk,
            'earnings_volatility': earnings_volatility,
            'valuation_risk': valuation_risk,
            'model_uncertainty': model_uncertainty,
        })

        return result

    def validate_risk_scores(
        self,
        risk_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str = 'excess_return_1y'
    ) -> Dict[str, float]:
        """
        Validate risk scores against realized outcomes.

        Parameters
        ----------
        risk_df : pd.DataFrame
            Risk scores from compute_risk_scores()
        df : pd.DataFrame
            Original data with realized returns
        target_col : str
            Target column for validation

        Returns
        -------
        Dict[str, float]
            Validation metrics
        """
        # Add risk quartile
        risk_df = risk_df.copy()
        risk_df['risk_quartile'] = pd.qcut(risk_df['risk_score'], 4, labels=['Q1', 'Q2', 'Q3', 'Q4'])
        risk_df['actual_return'] = df[target_col].values

        # Compute realized volatility by quartile
        vol_by_quartile = risk_df.groupby('risk_quartile')['actual_return'].agg(['mean', 'std', 'count'])

        # Correlation with target
        correlation = risk_df['risk_score'].corr(df[target_col])

        metrics = {
            'correlation_with_return': correlation,
            'quartile_stats': vol_by_quartile.to_dict(),
        }

        # Check monotonicity (higher risk -> higher volatility)
        quartile_stds = [vol_by_quartile.loc[q, 'std'] for q in ['Q1', 'Q2', 'Q3', 'Q4']]
        monotonic = all(quartile_stds[i] <= quartile_stds[i+1] for i in range(3))

        metrics['quartile_monotonic'] = monotonic

        print("\nRisk Score Validation:")
        print(f"  Correlation with return: {correlation:.4f}")
        print(f"  Quartile monotonic (risk increases with vol): {monotonic}")
        print("\n  Return by Risk Quartile:")
        print(vol_by_quartile.to_string())

        return metrics


def compute_risk_score(
    df: pd.DataFrame,
    pred_1y: np.ndarray,
    pred_3y: np.ndarray
) -> pd.DataFrame:
    """
    Convenience function to compute risk scores.

    Parameters
    ----------
    df : pd.DataFrame
        Preprocessed data
    pred_1y : np.ndarray
        1-year return predictions
    pred_3y : np.ndarray
        3-year return predictions

    Returns
    -------
    pd.DataFrame
        Risk scores and components
    """
    scorer = RiskScorer()
    return scorer.compute_risk_scores(df, pred_1y, pred_3y)