"""Celery worker — background jobs (ingestion, schedulers, long-running AI work).

Discovers tasks from modules listed in `include`. Add new task modules there as
they're built. Start with:
    celery -A worker worker --loglevel=info

For Celery beat (scheduled tasks):
    celery -A worker beat --loglevel=info
"""
from __future__ import annotations

import os
import sys

# Boot-time secrets check — same as main.py. The worker shares the process model
# so missing secrets must fail fast here too.
from dotenv import load_dotenv

load_dotenv()

for _required in ("JWT_SECRET", "SESSION_SECRET", "TOKEN_ENCRYPTION_KEY"):
    if not os.getenv(_required):
        print(f"FATAL: {_required} env var not set", file=sys.stderr)
        sys.exit(1)

from celery import Celery

_SENTRY_DSN_BACKEND = os.getenv("SENTRY_DSN_BACKEND")
if _SENTRY_DSN_BACKEND:
    import sentry_sdk
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
    sentry_sdk.init(
        dsn=_SENTRY_DSN_BACKEND,
        environment=os.getenv("ENV", "development"),
        release=os.getenv("GIT_SHA", "dev"),
        traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.1")),
        profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0.1")),
        send_default_pii=False,
        integrations=[CeleryIntegration(), SqlalchemyIntegration()],
    )

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "jarvis",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=[
        "tasks.intel",            # IntelBrief auto-runs
        "tasks.decisions",        # Decision Inbox builder
        "tasks.product_watcher",  # Industry product-release watcher (Phase 1)
        "tasks.mention_watcher",  # Celebrity / influencer mention watcher (Phase 3)
        # Add task modules here as new background jobs are built:
        # "tasks.email_ingest",
        # "tasks.shopify_sync",
        # "tasks.knowledge_indexer",
    ],
)

celery_app.conf.update(
    timezone="UTC",
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    task_track_started=True,
    task_time_limit=300,         # 5 min hard limit
    task_soft_time_limit=270,    # 4.5 min soft (raises SoftTimeLimitExceeded)
    worker_max_tasks_per_child=200,  # recycle workers to fight slow leaks
    broker_connection_retry_on_startup=True,
)


# ── Beat schedule ────────────────────────────────────────────────────────────
# Every 10 min, scan for IntelBriefs whose frequency_minutes have elapsed
# since last_run_at and enqueue them. Beat runs as its own service (see
# docker-compose `beat` service). Without beat running, briefs only run when
# the user hits POST /api/intel-briefs/{id}/run from the UI.
celery_app.conf.beat_schedule = {
    "intel-run-due-every-10-min": {
        "task": "intel.run_due",
        "schedule": 600.0,   # seconds
    },
    "decisions-build-every-15-min": {
        "task": "decisions.build_for_all",
        "schedule": 900.0,   # 15 minutes
    },
    # Industry product-release watcher (Shopify storefronts). Runs once
    # every 6 hours — products don't change often and the public JSON
    # endpoints are unauthenticated, so we stay polite.
    "product-watcher-every-6-hours": {
        "task": "product_watcher.run_for_all",
        "schedule": 21600.0,   # 6 hours
    },
    # Celebrity / influencer mention watcher (Google News + trade-press
    # RSS + Reddit). Lower-cardinality data than product feeds — runs
    # every 12 hours so we stay polite with the unauthenticated RSS
    # endpoints.
    "mention-watcher-every-12-hours": {
        "task": "mention_watcher.run_for_all",
        "schedule": 43200.0,   # 12 hours
    },
}


@celery_app.task(name="diagnostics.ping")
def ping() -> str:
    """Smoke task — used by /api/health to confirm worker connectivity."""
    return "pong"
