#!/usr/bin/env python
"""
S&P 500 Fundamental Analysis Data Pipeline
============================================
Entry point for the production-grade pipeline that retrieves, processes,
and engineers a complete fundamental analysis dataset for S&P 500 companies.

Usage:
    # Full run (all ~500 companies, ~2 hours):
    python run_pipeline.py

    # Test mode (10 companies, ~5 minutes):
    python run_pipeline.py --test

    # Specific tickers only:
    python run_pipeline.py --tickers AAPL,MSFT,GOOGL

    # Force re-download (ignore cache):
    python run_pipeline.py --no-cache

    # Fundamentals only (skip Yahoo Finance market data):
    python run_pipeline.py --skip-market

    # Resume from last checkpoint:
    python run_pipeline.py --resume

    # Fresh start (clear checkpoints):
    python run_pipeline.py --fresh
"""

import argparse
import io
import logging
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sp500_pipeline.pipeline import build_dataset


def setup_logging(verbose: bool = False):
    """Configure logging with both console and file output."""
    # Force UTF-8 for Windows console
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")
    
    log_level = logging.DEBUG if verbose else logging.INFO
    
    # Create formatters (ASCII-safe for Windows console)
    console_fmt = logging.Formatter(
        "%(asctime)s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    file_fmt = logging.Formatter(
        "%(asctime)s | %(name)-25s | %(levelname)-7s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(console_fmt)
    
    # File handler
    log_path = Path(__file__).resolve().parent / "pipeline.log"
    file_handler = logging.FileHandler(log_path, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy third-party loggers
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("yfinance").setLevel(logging.WARNING)
    logging.getLogger("peewee").setLevel(logging.WARNING)


def main():
    parser = argparse.ArgumentParser(
        description="S&P 500 Fundamental Analysis Data Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    
    parser.add_argument(
        "--test", action="store_true",
        help="Test mode: process only 10 companies (AAPL, MSFT, JNJ, JPM, XOM, PG, UNH, V, HD, MA)",
    )
    parser.add_argument(
        "--tickers", type=str, default=None,
        help="Comma-separated list of specific tickers to process (e.g., AAPL,MSFT,GOOGL)",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Force re-download from EDGAR (ignore cached responses)",
    )
    parser.add_argument(
        "--skip-market", action="store_true",
        help="Skip Yahoo Finance market data (fundamentals only)",
    )
    parser.add_argument(
        "--resume", action="store_true", default=True,
        help="Resume from last checkpoint (default behavior)",
    )
    parser.add_argument(
        "--fresh", action="store_true",
        help="Clear all checkpoints and start fresh",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose debug logging",
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(verbose=args.verbose)
    logger = logging.getLogger(__name__)
    
    # Parse tickers
    tickers = None
    if args.tickers:
        tickers = [t.strip().upper() for t in args.tickers.split(",")]
    
    # Banner
    logger.info("")
    logger.info("+==================================================================+")
    logger.info("|     S&P 500 Fundamental Analysis Data Pipeline v1.0.0           |")
    logger.info("+==================================================================+")
    logger.info("")
    
    mode = "TEST" if args.test else ("CUSTOM" if tickers else "FULL")
    logger.info(f"  Mode:           {mode}")
    if tickers:
        logger.info(f"  Tickers:        {', '.join(tickers)}")
    logger.info(f"  Cache:          {'DISABLED' if args.no_cache else 'ENABLED'}")
    logger.info(f"  Market data:    {'SKIP' if args.skip_market else 'ENABLED'}")
    logger.info(f"  Resume:         {'YES' if args.resume and not args.fresh else 'NO'}")
    logger.info("")
    
    try:
        df = build_dataset(
            test_mode=args.test,
            tickers=tickers,
            force_refresh=args.no_cache,
            resume=args.resume and not args.fresh,
            skip_market_data=args.skip_market,
        )
        
        # Print summary statistics
        logger.info("")
        logger.info("Sample of output data:")
        logger.info(f"\n{df.head(3).to_string()}")
        logger.info("")
        logger.info(f"Column list ({len(df.columns)} columns):")
        for i, col in enumerate(df.columns):
            logger.info(f"  {i+1:3d}. {col}")
        
    except KeyboardInterrupt:
        logger.warning("\nPipeline interrupted by user. Progress has been checkpointed.")
        logger.warning("Run with --resume to continue from where you left off.")
        sys.exit(1)
        
    except Exception as e:
        logger.error(f"\nPipeline failed: {e}", exc_info=True)
        logger.error("Run with --resume to retry from the last successful checkpoint.")
        sys.exit(1)


if __name__ == "__main__":
    main()
