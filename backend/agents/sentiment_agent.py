"""
Sentiment Agent.
Aggregates FinBERT-scored news and filings sentiment into a thesis.
"""

from __future__ import annotations
from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from ..utils.config import get_settings
from loguru import logger


SYSTEM_PROMPT = """You are a sentiment and news analyst at a top hedge fund.
Your role is to interpret FinBERT sentiment signals from news articles and SEC filings
to assess market sentiment towards a stock.

You must:
1. Interpret quantitative sentiment scores in context
2. Identify key narrative themes driving sentiment
3. Flag any major catalysts or risk events in the news
4. Form a clear sentiment thesis (BULLISH / BEARISH / NEUTRAL) with confidence 0-100

Be concise and specific. Distinguish between short-term noise and structural sentiment shifts."""


def run(
    ticker: str,
    sentiment_aggregate: dict,
    scored_articles: list[dict] = None,
) -> dict:
    """
    Run sentiment analysis for a ticker.
    sentiment_aggregate: output of finbert_pipeline.aggregate_sentiment()
    scored_articles: list of articles with sentiment scores attached
    """
    settings = get_settings()
    llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=600,
    )

    # Top headlines for context
    top_headlines = ""
    if scored_articles:
        sorted_articles = sorted(
            scored_articles,
            key=lambda a: abs(a.get("sentiment", {}).get("net_sentiment", 0)),
            reverse=True,
        )[:5]
        top_headlines = "\n".join([
            f"- [{a['sentiment']['label'].upper()}] {a.get('title', '')[:80]}"
            for a in sorted_articles
        ])

    user_prompt = f"""Analyze sentiment for {ticker}:

QUANTITATIVE SENTIMENT SUMMARY:
Mean Net Sentiment: {sentiment_aggregate.get('mean_net_sentiment', 0):.4f} (range: -1 to +1)
Article Count: {sentiment_aggregate.get('article_count', 0)}
Positive articles: {sentiment_aggregate.get('label_counts', {}).get('positive', 0)}
Negative articles: {sentiment_aggregate.get('label_counts', {}).get('negative', 0)}
Neutral articles: {sentiment_aggregate.get('label_counts', {}).get('neutral', 0)}
Dominant label: {sentiment_aggregate.get('dominant_label', 'neutral').upper()}

TOP HEADLINES (by sentiment strength):
{top_headlines if top_headlines else 'No headlines available'}

Provide:
THESIS: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]
KEY_THEMES: [theme1 | theme2 | theme3]
SENTIMENT_SIGNAL: [STRONG_POSITIVE/POSITIVE/NEUTRAL/NEGATIVE/STRONG_NEGATIVE]
SUMMARY: [one sentence]"""

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        raw = response.content
        result = _parse_response(raw, ticker, sentiment_aggregate)
        logger.info(f"Sentiment Agent [{ticker}]: {result['thesis']} @ {result['confidence']}")
        return result
    except Exception as e:
        logger.error(f"Sentiment Agent error for {ticker}: {e}")
        return {
            "ticker": ticker, "agent": "sentiment",
            "thesis": "NEUTRAL", "confidence": 0, "error": str(e),
        }


def _parse_response(raw: str, ticker: str, aggregate: dict) -> dict:
    result = {
        "ticker": ticker,
        "agent": "sentiment",
        "thesis": "NEUTRAL",
        "confidence": 50,
        "key_themes": [],
        "sentiment_signal": "NEUTRAL",
        "summary": "",
        "aggregate": aggregate,
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
        elif line.startswith("KEY_THEMES:"):
            result["key_themes"] = [s.strip() for s in line.split(":", 1)[1].split("|")]
        elif line.startswith("SENTIMENT_SIGNAL:"):
            result["sentiment_signal"] = line.split(":", 1)[1].strip().upper()
        elif line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
    return result
