"""
News feed fetcher — runs twice daily via APScheduler.
Primary source: NewsAPI (requires NEWS_API_KEY env var).
Fallback: RSS feeds from NAR, Redfin Research, and HUD.
"""
import hashlib
import logging
import os
from datetime import datetime, timedelta

import httpx
import feedparser
from sqlalchemy import select, delete

from ..db.session import AsyncSessionLocal
from ..db.models import NewsItem

log = logging.getLogger(__name__)

NEWS_API_KEY = os.getenv("NEWS_API_KEY", "")
NEWS_API_URL = "https://newsapi.org/v2/everything"

RSS_FEEDS = [
    ("NAR", "https://feeds.nar.realtor/news/all.rss"),
    ("Redfin Research", "https://www.redfin.com/news/feed/"),
    ("HUD", "https://www.hud.gov/feeds/hud_press_releases"),
]

RELEVANCE_KEYWORDS = {
    "high": ["mortgage rate", "home sales", "housing market", "median price", "inventory", "foreclosure"],
    "medium": ["real estate", "housing", "property", "home buyer", "first-time buyer", "interest rate"],
}


def _score_relevance(text: str) -> str:
    lower = text.lower()
    for level in ("high", "medium"):
        if any(kw in lower for kw in RELEVANCE_KEYWORDS[level]):
            return level
    return "low"


def _make_id(url: str) -> str:
    return "news-" + hashlib.sha1(url.encode()).hexdigest()[:12]


async def _fetch_newsapi() -> list[dict]:
    if not NEWS_API_KEY:
        return []
    params = {
        "q": "housing market OR mortgage rates OR home sales",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": NEWS_API_KEY,
    }
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(NEWS_API_URL, params=params)
            resp.raise_for_status()
            articles = resp.json().get("articles", [])
        items = []
        for a in articles:
            url = a.get("url", "")
            if not url:
                continue
            text = f"{a.get('title', '')} {a.get('description', '')}"
            items.append({
                "id": _make_id(url),
                "headline": a.get("title", "")[:500],
                "summary": (a.get("description") or "")[:1000],
                "source": (a.get("source") or {}).get("name", "NewsAPI"),
                "url": url,
                "relevance_score": _score_relevance(text),
                "market": None,
                "published_at": datetime.fromisoformat(
                    a["publishedAt"].replace("Z", "+00:00")
                ).replace(tzinfo=None) if a.get("publishedAt") else None,
            })
        return items
    except Exception as exc:
        log.warning("news_fetcher.newsapi_failed error=%s", exc)
        return []


async def _fetch_rss() -> list[dict]:
    items = []
    for source_name, feed_url in RSS_FEEDS:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(feed_url)
                resp.raise_for_status()
                feed = feedparser.parse(resp.text)
            for entry in feed.entries[:5]:
                url = entry.get("link", "")
                if not url:
                    continue
                text = f"{entry.get('title', '')} {entry.get('summary', '')}"
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    import time
                    published_at = datetime(*entry.published_parsed[:6])
                items.append({
                    "id": _make_id(url),
                    "headline": entry.get("title", "")[:500],
                    "summary": entry.get("summary", "")[:1000],
                    "source": source_name,
                    "url": url,
                    "relevance_score": _score_relevance(text),
                    "market": None,
                    "published_at": published_at,
                })
        except Exception as exc:
            log.warning("news_fetcher.rss_failed source=%s error=%s", source_name, exc)
    return items


async def fetch_and_store_news() -> None:
    """Fetch news from all sources and upsert into news_items table."""
    log.info("news_fetcher.start")
    items = await _fetch_newsapi()
    if not items:
        items = await _fetch_rss()

    if not items:
        log.info("news_fetcher.no_articles")
        return

    async with AsyncSessionLocal() as session:
        stored = 0
        for item in items:
            existing = await session.execute(
                select(NewsItem).where(NewsItem.url == item["url"])
            )
            if existing.scalar() is not None:
                continue
            session.add(NewsItem(**item))
            stored += 1

        # Prune items older than 7 days
        cutoff = datetime.utcnow() - timedelta(days=7)
        await session.execute(
            delete(NewsItem).where(NewsItem.fetched_at < cutoff)
        )
        await session.commit()

    log.info("news_fetcher.complete articles_stored=%d", stored)
