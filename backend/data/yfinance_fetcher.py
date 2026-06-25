"""
yfinance data fetcher.
Pulls historical prices, financial statements, and key ratios — all free via Yahoo Finance.
"""

from __future__ import annotations
import yfinance as yf
import pandas as pd
from typing import Optional, List, Dict
from loguru import logger


def fetch_price_history(ticker: str, period: str = "3y", interval: str = "1d") -> pd.DataFrame:
    """Fetch OHLCV price history for a ticker."""
    try:
        t = yf.Ticker(ticker)
        df = t.history(period=period, interval=interval)
        if df.empty:
            logger.warning(f"No price data for {ticker}")
            return pd.DataFrame()
        df.index = pd.to_datetime(df.index)
        logger.info(f"Fetched {len(df)} price rows for {ticker}")
        return df
    except Exception as e:
        logger.error(f"Price fetch failed for {ticker}: {e}")
        return pd.DataFrame()


def fetch_financials(ticker: str) -> dict:
    """
    Fetch income statement, balance sheet, and cash flow statement.
    Returns annual and quarterly data as DataFrames inside a dict.
    """
    try:
        t = yf.Ticker(ticker)
        return {
            "income_annual": t.financials,
            "income_quarterly": t.quarterly_financials,
            "balance_annual": t.balance_sheet,
            "balance_quarterly": t.quarterly_balance_sheet,
            "cashflow_annual": t.cashflow,
            "cashflow_quarterly": t.quarterly_cashflow,
        }
    except Exception as e:
        logger.error(f"Financials fetch failed for {ticker}: {e}")
        return {}


def fetch_key_ratios(ticker: str) -> dict:
    """
    Fetch key ratios and info from yfinance (P/E, P/B, debt/equity, etc.)
    These supplement EDGAR-derived features in the credit scorecard.
    """
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            "ticker": ticker,
            "sector": info.get("sector"),
            "industry": info.get("industry"),
            "market_cap": info.get("marketCap"),
            "pe_ratio": info.get("trailingPE"),
            "pb_ratio": info.get("priceToBook"),
            "ps_ratio": info.get("priceToSalesTrailing12Months"),
            "debt_to_equity": info.get("debtToEquity"),
            "current_ratio": info.get("currentRatio"),
            "quick_ratio": info.get("quickRatio"),
            "return_on_equity": info.get("returnOnEquity"),
            "return_on_assets": info.get("returnOnAssets"),
            "profit_margin": info.get("profitMargins"),
            "operating_margin": info.get("operatingMargins"),
            "revenue_growth": info.get("revenueGrowth"),
            "earnings_growth": info.get("earningsGrowth"),
            "dividend_yield": info.get("dividendYield"),
            "beta": info.get("beta"),
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }
    except Exception as e:
        logger.error(f"Key ratios fetch failed for {ticker}: {e}")
        return {"ticker": ticker, "error": str(e)}


def fetch_batch(tickers: list[str]) -> dict[str, dict]:
    """Fetch key ratios for multiple tickers. Returns dict keyed by ticker."""
    results = {}
    for ticker in tickers:
        results[ticker] = fetch_key_ratios(ticker)
    return results


if __name__ == "__main__":
    data = fetch_key_ratios("AAPL")
    print(data)

    prices = fetch_price_history("AAPL", period="1y")
    print(prices.tail())
