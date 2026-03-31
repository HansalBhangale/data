"""
EDGAR Data Fetcher
===================
Fetches company financial data from SEC EDGAR APIs:
  - Company Facts (XBRL JSON) — all structured financial data
  - Submissions — filing metadata (dates, accession numbers, form types)
Both endpoints cache responses to avoid redundant network calls.
"""

import logging
from typing import Optional

from . import config
from .rate_limiter import SECClient

logger = logging.getLogger(__name__)


def fetch_company_facts(
    cik: str,
    client: SECClient,
    force_refresh: bool = False,
) -> Optional[dict]:
    """
    Fetch all XBRL facts for a company from SEC EDGAR.
    
    Endpoint: https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json
    
    This single JSON contains every financial concept ever reported by the
    company in their XBRL filings, including all historical periods.
    
    Args:
        cik: Zero-padded 10-digit CIK string
        client: SECClient instance
        force_refresh: Skip cache and re-download
        
    Returns:
        Parsed JSON dict, or None if the company has no XBRL data
    """
    url = config.SEC_COMPANY_FACTS_URL.format(cik=cik)
    logger.debug(f"Fetching company facts for CIK {cik}")
    
    data = client.get_json(
        url,
        cache_dir=config.CACHE_COMPANY_FACTS_DIR,
        force_refresh=force_refresh,
    )
    
    if data is None:
        logger.warning(f"No company facts data for CIK {cik}")
        return None
    
    # Validate the response has the expected structure
    if "facts" not in data:
        logger.warning(f"CIK {cik}: Response missing 'facts' key")
        return None
    
    return data


def fetch_submissions(
    cik: str,
    client: SECClient,
    force_refresh: bool = False,
) -> Optional[dict]:
    """
    Fetch filing submission metadata for a company.
    
    Endpoint: https://data.sec.gov/submissions/CIK{cik}.json
    
    Returns filing dates, accession numbers, form types, etc.
    Handles pagination for companies with >1000 filings.
    
    Args:
        cik: Zero-padded 10-digit CIK string
        client: SECClient instance
        force_refresh: Skip cache and re-download
        
    Returns:
        Parsed JSON dict with all filings, or None on failure
    """
    url = config.SEC_SUBMISSIONS_URL.format(cik=cik)
    logger.debug(f"Fetching submissions for CIK {cik}")
    
    data = client.get_json(
        url,
        cache_dir=config.CACHE_SUBMISSIONS_DIR,
        force_refresh=force_refresh,
    )
    
    if data is None:
        logger.warning(f"No submissions data for CIK {cik}")
        return None
    
    # Handle pagination: if >1000 filings, additional pages are in 'files'
    if "filings" in data and "files" in data["filings"]:
        recent = data["filings"]["recent"]
        for extra_file in data["filings"]["files"]:
            extra_url = f"{config.SEC_BASE_URL}/submissions/{extra_file['name']}"
            extra_data = client.get_json(extra_url)
            if extra_data is not None:
                # Merge the additional filings into the 'recent' arrays
                for key in recent:
                    if key in extra_data and isinstance(extra_data[key], list):
                        recent[key].extend(extra_data[key])
    
    return data


def get_10q_filing_dates(submissions_data: dict) -> list:
    """
    Extract 10-Q filing dates from submissions data.
    
    Args:
        submissions_data: Parsed submissions JSON
        
    Returns:
        List of dicts with keys: filing_date, report_date, accession_number
    """
    if not submissions_data or "filings" not in submissions_data:
        return []
    
    recent = submissions_data["filings"]["recent"]
    filings = []
    
    forms = recent.get("form", [])
    filing_dates = recent.get("filingDate", [])
    report_dates = recent.get("reportDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    
    for i, form in enumerate(forms):
        if form == "10-Q":
            filings.append({
                "filing_date": filing_dates[i] if i < len(filing_dates) else None,
                "report_date": report_dates[i] if i < len(report_dates) else None,
                "accession_number": accession_numbers[i] if i < len(accession_numbers) else None,
            })
    
    return filings
