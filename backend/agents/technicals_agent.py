"""
Technicals Agent.
Analyzes price action, momentum indicators, and HMM market regime.
Produces a technical thesis with confidence score.
"""

import pandas as pd
import numpy as np
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from ..utils.config import get_settings
from loguru import logger


SYSTEM_PROMPT = """You are a quantitative technical analyst at a top hedge fund.
Your role is to analyze price action, momentum, trend, and market regime signals.

For each analysis you must:
1. Assess the current price trend (uptrend / downtrend / sideways)
2. Evaluate momentum (RSI, MACD signals)
3. Note key support/resistance levels
4. Factor in the current market regime (Bull/Bear/Sideways)
5. Form a clear technical thesis (BULLISH / BEARISH / NEUTRAL) with confidence 0-100

Be specific with numbers. Cite indicator values. Be direct."""


def compute_indicators(price_df: pd.DataFrame) -> dict:
    """Compute RSI, MACD, Bollinger Bands, and moving averages."""
    close = price_df["Close"]

    # Moving averages
    ma_20 = close.rolling(20).mean().iloc[-1]
    ma_50 = close.rolling(50).mean().iloc[-1]
    ma_200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else None
    current_price = close.iloc[-1]

    # RSI (14-period)
    delta = close.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss
    rsi = float(100 - (100 / (1 + rs)).iloc[-1])

    # MACD
    ema12 = close.ewm(span=12, adjust=False).mean()
    ema26 = close.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    macd_val = float(macd.iloc[-1])
    signal_val = float(signal.iloc[-1])
    macd_histogram = macd_val - signal_val

    # Bollinger Bands
    bb_middle = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_upper = float((bb_middle + 2 * bb_std).iloc[-1])
    bb_lower = float((bb_middle - 2 * bb_std).iloc[-1])

    # 52-week range
    high_52w = float(close.tail(252).max()) if len(close) >= 252 else float(close.max())
    low_52w = float(close.tail(252).min()) if len(close) >= 252 else float(close.min())

    # Volatility
    returns = close.pct_change().dropna()
    vol_30d = float(returns.tail(30).std() * np.sqrt(252))

    return {
        "current_price": round(current_price, 2),
        "ma_20": round(ma_20, 2),
        "ma_50": round(ma_50, 2),
        "ma_200": round(ma_200, 2) if ma_200 else None,
        "rsi_14": round(rsi, 2),
        "macd": round(macd_val, 4),
        "macd_signal": round(signal_val, 4),
        "macd_histogram": round(macd_histogram, 4),
        "bb_upper": round(bb_upper, 2),
        "bb_lower": round(bb_lower, 2),
        "high_52w": round(high_52w, 2),
        "low_52w": round(low_52w, 2),
        "vol_30d_annualized": round(vol_30d, 4),
    }


def run(ticker: str, price_df: pd.DataFrame, regime: dict = None) -> dict:
    """
    Run technical analysis for a ticker.
    price_df: historical price DataFrame from yfinance
    regime: dict from hmm_regime.predict_current_regime()
    """
    settings = get_settings()
    llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=800,
    )

    if price_df.empty or len(price_df) < 30:
        return {"ticker": ticker, "agent": "technicals", "thesis": "NEUTRAL", "confidence": 0, "error": "Insufficient price data"}

    indicators = compute_indicators(price_df)
    regime_str = f"Current Market Regime: {regime.get('current_regime', 'UNKNOWN')}" if regime else ""
    regime_dist = str(regime.get("recent_distribution_30d", {})) if regime else ""

    user_prompt = f"""Analyze {ticker} based on technical indicators:

PRICE DATA:
Current Price: ${indicators['current_price']}
MA20: ${indicators['ma_20']} | MA50: ${indicators['ma_50']} | MA200: ${indicators.get('ma_200', 'N/A')}
RSI(14): {indicators['rsi_14']}
MACD: {indicators['macd']} | Signal: {indicators['macd_signal']} | Histogram: {indicators['macd_histogram']}
Bollinger Upper: ${indicators['bb_upper']} | Lower: ${indicators['bb_lower']}
52W High: ${indicators['high_52w']} | 52W Low: ${indicators['low_52w']}
30D Annualized Volatility: {indicators['vol_30d_annualized']:.1%}

MARKET REGIME:
{regime_str}
30D Regime Distribution: {regime_dist}

Provide:
THESIS: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]
KEY_SIGNALS: [signal1 | signal2 | signal3]
SUPPORT_LEVEL: [price]
RESISTANCE_LEVEL: [price]
SUMMARY: [one sentence]"""

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        raw = response.content
        result = _parse_response(raw, ticker, indicators)
        logger.info(f"Technicals Agent [{ticker}]: {result['thesis']} @ {result['confidence']}")
        return result
    except Exception as e:
        logger.error(f"Technicals Agent error for {ticker}: {e}")
        return {"ticker": ticker, "agent": "technicals", "thesis": "NEUTRAL", "confidence": 0, "error": str(e)}


def _parse_response(raw: str, ticker: str, indicators: dict) -> dict:
    result = {
        "ticker": ticker,
        "agent": "technicals",
        "thesis": "NEUTRAL",
        "confidence": 50,
        "key_signals": [],
        "support_level": None,
        "resistance_level": None,
        "summary": "",
        "indicators": indicators,
        "raw": raw,
    }
    for line in raw.strip().split("\n"):
        if line.startswith("THESIS:"):
            t = line.split(":", 1)[1].strip().upper()
            if t in ["BULLISH", "BEARISH", "NEUTRAL"]:
                result["thesis"] = t
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("KEY_SIGNALS:"):
            result["key_signals"] = [s.strip() for s in line.split(":", 1)[1].split("|")]
        elif line.startswith("SUPPORT_LEVEL:"):
            try:
                result["support_level"] = float(line.split(":", 1)[1].strip().replace("$", ""))
            except ValueError:
                pass
        elif line.startswith("RESISTANCE_LEVEL:"):
            try:
                result["resistance_level"] = float(line.split(":", 1)[1].strip().replace("$", ""))
            except ValueError:
                pass
        elif line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
    return result
