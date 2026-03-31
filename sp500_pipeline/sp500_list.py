"""
S&P 500 Universe
=================
Retrieves the current S&P 500 constituent list with ticker-to-CIK mapping.
Uses Wikipedia for the authoritative constituent list and SEC EDGAR for CIK lookup.
"""

import logging
import re
from typing import Optional

import pandas as pd
import requests
from bs4 import BeautifulSoup

from . import config
from .rate_limiter import SECClient

logger = logging.getLogger(__name__)


def _fetch_sp500_from_wikipedia() -> pd.DataFrame:
    """
    Scrape the S&P 500 constituent list from Wikipedia.
    
    Returns:
        DataFrame with columns: ticker, company_name, sector, sub_industry
    """
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    logger.info("Fetching S&P 500 list from Wikipedia...")
    
    headers = {"User-Agent": "Mozilla/5.0 (SP500Pipeline)"}
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, "lxml")
    
    # The first table on the page contains current constituents
    table = soup.find("table", {"id": "constituents"})
    if table is None:
        # Fallback: find by class
        tables = soup.find_all("table", class_="wikitable")
        if tables:
            table = tables[0]
        else:
            raise ValueError("Could not find S&P 500 constituents table on Wikipedia")
    
    rows = []
    header_row = table.find("thead")
    tbody = table.find("tbody")
    if tbody is None:
        tbody = table
    
    for tr in tbody.find_all("tr"):
        cells = tr.find_all("td")
        if len(cells) >= 4:
            ticker = cells[0].get_text(strip=True).replace(".", "-")  # BRK.B → BRK-B
            company_name = cells[1].get_text(strip=True)
            sector = cells[3].get_text(strip=True)
            sub_industry = cells[4].get_text(strip=True) if len(cells) > 4 else ""
            
            rows.append({
                "ticker": ticker,
                "company_name": company_name,
                "sector": sector,
                "sub_industry": sub_industry,
            })
    
    df = pd.DataFrame(rows)
    logger.info(f"Found {len(df)} S&P 500 constituents from Wikipedia")
    return df


def _fetch_cik_mapping(client: SECClient) -> dict:
    """
    Fetch the SEC's official ticker-to-CIK mapping.
    
    Returns:
        Dict mapping uppercase ticker → zero-padded 10-digit CIK string
    """
    logger.info("Fetching SEC ticker-to-CIK mapping...")
    
    data = client.get_json(config.SEC_COMPANY_TICKERS_URL)
    if data is None:
        raise RuntimeError("Failed to fetch SEC company tickers mapping")
    
    cik_map = {}
    for entry in data.values():
        ticker = entry.get("ticker", "").upper()
        cik = entry.get("cik_str", entry.get("cik", ""))
        if ticker and cik:
            # Zero-pad CIK to 10 digits
            cik_map[ticker] = str(cik).zfill(10)
    
    logger.info(f"Loaded CIK mappings for {len(cik_map)} tickers")
    return cik_map


def get_sp500_list(
    client: Optional[SECClient] = None,
    tickers: Optional[list] = None,
) -> pd.DataFrame:
    """
    Build the S&P 500 company universe with CIK mappings.
    
    Args:
        client: SECClient instance (created if None)
        tickers: If provided, filter to only these tickers (for test mode)
        
    Returns:
        DataFrame with columns: ticker, cik, company_name, sector, sub_industry
    """
    own_client = client is None
    if own_client:
        client = SECClient()
    
    try:
        # Step 1: Get S&P 500 list from Wikipedia
        sp500_df = _fetch_sp500_from_wikipedia()
        
        # Step 2: Get CIK mapping from SEC
        cik_map = _fetch_cik_mapping(client)
        
        # Step 3: Map CIKs to tickers
        sp500_df["cik"] = sp500_df["ticker"].str.upper().map(cik_map)
        
        # Handle missing CIKs
        missing = sp500_df[sp500_df["cik"].isna()]
        if len(missing) > 0:
            logger.warning(
                f"{len(missing)} tickers missing CIK mapping: "
                f"{missing['ticker'].tolist()[:10]}..."
            )
            # Try alternate ticker formats (e.g., BRK-B → BRK.B, BRKB)
            for idx, row in missing.iterrows():
                ticker = row["ticker"]
                alternates = [
                    ticker.replace("-", "."),
                    ticker.replace("-", ""),
                    ticker.replace(".", "-"),
                ]
                for alt in alternates:
                    if alt.upper() in cik_map:
                        sp500_df.at[idx, "cik"] = cik_map[alt.upper()]
                        logger.info(f"Resolved {ticker} → {alt} (CIK: {cik_map[alt.upper()]})")
                        break
        
        # Drop companies without CIK (can't fetch EDGAR data)
        before = len(sp500_df)
        sp500_df = sp500_df.dropna(subset=["cik"]).reset_index(drop=True)
        if len(sp500_df) < before:
            logger.warning(f"Dropped {before - len(sp500_df)} companies without CIK mapping")
        
        # Filter to specific tickers if requested (test mode)
        if tickers:
            tickers_upper = [t.upper() for t in tickers]
            sp500_df = sp500_df[sp500_df["ticker"].str.upper().isin(tickers_upper)].reset_index(drop=True)
            logger.info(f"Filtered to {len(sp500_df)} test tickers")
        
        logger.info(f"Final universe: {len(sp500_df)} companies")
        return sp500_df
    
    finally:
        if own_client:
            client.close()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    df = get_sp500_list()
    print(df.head(20))
    print(f"\nTotal: {len(df)} companies")
