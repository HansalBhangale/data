"""
Pipeline Orchestrator
======================
Main pipeline that ties all modules together with checkpoint/resume support.
Orchestrates the full ETL flow from data retrieval to final CSV output.
"""

import logging
import sys
import time
from pathlib import Path
from typing import Optional

import pandas as pd
from tqdm import tqdm

from . import config
from .rate_limiter import SECClient
from .sp500_list import get_sp500_list
from .edgar_fetcher import fetch_company_facts
from .xbrl_extractor import extract_xbrl
from .feature_engineer import compute_features
from .market_data import fetch_market_data, fetch_spy_data, compute_valuation_metrics
from .target_generator import compute_targets
from .normalizer import normalize_and_clean

logger = logging.getLogger(__name__)


class PipelineCheckpoint:
    """Manages checkpoint files for pipeline resume support."""
    
    def __init__(self, checkpoint_dir: Path = config.CHECKPOINT_DIR):
        self.checkpoint_dir = checkpoint_dir
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    def save(self, name: str, df: pd.DataFrame):
        """Save a DataFrame checkpoint as parquet."""
        path = self.checkpoint_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        logger.info(f"Checkpoint saved: {name} ({len(df)} rows)")
    
    def load(self, name: str) -> Optional[pd.DataFrame]:
        """Load a checkpoint if it exists."""
        path = self.checkpoint_dir / f"{name}.parquet"
        if path.exists():
            df = pd.read_parquet(path)
            logger.info(f"Checkpoint loaded: {name} ({len(df)} rows)")
            return df
        return None
    
    def exists(self, name: str) -> bool:
        """Check if a checkpoint exists."""
        return (self.checkpoint_dir / f"{name}.parquet").exists()
    
    def clear(self):
        """Remove all checkpoints."""
        for f in self.checkpoint_dir.glob("*.parquet"):
            f.unlink()
        logger.info("All checkpoints cleared")


def build_dataset(
    test_mode: bool = False,
    tickers: Optional[list] = None,
    force_refresh: bool = False,
    resume: bool = True,
    skip_market_data: bool = False,
) -> pd.DataFrame:
    """
    Build the complete S&P 500 fundamental analysis dataset.
    
    Pipeline stages:
      1. Get S&P 500 company universe
      2. Fetch XBRL financial data from EDGAR
      3. Extract and structure quarterly financials
      4. Compute derived features
      5. Fetch market/price data (optional)
      6. Compute valuation metrics & target variables
      7. Normalize and clean
      8. Save to CSV
    
    Args:
        test_mode: If True, only process 10 test tickers
        tickers: Specific tickers to process (overrides test_mode)
        force_refresh: Re-download all data from EDGAR (ignore cache)
        resume: Resume from last checkpoint if available
        skip_market_data: Skip Yahoo Finance data (fundamentals only)
        
    Returns:
        Final DataFrame
    """
    start_time = time.time()
    checkpoint = PipelineCheckpoint()
    
    if not resume:
        checkpoint.clear()
    
    # ══════════════════════════════════════════════════════════════
    # Stage 1: Get S&P 500 Universe
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 70)
    logger.info("STAGE 1: Building S&P 500 company universe")
    logger.info("=" * 70)
    
    if resume and checkpoint.exists("01_sp500_list"):
        sp500_df = checkpoint.load("01_sp500_list")
    else:
        with SECClient() as client:
            if tickers:
                sp500_df = get_sp500_list(client=client, tickers=tickers)
            elif test_mode:
                sp500_df = get_sp500_list(client=client, tickers=config.TEST_TICKERS)
            else:
                sp500_df = get_sp500_list(client=client)
        
        checkpoint.save("01_sp500_list", sp500_df)
    
    logger.info(f"Universe: {len(sp500_df)} companies")
    
    # ══════════════════════════════════════════════════════════════
    # Stage 2-3: Fetch EDGAR Data & Extract XBRL Financials
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 70)
    logger.info("STAGE 2-3: Fetching EDGAR data & extracting XBRL financials")
    logger.info("=" * 70)
    
    if resume and checkpoint.exists("03_raw_financials"):
        raw_financials = checkpoint.load("03_raw_financials")
    else:
        all_company_data = []
        failed_tickers = []
        
        with SECClient() as client:
            for _, row in tqdm(
                sp500_df.iterrows(),
                total=len(sp500_df),
                desc="Extracting XBRL data",
                file=sys.stdout,
            ):
                ticker = row["ticker"]
                cik = row["cik"]
                
                try:
                    company_df = extract_xbrl(cik, ticker, client, force_refresh=force_refresh)
                    if company_df is not None and not company_df.empty:
                        # Add sector/industry metadata
                        company_df["sector"] = row.get("sector", "")
                        company_df["sub_industry"] = row.get("sub_industry", "")
                        all_company_data.append(company_df)
                    else:
                        failed_tickers.append(ticker)
                        
                except Exception as e:
                    logger.error(f"{ticker}: Extraction failed: {e}")
                    failed_tickers.append(ticker)
        
        if not all_company_data:
            raise RuntimeError("No financial data extracted for any company!")
        
        raw_financials = pd.concat(all_company_data, ignore_index=True)
        checkpoint.save("03_raw_financials", raw_financials)
        
        logger.info(
            f"Extracted data for {raw_financials['ticker'].nunique()} companies. "
            f"Failed: {len(failed_tickers)} ({failed_tickers[:10]})"
        )
    
    # ══════════════════════════════════════════════════════════════
    # Stage 4: Feature Engineering
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 70)
    logger.info("STAGE 4: Computing derived features")
    logger.info("=" * 70)
    
    if resume and checkpoint.exists("04_features"):
        featured_df = checkpoint.load("04_features")
    else:
        featured_df = compute_features(raw_financials)
        checkpoint.save("04_features", featured_df)
    
    # ══════════════════════════════════════════════════════════════
    # Stage 5: Market Data & Valuation Metrics
    # ══════════════════════════════════════════════════════════════
    if not skip_market_data:
        logger.info("=" * 70)
        logger.info("STAGE 5: Fetching market data & computing valuations")
        logger.info("=" * 70)
        
        if resume and checkpoint.exists("05_with_market"):
            merged_df = checkpoint.load("05_with_market")
            spy_df = checkpoint.load("05_spy")
            if spy_df is None:
                spy_df = pd.DataFrame()
        else:
            tickers_list = featured_df["ticker"].unique().tolist()
            market_df = fetch_market_data(tickers_list)
            spy_df = fetch_spy_data()
            
            if not market_df.empty:
                merged_df = compute_valuation_metrics(featured_df, market_df)
            else:
                merged_df = featured_df.copy()
                logger.warning("No market data available — skipping valuation metrics")
            
            checkpoint.save("05_with_market", merged_df)
            if not spy_df.empty:
                checkpoint.save("05_spy", spy_df)
    else:
        merged_df = featured_df.copy()
        spy_df = pd.DataFrame()
        logger.info("Skipping market data (fundamentals only mode)")
    
    # ══════════════════════════════════════════════════════════════
    # Stage 6: Target Variables
    # ══════════════════════════════════════════════════════════════
    if not skip_market_data:
        logger.info("=" * 70)
        logger.info("STAGE 6: Computing target variables")
        logger.info("=" * 70)
        
        if resume and checkpoint.exists("06_with_targets"):
            final_df = checkpoint.load("06_with_targets")
        else:
            final_df = compute_targets(merged_df, spy_df)
            checkpoint.save("06_with_targets", final_df)
    else:
        final_df = merged_df.copy()
    
    # ══════════════════════════════════════════════════════════════
    # Stage 7: Normalize & Clean
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 70)
    logger.info("STAGE 7: Normalizing and cleaning dataset")
    logger.info("=" * 70)
    
    final_df = normalize_and_clean(final_df)
    
    # ══════════════════════════════════════════════════════════════
    # Stage 8: Save Output
    # ══════════════════════════════════════════════════════════════
    logger.info("=" * 70)
    logger.info("STAGE 8: Saving final dataset")
    logger.info("=" * 70)
    
    output_path = config.OUTPUT_DIR / config.OUTPUT_FILENAME
    final_df.to_csv(output_path, index=False)
    
    elapsed = time.time() - start_time
    elapsed_min = elapsed / 60
    
    logger.info(f"")
    logger.info(f"{'=' * 70}")
    logger.info(f"  PIPELINE COMPLETE")
    logger.info(f"{'=' * 70}")
    logger.info(f"  Output:     {output_path}")
    logger.info(f"  Rows:       {len(final_df):,}")
    logger.info(f"  Companies:  {final_df['ticker'].nunique()}")
    logger.info(f"  Quarters:   {final_df['quarter_label'].nunique() if 'quarter_label' in final_df.columns else 'N/A'}")
    logger.info(f"  Columns:    {len(final_df.columns)}")
    logger.info(f"  File size:  {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    logger.info(f"  Time:       {elapsed_min:.1f} minutes")
    logger.info(f"{'=' * 70}")
    
    return final_df
