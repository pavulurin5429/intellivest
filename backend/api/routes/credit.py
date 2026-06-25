from __future__ import annotations
from fastapi import APIRouter, HTTPException
from loguru import logger
from ...data.yfinance_fetcher import fetch_financials, fetch_key_ratios, fetch_price_history
from ...ml.feature_engineering import extract_features
from ...ml.credit_scorecard import predict_score

router = APIRouter(prefix="/api/credit", tags=["credit"])


@router.get("/{ticker}")
async def get_credit_score(ticker: str):
    """Compute credit risk score for a ticker."""
    ticker = ticker.upper()
    try:
        financials = fetch_financials(ticker)
        ratios = fetch_key_ratios(ticker)
        price_df = fetch_price_history(ticker, period="1y")
        features = extract_features(ticker, financials, ratios, price_df)
        result = predict_score(features.copy())
        return result
    except Exception as e:
        logger.error(f"Credit score error for {ticker}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/batch")
async def batch_credit_scores(tickers: list[str]):
    """Compute credit scores for multiple tickers."""
    results = []
    for ticker in tickers[:50]:  # cap at 50 per request
        try:
            financials = fetch_financials(ticker)
            ratios = fetch_key_ratios(ticker)
            price_df = fetch_price_history(ticker, period="1y")
            features = extract_features(ticker, financials, ratios, price_df)
            score = predict_score(features.copy())
            results.append(score)
        except Exception as e:
            results.append({"ticker": ticker, "error": str(e)})
    return results
