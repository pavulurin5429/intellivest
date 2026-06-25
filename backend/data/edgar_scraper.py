"""
Async SEC EDGAR scraper.
Pulls 10-K and 10-Q filings for a list of tickers using the EDGAR full-text search API.
No API key required — EDGAR is fully public.
"""

from __future__ import annotations
import asyncio
import aiohttp
import json
from typing import Optional, List, Dict
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential


EDGAR_BASE = "https://data.sec.gov"
HEADERS = {"User-Agent": "InvestmentPlatform contact@example.com"}  # EDGAR requires a user-agent


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_cik(session: aiohttp.ClientSession, ticker: str) -> Optional[str]:
    """Map ticker symbol to SEC CIK number."""
    url = f"{EDGAR_BASE}/submissions/CIK{ticker.upper()}.json"
    # Try ticker lookup via company tickers JSON
    lookup_url = "https://www.sec.gov/files/company_tickers.json"
    async with session.get(lookup_url, headers=HEADERS) as resp:
        if resp.status != 200:
            logger.warning(f"Failed to fetch CIK lookup table: {resp.status}")
            return None
        data = await resp.json(content_type=None)
        for entry in data.values():
            if entry.get("ticker", "").upper() == ticker.upper():
                cik = str(entry["cik_str"]).zfill(10)
                logger.info(f"Resolved {ticker} -> CIK {cik}")
                return cik
    logger.warning(f"CIK not found for ticker: {ticker}")
    return None


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_filings_metadata(session: aiohttp.ClientSession, cik: str) -> dict:
    """Fetch all filings metadata for a CIK from EDGAR submissions endpoint."""
    url = f"{EDGAR_BASE}/submissions/CIK{cik}.json"
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            logger.error(f"EDGAR submissions fetch failed for CIK {cik}: {resp.status}")
            return {}
        return await resp.json(content_type=None)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
async def fetch_filing_document(session: aiohttp.ClientSession, url: str) -> str:
    """Download the raw text of a single filing document."""
    async with session.get(url, headers=HEADERS) as resp:
        if resp.status != 200:
            return ""
        return await resp.text(errors="replace")


def extract_recent_filings(metadata: dict, form_types: list[str] = ["10-K", "10-Q"], limit: int = 5) -> list[dict]:
    """Extract the most recent filings of given form types from metadata."""
    filings = []
    recent = metadata.get("filings", {}).get("recent", {})
    if not recent:
        return filings

    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accession_numbers = recent.get("accessionNumber", [])
    primary_docs = recent.get("primaryDocument", [])

    for i, form in enumerate(forms):
        if form in form_types and len(filings) < limit:
            filings.append({
                "form": form,
                "date": dates[i] if i < len(dates) else "",
                "accession": accession_numbers[i].replace("-", "") if i < len(accession_numbers) else "",
                "primary_doc": primary_docs[i] if i < len(primary_docs) else "",
            })

    return filings


async def scrape_ticker(session: aiohttp.ClientSession, ticker: str) -> dict:
    """Full pipeline: ticker -> CIK -> filings metadata -> document text."""
    cik = await fetch_cik(session, ticker)
    if not cik:
        return {"ticker": ticker, "error": "CIK not found", "filings": []}

    metadata = await fetch_filings_metadata(session, cik)
    if not metadata:
        return {"ticker": ticker, "cik": cik, "error": "No metadata", "filings": []}

    company_name = metadata.get("name", ticker)
    recent_filings = extract_recent_filings(metadata, form_types=["10-K", "10-Q"], limit=3)

    results = []
    for filing in recent_filings:
        accession = filing["accession"]
        primary_doc = filing["primary_doc"]
        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession}/{primary_doc}"
        text = await fetch_filing_document(session, doc_url)
        results.append({
            "form": filing["form"],
            "date": filing["date"],
            "url": doc_url,
            "text": text[:50000],  # cap at 50K chars to keep memory manageable
            "text_length": len(text),
        })
        await asyncio.sleep(0.1)  # polite rate limiting for EDGAR

    logger.info(f"Scraped {len(results)} filings for {ticker} ({company_name})")
    return {"ticker": ticker, "cik": cik, "company": company_name, "filings": results}


async def scrape_tickers_batch(tickers: list[str], concurrency: int = 5) -> list[dict]:
    """Scrape multiple tickers concurrently with a semaphore to avoid overwhelming EDGAR."""
    semaphore = asyncio.Semaphore(concurrency)
    connector = aiohttp.TCPConnector(limit=20)

    async def bounded_scrape(ticker: str) -> dict:
        async with semaphore:
            return await scrape_ticker(session, ticker)

    async with aiohttp.ClientSession(connector=connector) as session:
        tasks = [bounded_scrape(t) for t in tickers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    valid = []
    for r in results:
        if isinstance(r, Exception):
            logger.error(f"Scrape error: {r}")
        else:
            valid.append(r)

    return valid


# Quick test when run directly
if __name__ == "__main__":
    test_tickers = ["AAPL", "MSFT", "JPM"]
    results = asyncio.run(scrape_tickers_batch(test_tickers))
    for r in results:
        print(f"{r['ticker']}: {len(r.get('filings', []))} filings, company={r.get('company')}")
