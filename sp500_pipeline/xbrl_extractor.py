"""
XBRL Data Extractor
====================
Extracts structured quarterly financial data from SEC EDGAR company facts JSON.
Handles the complex mapping of XBRL tags with priority-ordered fallbacks,
fiscal period alignment, deduplication of restatements, and unit normalization.
"""

import logging
from typing import Optional

import numpy as np
import pandas as pd

from . import config
from .edgar_fetcher import fetch_company_facts
from .rate_limiter import SECClient

logger = logging.getLogger(__name__)


def _extract_fact_series(
    facts: dict,
    tags: list,
    start_year: int = config.START_YEAR,
    form_filter: str = "10-Q",
) -> pd.DataFrame:
    """
    Extract a time series for a financial concept from company facts.
    
    Tries multiple XBRL tags in priority order and returns the first
    one that has data. Handles both 'us-gaap' and 'dei' taxonomies.
    
    Args:
        facts: The 'facts' dict from company facts JSON
        tags: Priority-ordered list of XBRL tag names to try
        start_year: Only include data from this year onward
        form_filter: Filing form type to filter ("10-Q", "10-K", or None for all)
        
    Returns:
        DataFrame with columns: value, end, start, fy, fp, form, filed, tag_used
        Empty DataFrame if no data found for any tag.
    """
    taxonomies = {
        "us-gaap": facts.get("us-gaap", {}),
        "dei": facts.get("dei", {}),
        "ifrs-full": facts.get("ifrs-full", {}),
    }
    
    for tag in tags:
        # Determine which taxonomy this tag belongs to
        if tag in config.DEI_TAGS:
            taxonomy_name = "dei"
        else:
            taxonomy_name = "us-gaap"
        
        taxonomy_data = taxonomies.get(taxonomy_name, {})
        tag_data = taxonomy_data.get(tag)
        
        if tag_data is None:
            continue
        
        units = tag_data.get("units", {})
        
        # Try USD first, then USD/shares, then pure number
        records = []
        for unit_key in ["USD", "USD/shares", "shares", "pure"]:
            if unit_key in units:
                records = units[unit_key]
                break
        
        if not records:
            continue
        
        # Parse records into structured data
        rows = []
        for rec in records:
            fy = rec.get("fy")
            fp = rec.get("fp", "")
            form = rec.get("form", "")
            end = rec.get("end", "")
            start = rec.get("start", "")
            filed = rec.get("filed", "")
            val = rec.get("val")
            
            # Filter by year
            if fy is not None and int(fy) < start_year:
                continue
            
            # Filter by form type
            if form_filter and form != form_filter:
                continue
            
            # Filter to quarterly periods only (not annual aggregates in 10-Q)
            # Quarterly facts have fp in (Q1, Q2, Q3, Q4)
            if fp not in ("Q1", "Q2", "Q3", "Q4"):
                continue
            
            # CRITICAL: Filter by duration to distinguish single-quarter vs
            # cumulative (YTD) values. Flow metrics (revenue, income, cash flow)
            # have both in XBRL. We want ~90 day (single quarter) durations.
            # Balance sheet items (point-in-time) have no start date.
            if start and end:
                try:
                    start_dt = pd.Timestamp(start)
                    end_dt = pd.Timestamp(end)
                    duration_days = (end_dt - start_dt).days
                    # Keep only single-quarter durations (60-120 days)
                    # Reject cumulative/YTD values (>120 days)
                    if duration_days > 120:
                        continue
                except (ValueError, TypeError):
                    pass
            
            rows.append({
                "value": val,
                "end": end,
                "start": start,
                "fy": fy,
                "fp": fp,
                "form": form,
                "filed": filed,
                "tag_used": tag,
            })
        
        if rows:
            df = pd.DataFrame(rows)
            df["end"] = pd.to_datetime(df["end"], errors="coerce")
            df["filed"] = pd.to_datetime(df["filed"], errors="coerce")
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            return df
    
    return pd.DataFrame()


def _extract_fact_series_flexible(
    facts: dict,
    tags: list,
    start_year: int = config.START_YEAR,
) -> pd.DataFrame:
    """
    Extract facts with flexible form filtering.
    Tries 10-Q first, then falls back to allowing 10-K data
    for balance sheet items which may only appear in annual filings
    for some companies.
    """
    # Try 10-Q first
    df = _extract_fact_series(facts, tags, start_year, form_filter="10-Q")
    if not df.empty:
        return df
    
    # Fallback: also accept 10-K filings
    df = _extract_fact_series(facts, tags, start_year, form_filter="10-K")
    if not df.empty:
        # For 10-K, we need to filter to quarterly-like periods
        # Some companies only file annual but tag individual quarters
        return df
    
    return pd.DataFrame()


def _deduplicate_facts(df: pd.DataFrame) -> pd.DataFrame:
    """
    Deduplicate facts for the same period.
    When a company restates financials, there may be multiple values
    for the same (end, fp) pair. We keep the most recently filed value.
    """
    if df.empty:
        return df
    
    # Sort by period end date and filing date, keep latest filing
    df = df.sort_values(["end", "filed"], ascending=[True, False])
    df = df.drop_duplicates(subset=["end"], keep="first")
    return df.sort_values("end").reset_index(drop=True)


def extract_xbrl(
    cik: str,
    ticker: str,
    client: SECClient,
    force_refresh: bool = False,
) -> Optional[pd.DataFrame]:
    """
    Extract all quarterly financial data for a single company.
    
    Fetches the company facts JSON from EDGAR, then extracts each
    financial metric using the priority-ordered XBRL tag fallback map.
    
    Args:
        cik: Zero-padded 10-digit CIK
        ticker: Stock ticker symbol
        client: SECClient instance
        force_refresh: Skip cache
        
    Returns:
        DataFrame with one row per quarter, columns for each financial metric.
        Returns None if no data could be extracted.
    """
    # Fetch raw company facts
    company_data = fetch_company_facts(cik, client, force_refresh)
    if company_data is None:
        return None
    
    facts = company_data.get("facts", {})
    entity_name = company_data.get("entityName", ticker)
    
    # Extract each financial metric
    metric_dfs = {}
    
    for metric_name, tags in config.XBRL_TAG_MAP.items():
        df = _extract_fact_series_flexible(facts, tags)
        if not df.empty:
            df = _deduplicate_facts(df)
            metric_dfs[metric_name] = df[["end", "value", "fy", "fp", "tag_used"]].rename(
                columns={"value": metric_name, "tag_used": f"{metric_name}_tag"}
            )
    
    if not metric_dfs:
        logger.warning(f"{ticker} (CIK {cik}): No XBRL data extracted")
        return None
    
    # Merge all metrics on quarter end date
    # Start with the metric that has the most data points
    sorted_metrics = sorted(metric_dfs.items(), key=lambda x: len(x[1]), reverse=True)
    
    # Use the most populated metric as the base
    base_name, base_df = sorted_metrics[0]
    result = base_df.copy()
    
    for metric_name, metric_df in sorted_metrics[1:]:
        # Only merge the value and tag columns (fy/fp come from base)
        merge_cols = ["end", metric_name]
        if f"{metric_name}_tag" in metric_df.columns:
            merge_cols.append(f"{metric_name}_tag")
        
        result = result.merge(
            metric_df[merge_cols],
            on="end",
            how="outer",
        )
    
    if result.empty:
        return None
    
    # Fill fy/fp from any available source for rows added via outer joins
    if "fy" in result.columns:
        result["fy"] = result["fy"].ffill().bfill()
    if "fp" in result.columns:
        result["fp"] = result["fp"].ffill().bfill()
    
    # Add company identifiers
    result.insert(0, "ticker", ticker)
    result.insert(1, "cik", cik)
    result.insert(2, "entity_name", entity_name)
    
    # Rename 'end' to 'quarter_end' for clarity
    result = result.rename(columns={"end": "quarter_end"})
    
    # Sort by date
    result = result.sort_values("quarter_end").reset_index(drop=True)
    
    # Compute derived raw metrics that need multiple base values
    # Gross Profit = Revenue - Cost of Revenue (if not directly available)
    if "gross_profit" not in result.columns or result["gross_profit"].isna().all():
        if "revenue" in result.columns and "cost_of_revenue" in result.columns:
            result["gross_profit"] = result["revenue"] - result["cost_of_revenue"]
    
    # Total Debt = Long-term debt + Short-term debt
    if "total_debt" not in result.columns or result["total_debt"].isna().all():
        ltd = result.get("long_term_debt", pd.Series(dtype=float))
        std = result.get("short_term_debt", pd.Series(dtype=float))
        result["total_debt"] = ltd.fillna(0) + std.fillna(0)
        # If both are NaN, make total_debt NaN too
        both_na = ltd.isna() & std.isna()
        result.loc[both_na, "total_debt"] = np.nan
    
    # EBITDA = Operating Income + D&A
    if "operating_income" in result.columns:
        da = result.get("depreciation_amortization", pd.Series(dtype=float))
        result["ebitda"] = result["operating_income"] + da.fillna(0)
        # If operating income is NaN, EBITDA should be NaN too
        result.loc[result["operating_income"].isna(), "ebitda"] = np.nan
    
    # Free Cash Flow = Operating Cash Flow - CapEx
    if "operating_cash_flow" in result.columns and "capital_expenditures" in result.columns:
        # CapEx is typically reported as positive in XBRL, so we subtract
        result["free_cash_flow"] = result["operating_cash_flow"] - result["capital_expenditures"].abs()
    
    # Drop internal tag tracking columns from output
    tag_cols = [c for c in result.columns if c.endswith("_tag")]
    result = result.drop(columns=tag_cols, errors="ignore")
    
    # Drop the 'dei' duplicate shares column
    if "shares_outstanding_dei" in result.columns:
        if "shares_outstanding" not in result.columns or result["shares_outstanding"].isna().all():
            result["shares_outstanding"] = result["shares_outstanding_dei"]
        result = result.drop(columns=["shares_outstanding_dei"], errors="ignore")
    
    logger.info(
        f"{ticker}: Extracted {len(result)} quarters, "
        f"{result.columns.tolist()[:8]}..."
    )
    
    return result
