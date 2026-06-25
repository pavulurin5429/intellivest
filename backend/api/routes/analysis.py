from __future__ import annotations

import json
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Optional
from loguru import logger
from ...agents.orchestrator import analyze_ticker
from ...utils.db import get_supabase

router = APIRouter(prefix="/api/analyze", tags=["analysis"])

# In-memory cache (primary fast store)
_cache: dict = {}


class AnalysisRequest(BaseModel):
    ticker: str
    agent_weights: Optional[dict] = None


def _persist_to_db(ticker: str, payload: dict) -> None:
    sb = get_supabase()
    if not sb:
        return
    try:
        sb.table("analysis_results").insert({
            "ticker": ticker,
            "decision": payload.get("decision"),
            "conviction": payload.get("conviction"),
            "target_weight": payload.get("target_weight"),
            "credit_score": payload.get("credit_score"),
            "regime": payload.get("regime"),
            "key_thesis": payload.get("key_thesis"),
            "weighted_signal": payload.get("weighted_signal"),
            "agent_outputs": payload.get("agent_outputs", {}),
            "errors": payload.get("errors", []),
        }).execute()
        logger.info(f"Persisted analysis for {ticker} to Supabase")
    except Exception as e:
        logger.warning(f"Supabase persist failed for {ticker}: {e}")


def _load_from_db(ticker: str) -> Optional[dict]:
    sb = get_supabase()
    if not sb:
        return None
    try:
        rows = (
            sb.table("analysis_results")
            .select("*")
            .eq("ticker", ticker)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        if rows.data:
            row = rows.data[0]
            row["status"] = "complete"
            return row
    except Exception as e:
        logger.warning(f"Supabase load failed for {ticker}: {e}")
    return None


@router.post("/{ticker}")
async def run_analysis(ticker: str, background_tasks: BackgroundTasks):
    """
    Trigger a full 5-agent analysis for a ticker.
    Returns immediately. Poll /status/{ticker} for results.
    """
    ticker = ticker.upper()
    _cache[ticker] = {"status": "running", "ticker": ticker}

    def _run():
        try:
            result = analyze_ticker(ticker)
            fm = result.get("fund_manager_result") or {}
            regime = result.get("regime") or {}
            payload = {
                "status": "complete",
                "ticker": ticker,
                "decision": fm.get("decision", "HOLD"),
                "conviction": fm.get("conviction", "LOW"),
                "target_weight": fm.get("target_weight", "0%"),
                "credit_score": result.get("credit_score"),
                "regime": regime.get("current_regime"),
                "key_thesis": fm.get("key_thesis", ""),
                "weighted_signal": fm.get("weighted_signal"),
                "agent_outputs": {
                    "fundamentals": result.get("fundamentals_result"),
                    "technicals": result.get("technicals_result"),
                    "sentiment": result.get("sentiment_result"),
                    "risk_manager": result.get("risk_result"),
                    "fund_manager": fm,
                },
                "errors": result.get("errors", []),
            }
            _cache[ticker] = payload
            _persist_to_db(ticker, payload)
        except Exception as e:
            _cache[ticker] = {"status": "error", "ticker": ticker, "error": str(e)}
            logger.error(f"Analysis failed for {ticker}: {e}")

    background_tasks.add_task(_run)
    return {"status": "running", "ticker": ticker, "message": f"Analysis started for {ticker}"}


@router.get("/status/{ticker}")
async def get_status(ticker: str):
    """Poll for analysis results. Falls back to DB if not in memory."""
    ticker = ticker.upper()
    result = _cache.get(ticker)
    if not result:
        # Try loading last result from Supabase
        db_result = _load_from_db(ticker)
        if db_result:
            _cache[ticker] = db_result
            return db_result
        raise HTTPException(
            status_code=404,
            detail=f"No analysis found for {ticker}. POST to /api/analyze/{ticker} first.",
        )
    return result


@router.get("/result/{ticker}")
async def get_result(ticker: str):
    """Get full analysis result (only available after status == complete)."""
    ticker = ticker.upper()
    result = _cache.get(ticker)
    if not result:
        raise HTTPException(status_code=404, detail=f"No analysis found for {ticker}")
    if result.get("status") != "complete":
        raise HTTPException(status_code=202, detail=f"Analysis still running for {ticker}")
    return result


@router.get("/history/{ticker}")
async def get_history(ticker: str, limit: int = 10):
    """Return past analysis results from Supabase for a given ticker."""
    ticker = ticker.upper()
    sb = get_supabase()
    if not sb:
        raise HTTPException(status_code=503, detail="Database not configured")
    try:
        rows = (
            sb.table("analysis_results")
            .select("id,ticker,decision,conviction,credit_score,regime,key_thesis,created_at")
            .eq("ticker", ticker)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return {"ticker": ticker, "history": rows.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
