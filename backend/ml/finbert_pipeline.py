"""
FinBERT sentiment pipeline.
Runs locally via HuggingFace transformers — zero API cost.
Scores text as Positive / Negative / Neutral with confidence.
"""

from __future__ import annotations
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification
import torch
from typing import Optional, List
from loguru import logger


MODEL_NAME = "ProsusAI/finbert"
_pipeline = None


def get_finbert():
    global _pipeline
    if _pipeline is None:
        logger.info("Loading FinBERT model (first load may take ~30s)...")
        device = 0 if torch.cuda.is_available() else -1
        _pipeline = pipeline(
            "text-classification",
            model=MODEL_NAME,
            tokenizer=MODEL_NAME,
            device=device,
            return_all_scores=True,
        )
        logger.info("FinBERT loaded.")
    return _pipeline


def score_text(text: str) -> dict:
    """
    Score a single text snippet.
    Returns dict with positive, negative, neutral scores and a net_sentiment float in [-1, 1].
    """
    pipe = get_finbert()
    # FinBERT max token length is 512 — truncate long texts
    text = text[:2000]
    try:
        results = pipe(text)[0]
        scores = {r["label"].lower(): r["score"] for r in results}
        net = scores.get("positive", 0) - scores.get("negative", 0)
        return {
            "positive": round(scores.get("positive", 0), 4),
            "negative": round(scores.get("negative", 0), 4),
            "neutral": round(scores.get("neutral", 0), 4),
            "net_sentiment": round(net, 4),
            "label": max(scores, key=scores.get),
        }
    except Exception as e:
        logger.error(f"FinBERT scoring error: {e}")
        return {"positive": 0, "negative": 0, "neutral": 1, "net_sentiment": 0, "label": "neutral"}


def score_articles(articles: list[dict]) -> list[dict]:
    """
    Score a list of news articles.
    Each article dict should have 'title' and optionally 'summary'.
    Returns articles enriched with sentiment scores.
    """
    pipe = get_finbert()
    texts = [f"{a.get('title', '')}. {a.get('summary', '')}" for a in articles]

    enriched = []
    for i, (article, text) in enumerate(zip(articles, texts)):
        sentiment = score_text(text)
        enriched.append({**article, "sentiment": sentiment})

    logger.info(f"Scored sentiment for {len(enriched)} articles")
    return enriched


def aggregate_sentiment(scored_articles: list[dict], ticker: Optional[str] = None) -> dict:
    """
    Aggregate sentiment scores across multiple articles.
    Returns mean net_sentiment and label distribution.
    """
    if not scored_articles:
        return {"mean_net_sentiment": 0, "label_counts": {}, "article_count": 0}

    net_scores = [a["sentiment"]["net_sentiment"] for a in scored_articles if "sentiment" in a]
    labels = [a["sentiment"]["label"] for a in scored_articles if "sentiment" in a]

    label_counts = {"positive": 0, "negative": 0, "neutral": 0}
    for label in labels:
        label_counts[label] = label_counts.get(label, 0) + 1

    mean_net = sum(net_scores) / len(net_scores) if net_scores else 0
    dominant = max(label_counts, key=label_counts.get)

    return {
        "ticker": ticker,
        "mean_net_sentiment": round(mean_net, 4),
        "label_counts": label_counts,
        "dominant_label": dominant,
        "article_count": len(scored_articles),
    }


if __name__ == "__main__":
    sample = [
        {"title": "Apple reports record quarterly revenue beating expectations", "summary": "Strong iPhone sales drove growth"},
        {"title": "Federal Reserve raises interest rates amid inflation concerns", "summary": "Markets react negatively to rate hike"},
    ]
    scored = score_articles(sample)
    for s in scored:
        print(f"{s['title'][:60]} -> {s['sentiment']['label']} ({s['sentiment']['net_sentiment']:.3f})")
    print(aggregate_sentiment(scored))
