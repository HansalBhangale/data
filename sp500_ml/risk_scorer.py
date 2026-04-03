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
    6. Model Uncertainty (15%): prediction spread / std of predictions
    """

    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or RISK_WEIGHTS
        self.fitted_ = False

    # ------------------------------------------------------------------
    # HELPER: percentile-rank a raw composite score → 0-100
    # ------------------------------------------------------------------
    @staticmethod
    def _to_pct_rank(series: pd.Series) -> pd.Series:
        """Convert a raw series to percentile rank 0-100. NaN → 50 (median risk)."""
        ranked = series.rank(pct=True, na_option='keep') * 100
        return ranked.fillna(50)

    # ------------------------------------------------------------------
    # COMPONENT 1: Leverage Risk
    # Higher debt = higher score = higher risk
    # ------------------------------------------------------------------
    def _compute_leverage_risk(self, df: pd.DataFrame) -> pd.Series:
        parts = []

        if 'debt_to_equity' in df.columns:
            parts.append(df['debt_to_equity'].fillna(df['debt_to_equity'].median()))

        if 'leverage_ratio' in df.columns:
            parts.append(df['leverage_ratio'].fillna(df['leverage_ratio'].median()))

        if 'net_debt' in df.columns and 'ebitda_ttm' in df.columns:
            nd_ebitda = (df['net_debt'] / df['ebitda_ttm'].replace(0, np.nan)).clip(-10, 10)
            parts.append(nd_ebitda.fillna(nd_ebitda.median()))

        if not parts:
            return pd.Series(50.0, index=df.index)

        # Average the raw components, then percentile-rank the composite
        composite = sum(parts) / len(parts)
        return self._to_pct_rank(composite)

    # ------------------------------------------------------------------
    # COMPONENT 2: Liquidity Risk
    # Lower liquidity = higher score = higher risk → invert before ranking
    # ------------------------------------------------------------------
    def _compute_liquidity_risk(self, df: pd.DataFrame) -> pd.Series:
        parts = []

        if 'current_ratio' in df.columns:
            # Invert: low current_ratio → high risk
            parts.append(-df['current_ratio'].fillna(df['current_ratio'].median()))

        if 'cash_ratio' in df.columns:
            parts.append(-df['cash_ratio'].fillna(df['cash_ratio'].median()))

        if not parts:
            return pd.Series(50.0, index=df.index)

        composite = sum(parts) / len(parts)
        return self._to_pct_rank(composite)

    # ------------------------------------------------------------------
    # COMPONENT 3: Profitability Risk
    # Lower profitability = higher risk → invert before ranking
    # ------------------------------------------------------------------
    def _compute_profitability_risk(self, df: pd.DataFrame) -> pd.Series:
        parts = []

        if 'roe' in df.columns:
            parts.append(-df['roe'].fillna(df['roe'].median()))

        if 'roa' in df.columns:
            parts.append(-df['roa'].fillna(df['roa'].median()))

        if 'operating_margin' in df.columns:
            parts.append(-df['operating_margin'].fillna(df['operating_margin'].median()))

        if 'net_margin' in df.columns:
            parts.append(-df['net_margin'].fillna(df['net_margin'].median()))

        if not parts:
            return pd.Series(50.0, index=df.index)

        composite = sum(parts) / len(parts)
        return self._to_pct_rank(composite)

    # ------------------------------------------------------------------
    # COMPONENT 4: Earnings Volatility
    # Higher volatility = higher risk (already works; keep rank approach)
    # ------------------------------------------------------------------
    def _compute_earnings_volatility(self, df: pd.DataFrame) -> pd.Series:
        parts = []

        if 'revenue_growth_vol' in df.columns:
            parts.append(df['revenue_growth_vol'].fillna(df['revenue_growth_vol'].median()))

        if 'net_income_vol' in df.columns:
            parts.append(df['net_income_vol'].fillna(df['net_income_vol'].median()))

        if 'operating_margin_vol' in df.columns:
            parts.append(df['operating_margin_vol'].fillna(df['operating_margin_vol'].median()))

        if 'return_volatility' in df.columns:
            parts.append(df['return_volatility'].fillna(df['return_volatility'].median()))

        if not parts:
            return pd.Series(50.0, index=df.index)

        composite = sum(parts) / len(parts)
        return self._to_pct_rank(composite)

    # ------------------------------------------------------------------
    # COMPONENT 5: Valuation Risk
    # Higher sector-relative valuation = higher risk
    # ------------------------------------------------------------------
    def _compute_valuation_risk(self, df: pd.DataFrame) -> pd.Series:
        parts = []

        pe_col = 'pe_ratio_sector_zscore' if 'pe_ratio_sector_zscore' in df.columns else 'pe_ratio'
        if pe_col in df.columns:
            parts.append(df[pe_col].fillna(df[pe_col].median()))

        pb_col = 'pb_ratio_sector_zscore' if 'pb_ratio_sector_zscore' in df.columns else 'pb_ratio'
        if pb_col in df.columns:
            parts.append(df[pb_col].fillna(df[pb_col].median()))

        ev_col = 'ev_ebitda_sector_zscore' if 'ev_ebitda_sector_zscore' in df.columns else 'ev_ebitda'
        if ev_col in df.columns:
            parts.append(df[ev_col].fillna(df[ev_col].median()))

        if not parts:
            return pd.Series(50.0, index=df.index)

        composite = sum(parts) / len(parts)
        return self._to_pct_rank(composite)

    # ------------------------------------------------------------------
    # COMPONENT 6: Model Uncertainty  ← FIX for Bug 1
    # Old: |pred_1y - pred_3y/3| which = 0 when pred_3y = pred_1y * 3
    # New: uses prediction spread relative to cross-sectional std,
    #      so it's always non-zero and meaningful
    # ------------------------------------------------------------------
    def _compute_model_uncertainty(
        self,
        df: pd.DataFrame,
        pred_1y: np.ndarray,
        pred_3y: np.ndarray
    ) -> pd.Series:
        pred_1y = np.asarray(pred_1y, dtype=float)
        pred_3y = np.asarray(pred_3y, dtype=float)

        # --- Measure 1: absolute divergence between the two horizons ---
        # Annualise 3y pred and compare to 1y pred
        annualised_3y = pred_3y / 3.0
        divergence = np.abs(pred_1y - annualised_3y)

        # --- Measure 2: how extreme the 1y prediction is ---
        # Companies far from the median predicted return are more uncertain
        # (the model is extrapolating more)
        pred_1y_zscore = np.abs(pred_1y - np.nanmedian(pred_1y))

        # Combine: use divergence only when it has variance
        # (if pred_3y was a scaled copy of pred_1y, divergence = 0 → rely on extremity)
        if np.std(divergence) < 1e-8:
            # Fallback: use prediction extremity as the uncertainty proxy
            composite = pd.Series(pred_1y_zscore, index=df.index)
        else:
            # Blend both signals equally
            div_series = pd.Series(divergence, index=df.index)
            ext_series = pd.Series(pred_1y_zscore, index=df.index)
            # Rank each independently then average (avoids scale mismatch)
            composite = (
                div_series.rank(pct=True) + ext_series.rank(pct=True)
            ) / 2 * 100

        return self._to_pct_rank(composite)

    # ------------------------------------------------------------------
    # PUBLIC API: fit / compute / validate  (unchanged signatures)
    # ------------------------------------------------------------------
    def fit(self, df, pred_1y, pred_3y):
        self.fitted_ = True
        return self

    def compute_risk_scores(
        self,
        df: pd.DataFrame,
        pred_1y: np.ndarray,
        pred_3y: np.ndarray
    ) -> pd.DataFrame:
        if not self.fitted_:
            self.fit(df, pred_1y, pred_3y)

        leverage_risk      = self._compute_leverage_risk(df)
        liquidity_risk     = self._compute_liquidity_risk(df)
        profitability_risk = self._compute_profitability_risk(df)
        earnings_volatility= self._compute_earnings_volatility(df)
        valuation_risk     = self._compute_valuation_risk(df)
        model_uncertainty  = self._compute_model_uncertainty(df, pred_1y, pred_3y)

        total_risk = (
            self.weights['leverage_risk']      * leverage_risk +
            self.weights['liquidity_risk']     * liquidity_risk +
            self.weights['profitability_risk'] * profitability_risk +
            self.weights['earnings_volatility']* earnings_volatility +
            self.weights['valuation_risk']     * valuation_risk +
            self.weights['model_uncertainty']  * model_uncertainty
        ).clip(0, 100)

        return pd.DataFrame({
            'risk_score':          total_risk,
            'leverage_risk':       leverage_risk,
            'liquidity_risk':      liquidity_risk,
            'profitability_risk':  profitability_risk,
            'earnings_volatility': earnings_volatility,
            'valuation_risk':      valuation_risk,
            'model_uncertainty':   model_uncertainty,
        })

    def validate_risk_scores(
        self,
        risk_df: pd.DataFrame,
        df: pd.DataFrame,
        target_col: str = 'excess_return_1y'
    ) -> Dict:
        risk_df = risk_df.copy()
        risk_df['risk_quartile'] = pd.qcut(
            risk_df['risk_score'], 4, labels=['Q1', 'Q2', 'Q3', 'Q4']
        )
        risk_df['actual_return'] = df[target_col].values

        vol_by_quartile = risk_df.groupby('risk_quartile')['actual_return'].agg(
            ['mean', 'std', 'count']
        )
        correlation = risk_df['risk_score'].corr(df[target_col])

        quartile_stds = [vol_by_quartile.loc[q, 'std'] for q in ['Q1', 'Q2', 'Q3', 'Q4']]
        monotonic = all(quartile_stds[i] <= quartile_stds[i+1] for i in range(3))

        metrics = {
            'correlation_with_return': correlation,
            'quartile_stats': vol_by_quartile.to_dict(),
            'quartile_monotonic': monotonic,
        }

        print("\nRisk Score Validation:")
        print(f"  Correlation with return: {correlation:.4f}")
        print(f"  Score range: {risk_df['risk_score'].min():.1f} – {risk_df['risk_score'].max():.1f}")
        print(f"  Score std: {risk_df['risk_score'].std():.2f}")
        print(f"  Quartile monotonic (risk increases with vol): {monotonic}")
        print("\n  Return by Risk Quartile:")
        print(vol_by_quartile.to_string())

        return metrics


def compute_risk_score(df, pred_1y, pred_3y):
    scorer = RiskScorer()
    return scorer.compute_risk_scores(df, pred_1y, pred_3y)