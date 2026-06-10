"""
news_feed.py
Parses MMA/boxing RSS feeds and returns a merged, sorted list of articles.
"""

import feedparser
import html
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

RSS_SOURCES = [
    # MMA
    {"name": "MMA Fighting",  "url": "https://www.mmafighting.com/rss/current"},
    {"name": "Sherdog",       "url": "https://www.sherdog.com/rss/news.xml"},
    {"name": "ESPN MMA",      "url": "https://www.espn.com/espn/rss/mma/news"},
    {"name": "Tapology",      "url": "https://www.tapology.com/news.rss"},
    {"name": "Bloody Elbow",  "url": "https://bloodyelbow.substack.com/feed"},
    {"name": "MMA Mania",     "url": "https://www.mmamania.com/rss/current"},
    # Boxing
    {"name": "ESPN Boxing",   "url": "https://www.espn.com/espn/rss/boxing/news"},
    {"name": "Bad Left Hook",  "url": "https://www.badlefthook.com/rss/current"},
    {"name": "The Ring",      "url": "https://www.ringtv.com/feed/"},
]


def _parse_date(entry) -> datetime:
    """Best-effort date parse from a feedparser entry."""
    for attr in ("published", "updated"):
        raw = getattr(entry, attr, None)
        if raw:
            try:
                return parsedate_to_datetime(raw).astimezone(timezone.utc)
            except Exception:
                pass
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        try:
            return datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        except Exception:
            pass
    return datetime.min.replace(tzinfo=timezone.utc)


def fetch_news(limit_per_source: int = 10, total_limit: int = 30) -> tuple[list[dict], dict]:
    """
    Fetch and merge news from all RSS sources.

    Returns:
        articles : list of dicts — title, source, url, published, summary
        errors   : dict of source -> error string (empty string = success)
    """
    articles = []
    errors = {}

    for source in RSS_SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            if feed.bozo and not feed.entries:
                errors[source["name"]] = f"Feed error: {feed.bozo_exception}"
                continue

            for entry in feed.entries[:limit_per_source]:
                pub = _parse_date(entry)
                summary = getattr(entry, "summary", "") or ""
                # Strip HTML tags from summary
                import re
                summary = re.sub(r"<[^>]+>", "", summary).strip()

                articles.append({
                    "source":    source["name"],
                    "title":     html.unescape(entry.get("title", "").strip()),
                    "url":       entry.get("link", ""),
                    "published": pub,
                    "summary":   summary[:200] + "…" if len(summary) > 200 else summary,
                })

            errors[source["name"]] = ""

        except Exception as e:
            errors[source["name"]] = str(e)

    # Sort newest first, cap total
    articles.sort(key=lambda a: a["published"], reverse=True)
    return articles[:total_limit], errors
