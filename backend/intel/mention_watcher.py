"""Celebrity / influencer mention watcher.

Phase 3 of the industry-monitoring track. Watches public, free sources
for press / influencer / celebrity noise touching the user's vertical
(jewellery / piercing / tattoo today).

Sources (all unauthenticated):
  - Google News RSS via news.google.com/rss/search
  - Generic RSS feeds (trade press: Pain, Tattoolife, Inked, ...)
  - Reddit hot.json on industry subreddits, filtered for celebrity
    co-occurrence keywords

Hard skip: X (paid), Instagram, TikTok — no public search.

Public entrypoints:
    await fetch_google_news(query) -> list[dict]
    await fetch_rss(feed_url)      -> list[dict]
    await run_mention_cycle(db, user_id, queries?) -> stats dict

Each fetcher returns dicts matching `intel/fetchers.py` shape:
    {source, title, url, summary, score, author, created_at, comments}
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote_plus, urlparse

import httpx
from sqlalchemy.orm import Session

from intel.fetchers import default_sources_for_industry, fetch_reddit
from models import Decision, Mention, User

logger = logging.getLogger("jarvis.intel.mention_watcher")

UA = "JarvisV2/0.2 (industry-mention-monitor; +https://jarvis.app)"
TIMEOUT = 12.0

# Default trade-press RSS feeds. The watcher tolerates source-level
# failures (404, redirect loops, malformed XML) so an entry that goes
# dark just yields zero items that cycle — the rest still flow.
WATCHED_FEEDS: list[str] = [
    "https://www.painmag.com/feed/",
    "https://www.tattoolife.com/feed/",
    "https://www.inkedmag.com/feed",
]

# Per-industry-keyword query packs. The first substring match wins;
# users can override per-user via a future settings field.
INDUSTRY_QUERIES: dict[str, list[str]] = {
    "jewel": ["celebrity jewellery", "famous wearing", "celebrity earring"],
    "pierc": ["celebrity piercing", "celebrity ear piercing"],
    "tattoo": ["celebrity tattoo", "famous tattoo"],
    "body modification": ["celebrity body modification", "celebrity piercing"],
    "bodymod": ["celebrity body modification", "celebrity piercing"],
}

# Keywords used to filter Reddit posts for "is anyone famous talking
# about us?" noise. The product watcher catches new SKUs; this catches
# celebrity / influencer chatter. Posts that don't mention at least
# one of these words on a per-vertical sub are dropped.
CELEB_KEYWORDS = (
    "celebrity",
    "celeb",
    "famous",
    "influencer",
    "spotted",
    "wearing",
    "kardashian",
    "rihanna",
    "beyonce",
    "taylor swift",
    "bieber",
    "harry styles",
    "zendaya",
    "billie eilish",
)


# ── Fetch: Google News RSS ─────────────────────────────────────────────────


def _parse_rss_date(raw: Optional[str]) -> Optional[datetime]:
    """RFC 2822 / RSS pubDate parser. Returns None on any failure."""
    if not raw:
        return None
    try:
        dt = parsedate_to_datetime(raw)
        if dt is None:
            return None
        # Drop timezone info so we compare apples to apples with
        # `datetime.utcnow()` elsewhere. Convert to UTC first if tz-aware.
        if dt.tzinfo is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return dt
    except (TypeError, ValueError):
        return None


def _strip_namespace(tag: str) -> str:
    """`{http://...}title` → `title`. ElementTree appends the namespace
    to every tag when present — strip for friendlier lookups."""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _parse_rss_xml(xml_bytes: bytes, source_label: str) -> list[dict]:
    """Generic RSS 2.0 / Atom parser using stdlib xml.etree. Tolerant
    of missing optional fields and unknown namespaces."""
    try:
        root = ET.fromstring(xml_bytes)
    except ET.ParseError as exc:
        logger.warning("rss parse failed for %s: %s", source_label, exc)
        return []

    out: list[dict] = []

    # RSS 2.0: items live at /channel/item
    # Atom:    entries live at root/entry
    items: list[ET.Element] = []
    for child in root.iter():
        tag = _strip_namespace(child.tag)
        if tag in ("item", "entry"):
            items.append(child)

    for it in items:
        title = ""
        url = ""
        summary = ""
        author = ""
        pub_raw = ""

        for child in it:
            tag = _strip_namespace(child.tag)
            if tag == "title":
                title = (child.text or "").strip()
            elif tag == "link":
                # RSS: <link>https://...</link>; Atom: <link href="..."/>
                href = child.attrib.get("href")
                if href:
                    url = href.strip()
                elif child.text:
                    url = child.text.strip()
            elif tag in ("description", "summary", "content"):
                if not summary and child.text:
                    summary = child.text.strip()[:500]
            elif tag in ("author", "creator", "dc:creator"):
                if child.text:
                    author = child.text.strip()
                else:
                    # Atom <author><name>X</name></author>
                    for sub in child:
                        if _strip_namespace(sub.tag) == "name" and sub.text:
                            author = sub.text.strip()
                            break
            elif tag in ("pubDate", "published", "updated"):
                pub_raw = (child.text or "").strip()

        if not title or not url:
            continue

        out.append({
            "source": source_label,
            "title": title,
            "url": url,
            "summary": summary,
            "score": 0,
            "author": author or None,
            "created_at": pub_raw or None,  # human-readable string; we
                                            # re-parse to datetime for
                                            # the DB row separately
            "comments": 0,
        })
    return out


async def fetch_google_news(query: str, limit: int = 25) -> list[dict]:
    """Pull recent Google News results for `query` via the public RSS
    feed. No auth, no API key. Returns [] on any error."""
    q = quote_plus(query.strip())
    url = f"https://news.google.com/rss/search?q={q}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
            r = await c.get(url, headers={"User-Agent": UA})
        if r.status_code != 200:
            logger.warning("google_news returned %s for %s", r.status_code, query)
            return []
        items = _parse_rss_xml(r.content, source_label="google_news")
    except Exception:
        logger.exception("google_news fetch failed for %s", query)
        return []
    return items[:limit]


async def fetch_rss(feed_url: str, limit: int = 25) -> list[dict]:
    """Generic RSS / Atom feed reader. Tolerant of unreachable feeds
    and malformed XML — returns [] on any error."""
    try:
        host = urlparse(feed_url).hostname or feed_url
    except Exception:
        host = feed_url
    source_label = f"rss:{host}"
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
            r = await c.get(feed_url, headers={"User-Agent": UA})
        if r.status_code != 200:
            logger.warning("rss %s returned %s", feed_url, r.status_code)
            return []
        items = _parse_rss_xml(r.content, source_label=source_label)
    except Exception:
        logger.exception("rss fetch failed for %s", feed_url)
        return []
    return items[:limit]


# ── Helpers ────────────────────────────────────────────────────────────────


def _industry_queries_for(industry: Optional[str]) -> list[str]:
    industry = (industry or "").strip().lower()
    if not industry:
        return ["celebrity"]
    for kw, qs in INDUSTRY_QUERIES.items():
        if kw in industry:
            return list(qs)
    return [industry]


def _is_celeb_post(title: str, summary: str) -> bool:
    blob = f"{title} {summary}".lower()
    return any(kw in blob for kw in CELEB_KEYWORDS)


def _coerce_published_at(raw) -> Optional[datetime]:
    """Accept the variety of shapes `created_at` can take in the merged
    feed dicts (RSS pubDate string, ISO 8601 from Reddit fetcher,
    None) and return a tz-naive datetime or None."""
    if raw is None:
        return None
    if isinstance(raw, datetime):
        return raw.replace(tzinfo=None) if raw.tzinfo else raw
    if not isinstance(raw, str):
        return None
    # Try ISO first (fetch_reddit emits ISO strings), then RFC2822.
    try:
        s = raw[:-1] if raw.endswith("Z") else raw
        dt = datetime.fromisoformat(s)
        return dt.replace(tzinfo=None) if dt.tzinfo else dt
    except ValueError:
        pass
    return _parse_rss_date(raw)


# ── Orchestrator ───────────────────────────────────────────────────────────


async def run_mention_cycle(
    db: Session,
    user_id: int,
    queries: Optional[list[str]] = None,
) -> dict:
    """Top-level entrypoint called by the Celery beat job.

    Fan-out:
      1. Google News RSS for each derived query
      2. Each WATCHED_FEEDS RSS URL
      3. Reddit hot.json for each industry sub, filtered for celebrity
         co-occurrence keywords

    Dedupes by URL within the cycle, upserts into the `mentions` table
    (unique on (url, user_id)), and surfaces NEW items as a single
    aggregated Decision row per user — mirrors product_watcher's
    `source_id = f"mentions:{user_id}"` pattern so re-runs refresh in
    place instead of stacking duplicates.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        return {"error": f"user_id {user_id} not found"}

    industry = (user.industry or "").strip().lower()
    derived_queries = queries or _industry_queries_for(industry)

    # Source 1: Google News for each query
    google_items: list[dict] = []
    for q in derived_queries:
        google_items.extend(await fetch_google_news(q, limit=15))

    # Source 2: trade-press feeds
    rss_items: list[dict] = []
    for feed in WATCHED_FEEDS:
        rss_items.extend(await fetch_rss(feed, limit=15))

    # Source 3: reddit, only celebrity-flavoured posts
    reddit_items: list[dict] = []
    sources_for_industry = default_sources_for_industry(industry)
    subs = sources_for_industry.get("reddit") or []
    for sub in subs:
        posts = await fetch_reddit(sub, limit=20)
        for p in posts:
            if _is_celeb_post(p.get("title", ""), p.get("summary", "")):
                reddit_items.append(p)

    all_items = google_items + rss_items + reddit_items

    # Dedupe within the cycle by URL (first wins)
    seen_urls: set[str] = set()
    unique_items: list[dict] = []
    for it in all_items:
        u = (it.get("url") or "").strip()
        if not u or u in seen_urls:
            continue
        seen_urls.add(u)
        unique_items.append(it)

    # Upsert into mentions. The unique (url, user_id) keeps re-runs
    # idempotent — already-seen URLs touch `surfaced_to_user` not at all
    # (handled at the Decision step below).
    existing_rows = (
        db.query(Mention)
        .filter(Mention.user_id == user_id, Mention.url.in_(list(seen_urls)))
        .all()
    )
    by_url = {r.url: r for r in existing_rows}

    now = datetime.utcnow()
    new_rows: list[Mention] = []
    for it in unique_items:
        url = it["url"]
        if url in by_url:
            continue  # already known for this user
        row = Mention(
            user_id=user_id,
            source=it.get("source") or "unknown",
            title=(it.get("title") or "")[:500] or "(untitled)",
            url=url,
            summary=(it.get("summary") or None),
            author=it.get("author"),
            published_at=_coerce_published_at(it.get("created_at")),
            first_seen_at=now,
            surfaced_to_user=False,
        )
        db.add(row)
        new_rows.append(row)
    db.commit()

    # Surface a single Decision per cycle, refreshed in place
    decisions_created = 0
    if new_rows:
        unsurfaced = (
            db.query(Mention)
            .filter(
                Mention.user_id == user_id,
                Mention.surfaced_to_user == False,  # noqa: E712
            )
            .order_by(Mention.first_seen_at.desc())
            .limit(50)
            .all()
        )
        if unsurfaced:
            sample = ", ".join(r.title for r in unsurfaced[:3])
            more = f" (+{len(unsurfaced) - 3} more)" if len(unsurfaced) > 3 else ""
            src_id = f"mentions:{user_id}"
            count = len(unsurfaced)
            title = (
                f"{count} new mention{'s' if count != 1 else ''} "
                f"about {industry or 'your industry'}"
            )
            suggestion = (
                f"New press / influencer chatter: {sample}{more}. "
                f"Open the mentions panel to review."
            )
            ctx = {
                "count": count,
                "ids": [r.id for r in unsurfaced],
                "sample_titles": [r.title for r in unsurfaced[:5]],
                "sources": sorted({r.source for r in unsurfaced}),
            }

            existing = (
                db.query(Decision)
                .filter_by(user_id=user_id, source="mention", source_id=src_id)
                .filter(Decision.status.in_(["pending", "snoozed"]))
                .first()
            )
            if existing:
                existing.title = title
                existing.ai_suggestion = suggestion
                existing.context_json = ctx
                existing.created_at = now
                existing.status = "pending"
            else:
                db.add(
                    Decision(
                        user_id=user_id,
                        source="mention",
                        source_id=src_id,
                        title=title,
                        ai_suggestion=suggestion,
                        status="pending",
                        created_at=now,
                        context_json=ctx,
                    )
                )
                decisions_created += 1

            for r in unsurfaced:
                r.surfaced_to_user = True
        db.commit()

    return {
        "queries": derived_queries,
        "google_news_items": len(google_items),
        "rss_items": len(rss_items),
        "reddit_items": len(reddit_items),
        "unique_items": len(unique_items),
        "new_rows": len(new_rows),
        "decisions_created": decisions_created,
        "ran_at": now.isoformat(),
    }
