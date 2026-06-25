"""
Fundamentals Agent.
Analyzes SEC EDGAR filings via Pinecone semantic retrieval.
Produces a fundamental thesis with confidence score.
"""

from langchain_groq import ChatGroq
from langchain.schema import HumanMessage, SystemMessage
from ..data.pinecone_store import query_filings
from ..utils.config import get_settings
from loguru import logger


SYSTEM_PROMPT = """You are a senior fundamental equity analyst at a top hedge fund.
Your role is to analyze SEC EDGAR filings (10-K, 10-Q) to assess a company's financial health,
business moat, management quality, and investment merit.

For each analysis, you must:
1. Assess revenue quality and growth sustainability
2. Evaluate balance sheet strength and debt burden
3. Identify key risks from the filings
4. Form a clear investment thesis (BULLISH / BEARISH / NEUTRAL)
5. Assign a confidence score 0-100

Be specific, cite numbers from filings, and be direct about your conviction."""


def run(ticker: str, credit_score: float = None, extra_context: str = "") -> dict:
    """
    Run fundamental analysis for a ticker.
    Retrieves relevant filing excerpts from Pinecone and calls Groq LLM.
    Returns thesis dict with stance, confidence, key_points, and raw_analysis.
    """
    settings = get_settings()
    llm = ChatGroq(
        groq_api_key=settings.groq_api_key,
        model_name="llama-3.3-70b-versatile",
        temperature=0.3,
        max_tokens=1024,
    )

    # Semantic retrieval from Pinecone
    filing_chunks = query_filings(
        query=f"{ticker} revenue growth debt risk management outlook",
        ticker=ticker,
        top_k=5,
    )

    if not filing_chunks:
        filing_context = f"No EDGAR filings found in vector store for {ticker}. Analyze based on general knowledge."
    else:
        filing_context = "\n\n---\n\n".join([
            f"[{c['form']} | {c['date']}]\n{c['text']}" for c in filing_chunks
        ])

    credit_context = f"\nCredit Score: {credit_score}/100" if credit_score else ""
    user_prompt = f"""Analyze {ticker} based on the following EDGAR filing excerpts:{credit_context}

FILING EXCERPTS:
{filing_context[:3000]}

{extra_context}

Provide:
1. Investment thesis (BULLISH/BEARISH/NEUTRAL) with confidence 0-100
2. Top 3 bullish factors
3. Top 3 risk factors
4. One-sentence summary

Format your response as:
THESIS: [BULLISH/BEARISH/NEUTRAL]
CONFIDENCE: [0-100]
BULLISH_FACTORS: [factor1 | factor2 | factor3]
RISK_FACTORS: [risk1 | risk2 | risk3]
SUMMARY: [one sentence]
ANALYSIS: [detailed analysis]"""

    try:
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=user_prompt),
        ]
        response = llm.invoke(messages)
        raw = response.content

        result = _parse_response(raw, ticker)
        logger.info(f"Fundamentals Agent [{ticker}]: {result['thesis']} @ {result['confidence']}")
        return result
    except Exception as e:
        logger.error(f"Fundamentals Agent error for {ticker}: {e}")
        return {
            "ticker": ticker, "agent": "fundamentals",
            "thesis": "NEUTRAL", "confidence": 0,
            "error": str(e), "raw": "",
        }


def _parse_response(raw: str, ticker: str) -> dict:
    """Parse structured fields from LLM response."""
    lines = raw.strip().split("\n")
    result = {
        "ticker": ticker,
        "agent": "fundamentals",
        "thesis": "NEUTRAL",
        "confidence": 50,
        "bullish_factors": [],
        "risk_factors": [],
        "summary": "",
        "raw": raw,
    }
    for line in lines:
        if line.startswith("THESIS:"):
            thesis = line.split(":", 1)[1].strip().upper()
            if thesis in ["BULLISH", "BEARISH", "NEUTRAL"]:
                result["thesis"] = thesis
        elif line.startswith("CONFIDENCE:"):
            try:
                result["confidence"] = int(line.split(":", 1)[1].strip())
            except ValueError:
                pass
        elif line.startswith("BULLISH_FACTORS:"):
            factors = line.split(":", 1)[1].strip()
            result["bullish_factors"] = [f.strip() for f in factors.split("|")]
        elif line.startswith("RISK_FACTORS:"):
            risks = line.split(":", 1)[1].strip()
            result["risk_factors"] = [r.strip() for r in risks.split("|")]
        elif line.startswith("SUMMARY:"):
            result["summary"] = line.split(":", 1)[1].strip()
    return result
