"""
LangGraph orchestrator.
Wires all 5 agents into a stateful graph.
State flows: data fetch -> ML scoring -> [fundamentals, technicals, sentiment] in parallel -> risk manager -> fund manager
"""

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, Any
from loguru import logger
import asyncio

from . import fundamentals_agent, technicals_agent, sentiment_agent, risk_manager_agent, fund_manager_agent
from ..data import edgar_scraper, yfinance_fetcher, news_ingestion, pinecone_store
from ..ml import finbert_pipeline, feature_engineering, credit_scorecard, hmm_regime


class AnalysisState(TypedDict):
    ticker: str
    price_df: Any
    financials: dict
    ratios: dict
    news_articles: list
    sentiment_aggregate: dict
    scored_articles: list
    features: dict
    credit_score: Optional[float]
    regime: Optional[dict]
    fundamentals_result: Optional[dict]
    technicals_result: Optional[dict]
    sentiment_result: Optional[dict]
    risk_result: Optional[dict]
    fund_manager_result: Optional[dict]
    agent_weights: Optional[dict]
    errors: list


# ── Node functions ─────────────────────────────────────────────────────────────

def fetch_market_data(state: AnalysisState) -> AnalysisState:
    """Fetch price history, financials, and key ratios from yfinance."""
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Fetching market data...")
    try:
        state["price_df"] = yfinance_fetcher.fetch_price_history(ticker, period="3y")
        state["financials"] = yfinance_fetcher.fetch_financials(ticker)
        state["ratios"] = yfinance_fetcher.fetch_key_ratios(ticker)
    except Exception as e:
        logger.error(f"[{ticker}] Market data fetch error: {e}")
        state["errors"].append(f"market_data: {e}")
    return state


def fetch_news(state: AnalysisState) -> AnalysisState:
    """Fetch and score news articles with FinBERT."""
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Fetching news and scoring sentiment...")
    try:
        articles = news_ingestion.fetch_news_for_ticker(ticker)
        scored = finbert_pipeline.score_articles(articles) if articles else []
        aggregate = finbert_pipeline.aggregate_sentiment(scored, ticker=ticker)
        state["news_articles"] = articles
        state["scored_articles"] = scored
        state["sentiment_aggregate"] = aggregate
        logger.info(f"[{ticker}] News: {len(articles)} articles, sentiment={aggregate.get('dominant_label')}")
    except Exception as e:
        logger.error(f"[{ticker}] News fetch error: {e}")
        state["errors"].append(f"news: {e}")
        state["sentiment_aggregate"] = {"mean_net_sentiment": 0, "article_count": 0, "label_counts": {}, "dominant_label": "neutral"}
    return state


def compute_ml_scores(state: AnalysisState) -> AnalysisState:
    """Compute credit score and market regime."""
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Computing ML scores...")
    try:
        if state.get("financials") and state.get("ratios") and state.get("price_df") is not None:
            features = feature_engineering.extract_features(
                ticker,
                state["financials"],
                state["ratios"],
                state["price_df"],
            )
            state["features"] = features
            credit_result = credit_scorecard.predict_score(features.copy())
            state["credit_score"] = credit_result.get("credit_score")
    except Exception as e:
        logger.error(f"[{ticker}] Credit score error: {e}")
        state["errors"].append(f"credit_score: {e}")

    try:
        if state.get("price_df") is not None and not state["price_df"].empty:
            state["regime"] = hmm_regime.predict_current_regime(state["price_df"])
    except Exception as e:
        logger.error(f"[{ticker}] HMM regime error: {e}")
        state["errors"].append(f"regime: {e}")
    return state


def run_fundamentals(state: AnalysisState) -> AnalysisState:
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Running Fundamentals Agent...")
    try:
        state["fundamentals_result"] = fundamentals_agent.run(
            ticker=ticker,
            credit_score=state.get("credit_score"),
        )
    except Exception as e:
        logger.error(f"[{ticker}] Fundamentals error: {e}")
        state["errors"].append(f"fundamentals: {e}")
        state["fundamentals_result"] = {"ticker": ticker, "agent": "fundamentals", "thesis": "NEUTRAL", "confidence": 0}
    return state


def run_technicals(state: AnalysisState) -> AnalysisState:
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Running Technicals Agent...")
    try:
        state["technicals_result"] = technicals_agent.run(
            ticker=ticker,
            price_df=state.get("price_df"),
            regime=state.get("regime"),
        )
    except Exception as e:
        logger.error(f"[{ticker}] Technicals error: {e}")
        state["errors"].append(f"technicals: {e}")
        state["technicals_result"] = {"ticker": ticker, "agent": "technicals", "thesis": "NEUTRAL", "confidence": 0}
    return state


def run_sentiment(state: AnalysisState) -> AnalysisState:
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Running Sentiment Agent...")
    try:
        state["sentiment_result"] = sentiment_agent.run(
            ticker=ticker,
            sentiment_aggregate=state.get("sentiment_aggregate", {}),
            scored_articles=state.get("scored_articles", []),
        )
    except Exception as e:
        logger.error(f"[{ticker}] Sentiment error: {e}")
        state["errors"].append(f"sentiment: {e}")
        state["sentiment_result"] = {"ticker": ticker, "agent": "sentiment", "thesis": "NEUTRAL", "confidence": 0}
    return state


def run_risk_manager(state: AnalysisState) -> AnalysisState:
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Running Risk Manager Agent...")
    try:
        state["risk_result"] = risk_manager_agent.run(
            ticker=ticker,
            price_df=state.get("price_df"),
            fundamentals_result=state.get("fundamentals_result"),
            technicals_result=state.get("technicals_result"),
            credit_score=state.get("credit_score"),
            regime=state.get("regime"),
        )
    except Exception as e:
        logger.error(f"[{ticker}] Risk Manager error: {e}")
        state["errors"].append(f"risk_manager: {e}")
        state["risk_result"] = {"ticker": ticker, "agent": "risk_manager", "risk_rating": "HIGH", "confidence": 0}
    return state


def run_fund_manager(state: AnalysisState) -> AnalysisState:
    ticker = state["ticker"]
    logger.info(f"[{ticker}] Running Fund Manager Agent (final synthesis)...")
    try:
        state["fund_manager_result"] = fund_manager_agent.run(
            ticker=ticker,
            fundamentals_result=state.get("fundamentals_result", {}),
            technicals_result=state.get("technicals_result", {}),
            sentiment_result=state.get("sentiment_result", {}),
            risk_result=state.get("risk_result", {}),
            agent_weights=state.get("agent_weights"),
            credit_score=state.get("credit_score"),
        )
    except Exception as e:
        logger.error(f"[{ticker}] Fund Manager error: {e}")
        state["errors"].append(f"fund_manager: {e}")
        state["fund_manager_result"] = {"ticker": ticker, "agent": "fund_manager", "decision": "HOLD", "conviction": "LOW"}
    return state


# ── Combined analyst node (runs all 3 analysts sequentially in one node) ───────

def run_analysts(state: AnalysisState) -> AnalysisState:
    """Run fundamentals, technicals, and sentiment agents sequentially."""
    state = run_fundamentals(state)
    state = run_technicals(state)
    state = run_sentiment(state)
    return state


# ── Build the LangGraph ────────────────────────────────────────────────────────

def build_graph() -> StateGraph:
    graph = StateGraph(AnalysisState)

    graph.add_node("fetch_market_data", fetch_market_data)
    graph.add_node("fetch_news", fetch_news)
    graph.add_node("compute_ml_scores", compute_ml_scores)
    graph.add_node("run_analysts", run_analysts)
    graph.add_node("run_risk_manager", run_risk_manager)
    graph.add_node("run_fund_manager", run_fund_manager)

    graph.set_entry_point("fetch_market_data")

    graph.add_edge("fetch_market_data", "fetch_news")
    graph.add_edge("fetch_news", "compute_ml_scores")
    graph.add_edge("compute_ml_scores", "run_analysts")
    graph.add_edge("run_analysts", "run_risk_manager")
    graph.add_edge("run_risk_manager", "run_fund_manager")
    graph.add_edge("run_fund_manager", END)

    return graph.compile()


_compiled_graph = None


def get_graph():
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_graph()
    return _compiled_graph


def analyze_ticker(ticker: str, agent_weights: dict = None) -> dict:
    """
    Main entry point. Run the full 5-agent analysis for a ticker.
    Returns the complete state including all agent outputs.
    """
    graph = get_graph()
    initial_state: AnalysisState = {
        "ticker": ticker.upper(),
        "price_df": None,
        "financials": {},
        "ratios": {},
        "news_articles": [],
        "sentiment_aggregate": {},
        "scored_articles": [],
        "features": {},
        "credit_score": None,
        "regime": None,
        "fundamentals_result": None,
        "technicals_result": None,
        "sentiment_result": None,
        "risk_result": None,
        "fund_manager_result": None,
        "agent_weights": agent_weights,
        "errors": [],
    }

    logger.info(f"Starting multi-agent analysis for {ticker}")
    final_state = graph.invoke(initial_state)
    logger.info(f"Analysis complete for {ticker}: {final_state['fund_manager_result'].get('decision')}")
    return final_state


if __name__ == "__main__":
    result = analyze_ticker("AAPL")
    fm = result["fund_manager_result"]
    print(f"\n{'='*50}")
    print(f"TICKER: {result['ticker']}")
    print(f"DECISION: {fm.get('decision')} | CONVICTION: {fm.get('conviction')}")
    print(f"TARGET WEIGHT: {fm.get('target_weight')}")
    print(f"THESIS: {fm.get('key_thesis')}")
    print(f"ERRORS: {result['errors']}")
