"""Product-release watcher for industry monitoring.

Pulls product feeds from Shopify-style storefronts and persists each
product to the `product_releases` table. Idempotent on
(site_domain, external_product_id) so the daily Celery beat job can call
us as often as it likes — only the first sighting surfaces a Decision
row.

Shopify exposes a public, unauthenticated `/products.json` endpoint on
every storefront (we use this — no scraping, no API key). The same
shape works for `/collections/<slug>/products.json`.

Public entrypoints:
    await fetch_shopify_products(domain) -> list[NormalisedProduct]
    await ingest_shopify_site(db, domain, user_id) -> {new, seen, updated}
    await run_watch_cycle(db, user_id, sites) -> {per-site stats + new Decisions}

WATCHED_SITES below is the canned list for Phase 1 (jewellery + tattoo
verticals). Users can override per-user via a future settings field.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from sqlalchemy.orm import Session

from models import Decision, ProductRelease

logger = logging.getLogger("jarvis.intel.product_watcher")

UA = "JarvisV2/0.2 (industry-product-monitor; +https://jarvis.app)"
TIMEOUT = 20.0
MAX_PAGES = 5  # Shopify caps at 250/page; 5 × 250 = 1250 products / site

# Default canned set — jewellery + tattoo + piercing supplies vertical.
# Each entry is a public Shopify storefront with /products.json reachable.
WATCHED_SITES: list[str] = [
    "wholesalebodyjewellery.com",
    "tishlyon.com",
]


@dataclass
class NormalisedProduct:
    """Source-agnostic product shape. Both Shopify storefronts and any
    future site adapter must produce this."""
    external_id: str
    handle: Optional[str]
    title: str
    vendor: Optional[str]
    product_type: Optional[str]
    tags: list[str] = field(default_factory=list)
    price: Optional[str] = None
    image_url: Optional[str] = None
    url: str = ""
    created_at_remote: Optional[datetime] = None
    published_at_remote: Optional[datetime] = None


# ── Fetch ──────────────────────────────────────────────────────────────────


def _parse_shopify_dt(raw: Any) -> Optional[datetime]:
    if not raw or not isinstance(raw, str):
        return None
    # Shopify returns ISO 8601 with timezone offset, e.g. 2026-05-08T14:31:24+01:00
    try:
        return datetime.fromisoformat(raw)
    except ValueError:
        return None


def _normalise_shopify(p: dict, domain: str) -> NormalisedProduct:
    variants = p.get("variants") or []
    images = p.get("images") or []
    cheapest = None
    for v in variants:
        pr = v.get("price")
        if pr is None:
            continue
        try:
            if cheapest is None or float(pr) < float(cheapest):
                cheapest = pr
        except (TypeError, ValueError):
            continue
    return NormalisedProduct(
        external_id=str(p.get("id")),
        handle=p.get("handle"),
        title=p.get("title") or "(untitled)",
        vendor=p.get("vendor"),
        product_type=p.get("product_type"),
        tags=p.get("tags") if isinstance(p.get("tags"), list) else [],
        price=cheapest,
        image_url=(images[0].get("src") if images and isinstance(images[0], dict) else None),
        url=f"https://{domain}/products/{p.get('handle', '')}",
        created_at_remote=_parse_shopify_dt(p.get("created_at")),
        published_at_remote=_parse_shopify_dt(p.get("published_at")),
    )


async def fetch_shopify_products(
    domain: str,
    *,
    limit_per_page: int = 250,
    max_pages: int = MAX_PAGES,
) -> list[NormalisedProduct]:
    """Walk `/products.json` paginated. Returns [] on any error.

    Shopify ignores filters but obeys ?limit + ?page. If a page returns
    fewer than limit, we know we've hit the end and stop early.
    """
    # Normalise: accept "tishlyon.com", "https://tishlyon.com", or
    # "https://tishlyon.com/". `str.lstrip` strips CHARS, not a prefix,
    # so e.g. "tishlyon.com".lstrip("https://") → "ishlyon.com" — use
    # removeprefix instead.
    host = domain.strip()
    for pre in ("https://", "http://"):
        if host.startswith(pre):
            host = host[len(pre):]
    host = host.rstrip("/")
    base = f"https://{host}/products.json"
    out: list[NormalisedProduct] = []
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as c:
            for page in range(1, max_pages + 1):
                r = await c.get(
                    base,
                    params={"limit": limit_per_page, "page": page},
                    headers={"User-Agent": UA, "Accept": "application/json"},
                )
                if r.status_code != 200:
                    logger.warning("shopify %s page=%s returned %s", domain, page, r.status_code)
                    break
                try:
                    products = r.json().get("products") or []
                except ValueError:
                    logger.warning("shopify %s page=%s non-json body", domain, page)
                    break
                for p in products:
                    if not isinstance(p, dict):
                        continue
                    out.append(_normalise_shopify(p, domain))
                if len(products) < limit_per_page:
                    break  # last page reached
    except Exception:
        logger.exception("shopify fetch failed: %s", domain)
        return []
    return out


# ── Ingest ─────────────────────────────────────────────────────────────────


async def ingest_shopify_site(
    db: Session,
    domain: str,
    user_id: Optional[int],
) -> dict:
    """Fetch + upsert one site. Returns stats dict.

    Idempotent: rows keyed on (site_domain, external_product_id). Re-runs
    update last_seen_at and price (in case of restock or discount) but
    never create duplicate rows.

    Returns:
        {"site": domain, "fetched": N, "new": N, "updated": N}
    """
    products = await fetch_shopify_products(domain)
    if not products:
        return {"site": domain, "fetched": 0, "new": 0, "updated": 0}

    existing_rows = (
        db.query(ProductRelease)
        .filter(ProductRelease.site_domain == domain)
        .all()
    )
    by_ext = {r.external_product_id: r for r in existing_rows}

    now = datetime.utcnow()
    new = updated = 0
    for p in products:
        row = by_ext.get(p.external_id)
        if row is None:
            db.add(
                ProductRelease(
                    user_id=user_id,
                    site_domain=domain,
                    external_product_id=p.external_id,
                    handle=p.handle,
                    title=p.title,
                    vendor=p.vendor,
                    product_type=p.product_type,
                    tags=p.tags,
                    price=p.price,
                    image_url=p.image_url,
                    url=p.url,
                    created_at_remote=p.created_at_remote,
                    published_at_remote=p.published_at_remote,
                    first_seen_at=now,
                    last_seen_at=now,
                    surfaced_to_user=False,
                )
            )
            new += 1
        else:
            row.last_seen_at = now
            # refresh price + image if the storefront changed them
            if p.price and p.price != row.price:
                row.price = p.price
                updated += 1
            if p.image_url and p.image_url != row.image_url:
                row.image_url = p.image_url
    db.commit()
    return {"site": domain, "fetched": len(products), "new": new, "updated": updated}


async def run_watch_cycle(
    db: Session,
    user_id: Optional[int],
    sites: Optional[list[str]] = None,
) -> dict:
    """Top-level entrypoint called by the Celery beat job.

    For each site:
      1. fetch + upsert (`ingest_shopify_site`)
      2. find unsurfaced rows, create a single aggregated Decision row
         per site so the user gets ONE notification per cycle (not 50)
      3. flip surfaced_to_user = True on those rows

    Returns a summary dict for logs / health checks.
    """
    sites = sites or WATCHED_SITES
    summaries: list[dict] = []
    decisions_created = 0
    for domain in sites:
        stats = await ingest_shopify_site(db, domain, user_id)
        summaries.append(stats)

        if user_id is None:
            continue  # multi-tenant: skip Decision creation for system-level runs

        unsurfaced = (
            db.query(ProductRelease)
            .filter(
                ProductRelease.site_domain == domain,
                ProductRelease.surfaced_to_user == False,  # noqa: E712
                ProductRelease.user_id == user_id,
            )
            .order_by(ProductRelease.first_seen_at.desc())
            .limit(50)
            .all()
        )
        if not unsurfaced:
            continue

        # One Decision row per site per cycle. Avoid pile-up.
        sample = ", ".join(f"{r.title}" for r in unsurfaced[:3])
        more = f" (+{len(unsurfaced) - 3} more)" if len(unsurfaced) > 3 else ""
        db.add(
            Decision(
                user_id=user_id,
                source="product_release",
                source_id=f"product_release:{domain}:{int(datetime.utcnow().timestamp())}",
                title=f"{len(unsurfaced)} new product{'s' if len(unsurfaced) != 1 else ''} on {domain}",
                ai_suggestion=(
                    f"New on {domain}: {sample}{more}. "
                    f"Open the product-releases panel to review and decide if any belong on your line."
                ),
                status="pending",
                created_at=datetime.utcnow(),
                context_json={
                    "site_domain": domain,
                    "count": len(unsurfaced),
                    "ids": [r.id for r in unsurfaced],
                    "sample_titles": [r.title for r in unsurfaced[:5]],
                },
            )
        )
        for r in unsurfaced:
            r.surfaced_to_user = True
        decisions_created += 1
    db.commit()

    return {
        "sites": summaries,
        "decisions_created": decisions_created,
        "ran_at": datetime.utcnow().isoformat(),
    }


# ── Helpers for the router / smoke tests ───────────────────────────────────


def domain_from_url(url: str) -> str:
    """Best-effort: 'https://www.tishlyon.com/products/foo' → 'tishlyon.com'."""
    try:
        host = urlparse(url).hostname or url
    except Exception:
        host = url
    return host.lstrip("www.")
