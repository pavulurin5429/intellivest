"""
One-shot EDGAR ingestion script.
Scrapes 10-K/10-Q filings for top tickers and upserts chunks into Pinecone.
Run from project root: python -m backend.data.ingest_edgar
"""
from __future__ import annotations

import asyncio
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from loguru import logger
from backend.data.edgar_scraper import scrape_tickers_batch
from backend.data.pinecone_store import upsert_filing, get_pinecone_index

TOP_TICKERS = [
    # Mega-cap tech
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "TSLA", "NVDA", "NFLX",
    # Finance
    "JPM", "BAC", "GS", "MS",
    # Healthcare
    "JNJ", "PFE", "UNH",
    # Consumer
    "WMT", "HD", "MCD",
    # Energy
    "XOM", "CVX",
]


async def ingest_all(tickers: list[str]) -> None:
    index = get_pinecone_index()
    stats = index.describe_index_stats()
    logger.info(f"Pinecone index before ingestion: {stats.total_vector_count} vectors")

    logger.info(f"Scraping EDGAR filings for {len(tickers)} tickers...")
    results = await scrape_tickers_batch(tickers, concurrency=3)

    total_chunks = 0
    for company in results:
        ticker = company.get("ticker", "?")
        filings = company.get("filings", [])
        if not filings:
            logger.warning(f"[{ticker}] No filings found — skipping")
            continue

        for filing in filings:
            text = filing.get("text", "")
            if not text or len(text) < 500:
                logger.warning(f"[{ticker}] {filing.get('form')} too short — skipping")
                continue
            try:
                n = upsert_filing(
                    ticker=ticker,
                    form=filing["form"],
                    date=filing["date"],
                    text=text,
                )
                total_chunks += n
                logger.success(f"[{ticker}] {filing['form']} {filing['date']}: {n} chunks upserted")
            except Exception as e:
                logger.error(f"[{ticker}] Upsert failed: {e}")

    stats_after = index.describe_index_stats()
    logger.success(
        f"Ingestion complete. Chunks upserted: {total_chunks}. "
        f"Pinecone total vectors: {stats_after.total_vector_count}"
    )


if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    asyncio.run(ingest_all(TOP_TICKERS))
