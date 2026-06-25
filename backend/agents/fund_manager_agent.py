"""
Fund Manager Agent.
Synthesizes debates from all 4 specialist agents into a final investment decision.
Applies meta-learning weight adjustments based on rolling 90-day accuracy.
"""

from __future__ import annotations
import json
from datetime import datetime, timezone
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from ..utils.config import get_settings
from loguru import logger


SYSTEM_PROMPT = """You are the Portfolio Manager (PM) at a top multi-strategy hedge fund.
You have just received investment theses from four specialist analysts:
- Fundamentals Analyst (EDGAR filings, financial health)
- Technical Analyst (price action, indicators, market regime)
- Sentiment Analyst (news flow, FinBERT signals)
- Risk Manager (VaR, position sizing, downside protection)

Your job is to:
1. Weigh each analyst's thesis and confidence against their recent track record (weights provided)
2. Identify where analysts agree and disagree (the debate)
3. Make a FINAL investment decision: BUY / HOLD / SELL with a target weight (% of portfolio)
4. Explain your reasoning for overriding any analyst if you do
5. Set a 90-day price target

You are the final decision maker. Be decisive. Capital preservation is paramount."""


DEFAULT_WEIGHTS = {
    "fundamentals": 0.35,
    "technicals": 0.25,
    "sentiment": 0.20,
    "risk_manager": 0.20,
}

THESIS_SCORE = {"BULLISH": 1, "NEUTRAL": 0, "BEARISH": -1}


def compute_weighted_signal(agent_results: list[dict], weights: dict = None) -> dict:
    """
    Compute a weighted consensus signal from all agent theses.
    Returns weighted score in [-1, 1] and individual contributions.
    """
    if weights is None:
        weights = DEFAULT_WEIGHTS

    total_score = 0
    total_weight = 0
    contributions = {}

    for result in agent_results:
        agent = result.get("agent")
        thesis = result.get("thesis", "NEUTRAL")
        confidence = result.get("confidence", 50) / 100
        weight = weights.get(agent, 0.25)

        score = THESIS_SCORE.get(thesis, 0) * confidence * weight
        total_score += score
        total_weight += weight
        contributions[agent] = {
            "thesis": thesis,
            "confidence": result.get("confidence", 50),
            "weight": weight,
            "contribution": round(score, 4),
        }

    normalized_score = total_score / total_weight if total_weight > 0 else 0
    return {
        "weighted_score": round(normalized_score, 4),
        "contributions": contributions,
        "consensus": "BULLISH" if normalized_score > 0.15 else ("BEARISH" if normalized_score < -0.15 else "NEUTRAL"),
    }


def run(
    ticker: str,
    fundamentals_result: dict,
    technicals_result: dict,
    sentiment_result: dict,
    risk_result: dict,
    agent_weights: dict = None,
    credit_score: float = None,
) -> dict:
    """
    Final fund manager synthesis. Returns the ultimate investment decision.
    agent_weights: dict of rolling 90-day accuracy weights per agent (optional, uses defaults if None)
    """
    settings = get_settings()
    llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.2,
        max_tokens=1200,
    )

    weights = agent_weights or DEFAULT_WEIGHTS
    agent_results = [fundamentals_result, technicals_result, sentiment_result, risk_result]
    consensus = compute_weighted_signal(agent_results, weights)

    user_prompt = f"""Make the final investment decision for {ticker}:

AGENT THESES AND CONFIDENCE:
Fundamentals Analyst: {fundamentals_result.get('thesis')} (confidence: {fundamentals_result.get('confidence')}/100)
  Summary: {fundamentals_result.get('summary', '')}
  Weight in portfolio: {weights.get('fundamentals', 0.35):.0%}

Technical Analyst: {technicals_result.get('thesis')} (confidence: {technicals_result.get('confidence')}/100)
  Summary: {technicals_result.get('summary', '')}
  Weight: {weights.get('technicals', 0.25):.0%}

Sentiment Analyst: {sentiment_result.get('thesis')} (confidence: {sentiment_result.get('confidence')}/100)
  Summary: {sentiment_result.get('summary', '')}
  Weight: {weights.get('sentiment', 0.20):.0%}

Risk Manager: {risk_result.get('risk_rating')} risk (confidence: {risk_result.get('confidence')}/100)
  Max position size: {risk_result.get('max_position_size')}
  Summary: {risk_result.get('summary', '')}
  Weight: {weights.get('risk_manager', 0.20):.0%}

QUANTITATIVE CONSENSUS:
Weighted Signal Score: {consensus['weighted_score']} (range: -1 to +1)
Consensus Direction: {consensus['consensus']}
Credit Score: {credit_score}/100 if credit_score else "N/A"

AGENT DEBATE SUMMARY:
{_summarize_disagreements(fundamentals_result, technicals_result, sentiment_result)}

Make your final decision:
DECISION: [BUY/HOLD/SELL]
TARGET_WEIGHT: [% of portfolio, respect risk manager's max]
CONVICTION: [LOW/MEDIUM/HIGH]
PRICE_TARGET_90D: [price or N/A]
OVERRIDE_REASON: [if you overrode any agent, explain why | N/A]
KEY_THESIS: [2-3 sentence investment thesis]
DEBATE_RESOLUTION: [how you resolved any analyst disagreements]"""

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        raw = response.content
        result = _parse_response(raw, ticker, consensus, weights)
        result["timestamp"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"Fund Manager [{ticker}]: {result['decision']} | Conviction: {result['conviction']} | Weight: {result['target_weight']}")
        return result
    except Exception as e:
        logger.error(f"Fund Manager error for {ticker}: {e}")
        return {
            "ticker": ticker, "agent": "fund_manager",
            "decision": "HOLD", "conviction": "LOW",
            "error": str(e), "consensus": consensus,
        }


def _summarize_disagreements(fundamentals: dict, technicals: dict, sentiment: dict) -> str:
    theses = {
        "Fundamentals": fundamentals.get("thesis"),
        "Technicals": technicals.get("thesis"),
        "Sentiment": sentiment.get("thesis"),
    }
    unique = set(theses.values())
    if len(unique) == 1:
        return f"All analysts agree: {list(unique)[0]}"
    disagreements = [f"{k}: {v}" for k, v in theses.items()]
    return "Analysts disagree — " + " | ".join(disagreements)


def _parse_response(raw: str, ticker: str, consensus: dict, weights: dict) -> dict:
    result = {
        "ticker": ticker,
        "agent": "fund_manager",
        "decision": "HOLD",
        "target_weight": "0%",
        "conviction": "LOW",
        "price_target_90d": None,
        "override_reason": None,
        "key_thesis": "",
        "debate_resolution": "",
        "consensus": consensus,
        "weights_used": weights,
        "raw": raw,
    }
    for line in raw.strip().split("\n"):
        if line.startswith("DECISION:"):
            d = line.split(":", 1)[1].strip().upper()
            if d in ["BUY", "HOLD", "SELL"]:
                result["decision"] = d
        elif line.startswith("TARGET_WEIGHT:"):
            result["target_weight"] = line.split(":", 1)[1].strip()
        elif line.startswith("CONVICTION:"):
            c = line.split(":", 1)[1].strip().upper()
            if c in ["LOW", "MEDIUM", "HIGH"]:
                result["conviction"] = c
        elif line.startswith("PRICE_TARGET_90D:"):
            result["price_target_90d"] = line.split(":", 1)[1].strip()
        elif line.startswith("OVERRIDE_REASON:"):
            result["override_reason"] = line.split(":", 1)[1].strip()
        elif line.startswith("KEY_THESIS:"):
            result["key_thesis"] = line.split(":", 1)[1].strip()
        elif line.startswith("DEBATE_RESOLUTION:"):
            result["debate_resolution"] = line.split(":", 1)[1].strip()
    return result
