"""
Financial feature engineering for the credit scorecard.
Computes 42 ratio features from EDGAR filings + yfinance data.
"""

from __future__ import annotations
import pandas as pd
import numpy as np
from typing import List, Dict
from loguru import logger


def safe_div(a, b, default=np.nan):
    try:
        if b == 0 or b is None or pd.isna(b):
            return default
        return a / b
    except Exception:
        return default


def extract_features(ticker: str, financials: dict, ratios: dict, price_df: pd.DataFrame) -> dict:
    """
    Compute all 42 features for a single ticker.
    financials: output of yfinance_fetcher.fetch_financials()
    ratios: output of yfinance_fetcher.fetch_key_ratios()
    price_df: output of yfinance_fetcher.fetch_price_history()
    """
    f = {}
    f["ticker"] = ticker

    income = financials.get("income_annual", pd.DataFrame())
    balance = financials.get("balance_annual", pd.DataFrame())
    cashflow = financials.get("cashflow_annual", pd.DataFrame())

    def get(df, row, col=0, default=np.nan):
        try:
            return float(df.loc[row].iloc[col])
        except Exception:
            return default

    # --- Liquidity Ratios (5) ---
    current_assets = get(balance, "Current Assets")
    current_liab = get(balance, "Current Liabilities")
    inventory = get(balance, "Inventory")
    cash = get(balance, "Cash And Cash Equivalents")
    total_assets = get(balance, "Total Assets")

    f["current_ratio"] = safe_div(current_assets, current_liab)
    f["quick_ratio"] = safe_div(current_assets - inventory, current_liab)
    f["cash_ratio"] = safe_div(cash, current_liab)
    f["operating_cash_ratio"] = safe_div(get(cashflow, "Operating Cash Flow"), current_liab)
    f["working_capital_ratio"] = safe_div(current_assets - current_liab, total_assets)

    # --- Leverage / Solvency Ratios (7) ---
    total_debt = get(balance, "Total Debt")
    total_equity = get(balance, "Stockholders Equity")
    total_liab = get(balance, "Total Liabilities Net Minority Interest")
    ebit = get(income, "EBIT")
    interest_expense = abs(get(income, "Interest Expense", default=1))
    operating_cf = get(cashflow, "Operating Cash Flow")

    f["debt_to_equity"] = safe_div(total_debt, total_equity)
    f["debt_to_assets"] = safe_div(total_debt, total_assets)
    f["equity_multiplier"] = safe_div(total_assets, total_equity)
    f["interest_coverage"] = safe_div(ebit, interest_expense)
    f["debt_service_coverage"] = safe_div(operating_cf, total_debt)
    f["long_term_debt_ratio"] = safe_div(get(balance, "Long Term Debt"), total_assets)
    f["total_liab_to_equity"] = safe_div(total_liab, total_equity)

    # --- Profitability Ratios (8) ---
    revenue = get(income, "Total Revenue")
    gross_profit = get(income, "Gross Profit")
    net_income = get(income, "Net Income")
    operating_income = get(income, "Operating Income")

    f["gross_margin"] = safe_div(gross_profit, revenue)
    f["operating_margin"] = safe_div(operating_income, revenue)
    f["net_profit_margin"] = safe_div(net_income, revenue)
    f["return_on_assets"] = safe_div(net_income, total_assets)
    f["return_on_equity"] = safe_div(net_income, total_equity)
    f["ebitda_margin"] = safe_div(get(income, "EBITDA"), revenue)
    f["asset_turnover"] = safe_div(revenue, total_assets)
    f["equity_turnover"] = safe_div(revenue, total_equity)

    # --- Cash Flow Ratios (5) ---
    capex = abs(get(cashflow, "Capital Expenditure", default=0))
    free_cf = operating_cf - capex

    f["operating_cf_margin"] = safe_div(operating_cf, revenue)
    f["free_cf_margin"] = safe_div(free_cf, revenue)
    f["capex_ratio"] = safe_div(capex, revenue)
    f["cf_to_debt"] = safe_div(operating_cf, total_debt)
    f["cf_to_assets"] = safe_div(operating_cf, total_assets)

    # --- Efficiency Ratios (5) ---
    cogs = get(income, "Cost Of Revenue")
    receivables = get(balance, "Accounts Receivable")
    payables = get(balance, "Accounts Payable")

    f["inventory_turnover"] = safe_div(cogs, inventory)
    f["receivables_turnover"] = safe_div(revenue, receivables)
    f["payables_turnover"] = safe_div(cogs, payables)
    f["days_sales_outstanding"] = safe_div(365, f["receivables_turnover"])
    f["days_inventory_outstanding"] = safe_div(365, f["inventory_turnover"])

    # --- Growth Ratios (4) ---
    income_q = financials.get("income_quarterly", pd.DataFrame())
    rev_vals = []
    try:
        rev_vals = income_q.loc["Total Revenue"].dropna().values
    except Exception:
        pass

    f["revenue_yoy_growth"] = safe_div(rev_vals[0] - rev_vals[4], abs(rev_vals[4])) if len(rev_vals) > 4 else np.nan
    f["earnings_yoy_growth"] = ratios.get("earnings_growth", np.nan)
    f["revenue_qoq_growth"] = safe_div(rev_vals[0] - rev_vals[1], abs(rev_vals[1])) if len(rev_vals) > 1 else np.nan
    f["operating_cf_growth"] = np.nan  # placeholder — needs prior year cashflow

    # --- Market / Valuation Ratios (5) ---
    f["pe_ratio"] = ratios.get("pe_ratio", np.nan)
    f["pb_ratio"] = ratios.get("pb_ratio", np.nan)
    f["ps_ratio"] = ratios.get("ps_ratio", np.nan)
    f["dividend_yield"] = ratios.get("dividend_yield", np.nan)
    f["beta"] = ratios.get("beta", np.nan)

    # --- Market Volatility Features (3) from price history ---
    if not price_df.empty and len(price_df) > 20:
        returns = price_df["Close"].pct_change().dropna()
        f["volatility_30d"] = returns.tail(30).std() * np.sqrt(252)
        f["volatility_90d"] = returns.tail(90).std() * np.sqrt(252)
        f["price_momentum_90d"] = safe_div(
            price_df["Close"].iloc[-1] - price_df["Close"].iloc[-90],
            price_df["Close"].iloc[-90]
        ) if len(price_df) >= 90 else np.nan
    else:
        f["volatility_30d"] = np.nan
        f["volatility_90d"] = np.nan
        f["price_momentum_90d"] = np.nan

    logger.info(f"Extracted {len(f) - 1} features for {ticker}")
    return f


def build_feature_matrix(ticker_data: list[dict]) -> pd.DataFrame:
    """
    Build a DataFrame where each row is a ticker and columns are the 42 features.
    ticker_data: list of dicts, each from extract_features()
    """
    df = pd.DataFrame(ticker_data)
    df = df.set_index("ticker")

    # Clip extreme outliers at 1st/99th percentile per feature
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        p1, p99 = df[col].quantile(0.01), df[col].quantile(0.99)
        df[col] = df[col].clip(p1, p99)

    logger.info(f"Feature matrix shape: {df.shape}")
    return df
