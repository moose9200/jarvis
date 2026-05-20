"""Public web fetchers for Intel Briefs.

These hit only public, unauthenticated endpoints so they work without the
user adding any third-party credentials. Each fetcher returns a list of
plain dicts with normalised keys: {source, title, url, summary, score,
author, created_at, comments}.

Sources implemented (today):
  - Reddit hot.json per subreddit (public, no auth, polite User-Agent)
  - Hacker News Algolia search (public, no auth, full-text query)

To add a new source, write fetch_X() returning the same dict shape and
import it in synth.py.
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

import httpx

logger = logging.getLogger("jarvis.intel.fetchers")

UA = "JarvisV2/0.2 (industry-intel-monitor; +https://jarvis.app)"
TIMEOUT = 12.0


async def fetch_reddit(subreddit: str, limit: int = 20) -> list[dict]:
    """Pull `hot` posts from a public subreddit. Returns [] on any error
    (network, 403, deleted sub) — never raises."""
    sub = subreddit.lstrip("r/").lstrip("/")
    url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": UA})
        if r.status_code != 200:
            logger.warning("reddit %s returned %s", sub, r.status_code)
            return []
        children = r.json().get("data", {}).get("children", []) or []
    except Exception:
        logger.exception("reddit fetch failed for %s", sub)
        return []

    out: list[dict] = []
    for c in children[:limit]:
        d = c.get("data", {}) if isinstance(c, dict) else {}
        if d.get("stickied") or d.get("over_18"):
            continue
        out.append({
            "source": f"reddit:r/{sub}",
            "title": d.get("title") or "",
            "url": f"https://reddit.com{d.get('permalink', '')}" if d.get("permalink") else d.get("url", ""),
            "summary": (d.get("selftext") or "")[:500],
            "score": d.get("score", 0) or 0,
            "author": d.get("author"),
            "created_at": _ts(d.get("created_utc")),
            "comments": d.get("num_comments", 0) or 0,
        })
    return out


async def fetch_hn(query: str, limit: int = 15) -> list[dict]:
    """Search Hacker News via Algolia. Returns story items only — comments
    add too much noise to a daily brief."""
    url = "https://hn.algolia.com/api/v1/search"
    params = {"query": query, "tags": "story", "hitsPerPage": str(limit)}
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT) as c:
            r = await c.get(url, params=params, headers={"User-Agent": UA})
        if r.status_code != 200:
            logger.warning("hn returned %s for %s", r.status_code, query)
            return []
        hits = r.json().get("hits", []) or []
    except Exception:
        logger.exception("hn fetch failed for %s", query)
        return []

    out: list[dict] = []
    for h in hits[:limit]:
        out.append({
            "source": "hn",
            "title": h.get("title") or h.get("story_title") or "",
            "url": h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}",
            "summary": (h.get("story_text") or "")[:500],
            "score": h.get("points", 0) or 0,
            "author": h.get("author"),
            "created_at": h.get("created_at"),
            "comments": h.get("num_comments", 0) or 0,
        })
    return out


def _ts(epoch: Optional[float]) -> Optional[str]:
    if not epoch:
        return None
    try:
        return datetime.utcfromtimestamp(epoch).isoformat() + "Z"
    except (TypeError, ValueError, OSError):
        return None


def default_sources_for_industry(industry: str) -> dict[str, Any]:
    """Reasonable default sub list + HN query for a user's industry text.
    Keeps it small (3 subs + HN) so we don't burn tokens. Users can edit
    the brief in Settings."""
    industry = (industry or "").strip().lower()
    base_subs = ["Entrepreneur", "smallbusiness", "startups"]

    keyword_subs = {
        "saas":         ["SaaS", "startups", "Entrepreneur"],
        "ecommerce":    ["ecommerce", "shopify", "smallbusiness"],
        "d2c":          ["ecommerce", "shopify", "smallbusiness"],
        "botanical":    ["skincareaddiction", "ecommerce", "smallbusiness"],
        "skincare":     ["skincareaddiction", "ecommerce", "smallbusiness"],
        "fintech":      ["fintech", "startups", "personalfinance"],
        "ai":           ["LocalLLaMA", "MachineLearning", "OpenAI"],
        "developer":    ["webdev", "programming", "javascript"],
        "marketing":    ["marketing", "advertising", "growthhacking"],
        "real estate":  ["RealEstate", "realestateinvesting", "Entrepreneur"],
        "health":       ["healthcare", "medicine", "wellness"],
    }
    subs = base_subs
    for kw, subset in keyword_subs.items():
        if kw in industry:
            subs = subset
            break

    return {"reddit": subs, "hn": True, "hn_query": industry or "industry trends"}
