"""
News ingestion via yfinance (primary), RSS feeds, and optional NewsAPI.
yfinance.Ticker.news gives 15-20 ticker-specific articles for free.
"""

from __future__ import annotations
import feedparser
import yfinance as yf
from datetime import datetime, timezone
from typing import Optional
from loguru import logger


# Ticker → common names used in headlines
TICKER_ALIASES: dict[str, list[str]] = {
    "AAPL":  ["apple", "aapl"],
    "MSFT":  ["microsoft", "msft"],
    "GOOGL": ["google", "alphabet", "googl"],
    "GOOG":  ["google", "alphabet", "goog"],
    "AMZN":  ["amazon", "amzn"],
    "META":  ["meta", "facebook", "instagram"],
    "TSLA":  ["tesla", "tsla", "elon musk"],
    "NVDA":  ["nvidia", "nvda"],
    "NFLX":  ["netflix", "nflx"],
    "AMD":   ["amd", "advanced micro"],
    "INTC":  ["intel", "intc"],
    "CRM":   ["salesforce", "crm"],
    "ORCL":  ["oracle", "orcl"],
    "IBM":   ["ibm"],
    "BABA":  ["alibaba", "baba"],
    "JPM":   ["jpmorgan", "jpm", "jp morgan"],
    "BAC":   ["bank of america", "bac"],
    "GS":    ["goldman sachs", "goldman", "gs"],
    "MS":    ["morgan stanley", "ms"],
    "WMT":   ["walmart", "wmt"],
    "TGT":   ["target", "tgt"],
    "HD":    ["home depot", "hd"],
    "COST":  ["costco", "cost"],
    "JNJ":   ["johnson", "jnj"],
    "PFE":   ["pfizer", "pfe"],
    "UNH":   ["unitedhealth", "unh"],
    "XOM":   ["exxon", "xom"],
    "CVX":   ["chevron", "cvx"],
    "BA":    ["boeing", "ba"],
    "CAT":   ["caterpillar", "cat"],
    "GE":    ["general electric", "ge"],
    "F":     ["ford", " f "],
    "GM":    ["general motors", " gm"],
    "DIS":   ["disney", "dis"],
    "SBUX":  ["starbucks", "sbux"],
    "MCD":   ["mcdonald", "mcd"],
    "KO":    ["coca-cola", "coca cola", " ko "],
    "PEP":   ["pepsi", "pepsico", "pep"],
    "BRK-B": ["berkshire", "buffett", "brk"],
}

RSS_FEEDS = {
    "yahoo_finance":  "https://finance.yahoo.com/news/rssindex",
    "seeking_alpha":  "https://seekingalpha.com/feed.xml",
    "marketwatch":    "https://feeds.content.dowjones.io/public/rss/mw_topstories",
    "reuters_biz":    "https://feeds.reuters.com/reuters/businessNews",
    "wsj_markets":    "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
}


def fetch_yfinance_news(ticker: str) -> list[dict]:
    """
    Fetch ticker-specific news via yfinance (free, no API key).
    Returns up to 20 articles pre-filtered for the ticker.
    """
    try:
        t = yf.Ticker(ticker)
        raw = t.news or []
        articles = []
        for item in raw[:20]:
            content = item.get("content", {})
            articles.append({
                "source":     "yfinance",
                "ticker":     ticker,
                "title":      content.get("title") or item.get("title", ""),
                "summary":    content.get("summary") or item.get("summary", ""),
                "link":       content.get("canonicalUrl", {}).get("url", "") or item.get("link", ""),
                "published":  content.get("pubDate") or item.get("published", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.info(f"[{ticker}] yfinance news: {len(articles)} articles")
        return articles
    except Exception as e:
        logger.warning(f"[{ticker}] yfinance news fetch failed: {e}")
        return []


def parse_rss_feed(feed_name: str, feed_url: str) -> list[dict]:
    """Parse a single RSS feed and return normalized article list."""
    try:
        feed = feedparser.parse(feed_url)
        articles = []
        for entry in feed.entries[:20]:
            articles.append({
                "source":     feed_name,
                "title":      entry.get("title", ""),
                "summary":    entry.get("summary", ""),
                "link":       entry.get("link", ""),
                "published":  entry.get("published", ""),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
            })
        logger.info(f"Parsed {len(articles)} articles from {feed_name}")
        return articles
    except Exception as e:
        logger.error(f"RSS parse error for {feed_name}: {e}")
        return []


def fetch_all_rss() -> list[dict]:
    """Fetch and parse all configured RSS feeds."""
    all_articles = []
    for name, url in RSS_FEEDS.items():
        all_articles.extend(parse_rss_feed(name, url))
    logger.info(f"Total RSS articles fetched: {len(all_articles)}")
    return all_articles


def filter_articles_by_ticker(articles: list[dict], ticker: str) -> list[dict]:
    """
    Filter RSS articles that mention the ticker or any of its company name aliases.
    Uses TICKER_ALIASES for broad matching (e.g. 'AAPL' matches 'Apple' in headlines).
    """
    aliases = TICKER_ALIASES.get(ticker.upper(), [ticker.lower()])
    if ticker.lower() not in aliases:
        aliases = aliases + [ticker.lower()]

    def matches(article: dict) -> bool:
        text = (article.get("title", "") + " " + article.get("summary", "")).lower()
        return any(alias in text for alias in aliases)

    matched = [a for a in articles if matches(a)]
    logger.info(f"[{ticker}] RSS filter: {len(matched)}/{len(articles)} articles matched")
    return matched


def fetch_news_for_ticker(ticker: str, news_api_key: Optional[str] = None) -> list[dict]:
    """
    Main entry point. Returns articles from all sources for a given ticker:
    1. yfinance ticker-specific news (best, free)
    2. RSS feeds filtered by company name
    Deduplicates by title.
    """
    seen_titles: set[str] = set()
    combined: list[dict] = []

    # Primary: yfinance ticker news
    yf_articles = fetch_yfinance_news(ticker)
    for a in yf_articles:
        t = a.get("title", "").strip()
        if t and t not in seen_titles:
            seen_titles.add(t)
            combined.append(a)

    # Secondary: filtered RSS
    rss_articles = fetch_all_rss()
    rss_filtered  = filter_articles_by_ticker(rss_articles, ticker)
    for a in rss_filtered:
        t = a.get("title", "").strip()
        if t and t not in seen_titles:
            seen_titles.add(t)
            combined.append(a)

    logger.info(f"[{ticker}] Total unique articles: {len(combined)}")
    return combined


async def fetch_newsapi(ticker: str, api_key: str, page_size: int = 20) -> list[dict]:
    """Optional: fetch from NewsAPI (free tier: 100 req/day)."""
    if not api_key:
        return []
    import aiohttp
    url = "https://newsapi.org/v2/everything"
    params = {"q": ticker, "sortBy": "publishedAt", "pageSize": page_size,
              "language": "en", "apiKey": api_key}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return [{
                    "source":    "newsapi",
                    "ticker":    ticker,
                    "title":     a.get("title", ""),
                    "summary":   a.get("description", ""),
                    "link":      a.get("url", ""),
                    "published": a.get("publishedAt", ""),
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                } for a in data.get("articles", [])]
    except Exception as e:
        logger.error(f"NewsAPI fetch failed for {ticker}: {e}")
        return []


if __name__ == "__main__":
    for ticker in ["AAPL", "TSLA", "MSFT"]:
        articles = fetch_news_for_ticker(ticker)
        print(f"\n{ticker}: {len(articles)} articles")
        for a in articles[:3]:
            print(f"  [{a['source']}] {a['title'][:80]}")
