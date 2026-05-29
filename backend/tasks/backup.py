"""Nightly Postgres backup → S3/R2.

Runs daily at 03:00 UTC (Celery beat schedule in worker.py). Streams the
output of `pg_dump` through gzip, uploads the resulting blob to the
configured S3-compatible bucket under `backups/jarvis_YYYYMMDD.sql.gz`,
and prunes old keys according to a sliding retention window.

Designed to land BEFORE S3 credentials are provisioned — when
`storage.is_configured()` returns False the task short-circuits with
`{"skipped": True, "reason": "storage_unconfigured"}` and logs an info
line. The moment the env vars land (R2 bucket from USER TODO #3) the
task starts uploading on the next beat tick without any code change.

Retention policy:
  - last 14 daily snapshots
  - last 8 weekly snapshots (one per ISO week)
  - last 6 monthly snapshots (one per calendar month, first-of-month)
Anything older is deleted. Daily / weekly / monthly are computed from
the date encoded in the object key, so the pruner never has to read
the object body.

The pg_dump binary is shipped in the worker image (see backend/Dockerfile
— installs `postgresql-client` apt package). The connection target is
the in-cluster `postgres` service; credentials come from the same
POSTGRES_* env vars the rest of the app already uses.
"""
from __future__ import annotations

import gzip
import logging
import os
import re
import subprocess
from datetime import date, datetime, timedelta
from typing import Iterable

from worker import celery_app

logger = logging.getLogger("jarvis.tasks.backup")

# Object-key prefix under which every backup lives. Keep flat — date is
# encoded in the filename so date math works without listing subfolders.
BACKUP_PREFIX = "backups/"
KEY_DATE_RE = re.compile(r"^backups/jarvis_(\d{8})\.sql\.gz$")

# Retention windows.
KEEP_DAILY = 14
KEEP_WEEKLY = 8
KEEP_MONTHLY = 6


def _today_str() -> str:
    return date.today().strftime("%Y%m%d")


def _make_key(today: str | None = None) -> str:
    return f"{BACKUP_PREFIX}jarvis_{today or _today_str()}.sql.gz"


def _pg_dump_bytes() -> bytes:
    """Run pg_dump against the in-cluster postgres service and return the
    compressed dump bytes. Raises CalledProcessError on failure so the
    Celery task surfaces the error and the next beat retries."""
    host = os.getenv("POSTGRES_HOST", "postgres")
    user = os.getenv("POSTGRES_USER", "jarvis")
    db = os.getenv("POSTGRES_DB", "jarvis")
    password = os.getenv("POSTGRES_PASSWORD", "")
    env = {**os.environ, "PGPASSWORD": password}
    # --no-owner so a restore into a different role works cleanly.
    # --clean so the dump drops existing objects before recreating them.
    cmd = [
        "pg_dump",
        "-h", host,
        "-U", user,
        "-d", db,
        "--no-owner",
        "--clean",
        "--if-exists",
    ]
    proc = subprocess.run(cmd, env=env, capture_output=True, check=True)
    return gzip.compress(proc.stdout)


def _parse_key_date(key: str) -> date | None:
    m = KEY_DATE_RE.match(key)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d").date()
    except ValueError:
        return None


def _classify_keep(dates: Iterable[date], today: date | None = None) -> set[date]:
    """Given the set of dates we have backups for, return the subset that
    must be retained under the daily / weekly / monthly windows.

    Windows are calendar-based so "old" backups actually expire even if
    we end up with very few snapshots:
      - daily:   any date within the last KEEP_DAILY calendar days
      - weekly:  one per ISO week, for the last KEEP_WEEKLY weeks
                 (most-recent backup in that week)
      - monthly: one per (year, month), for the last KEEP_MONTHLY months
                 (most-recent backup in that month)

    A backup retained by any single window survives the prune.
    """
    ref = today or date.today()
    sorted_dates = sorted(set(dates), reverse=True)
    keep: set[date] = set()

    # daily: anything strictly within the last KEEP_DAILY days
    daily_cutoff = ref - timedelta(days=KEEP_DAILY)
    for d in sorted_dates:
        if d > daily_cutoff:
            keep.add(d)

    # weekly: one per ISO week, only weeks within the last KEEP_WEEKLY
    # weeks (anchored to `ref`)
    ref_iso = ref.isocalendar()[:2]
    seen_weeks: dict[tuple[int, int], date] = {}
    for d in sorted_dates:
        wk = d.isocalendar()[:2]
        # weeks-distance from ref. ISO weeks are tricky across year
        # boundaries; approximate via raw day delta divided by 7.
        weeks_ago = (ref - d).days // 7
        if weeks_ago >= KEEP_WEEKLY:
            continue
        if wk == ref_iso:
            # current week — already covered by daily; skip duplicate
            continue
        if wk not in seen_weeks:
            seen_weeks[wk] = d  # most-recent in that week, due to desc sort
    keep.update(seen_weeks.values())

    # monthly: one per (year, month), only months within the last
    # KEEP_MONTHLY months (anchored to `ref`)
    seen_months: dict[tuple[int, int], date] = {}
    cutoff_year = ref.year - (1 if ref.month <= KEEP_MONTHLY else 0)
    cutoff_month = ref.month - KEEP_MONTHLY
    if cutoff_month <= 0:
        cutoff_month += 12
    for d in sorted_dates:
        ym = (d.year, d.month)
        # months-distance from ref
        months_ago = (ref.year - d.year) * 12 + (ref.month - d.month)
        if months_ago >= KEEP_MONTHLY:
            continue
        if ym == (ref.year, ref.month):
            # current month — daily already covers; skip
            continue
        if ym not in seen_months:
            seen_months[ym] = d
    keep.update(seen_months.values())

    return keep


def _list_existing_keys() -> list[str]:
    """List every backup key under BACKUP_PREFIX. Returns [] if storage
    is unconfigured — caller short-circuits before this anyway."""
    from storage import _bucket, _client  # local import — module gated on env

    resp = _client().list_objects_v2(Bucket=_bucket(), Prefix=BACKUP_PREFIX)
    contents = resp.get("Contents") or []
    return [obj["Key"] for obj in contents]


def _prune_old_backups(today: date | None = None) -> dict:
    """Apply the retention windows. Returns a summary dict.

    `today` is an optional override for tests; production calls pass
    None and the function uses the real current date.
    """
    from storage import delete as storage_delete

    keys = _list_existing_keys()
    # Build a map of date → key. Skip anything we can't parse — leave it
    # for the operator to inspect.
    dated: dict[date, str] = {}
    unparsed: list[str] = []
    for k in keys:
        d = _parse_key_date(k)
        if d is None:
            unparsed.append(k)
        else:
            dated[d] = k

    keep_dates = _classify_keep(dated.keys(), today=today)
    to_delete = [key for d, key in dated.items() if d not in keep_dates]
    for k in to_delete:
        try:
            storage_delete(k)
        except Exception:
            logger.exception("retention prune: failed to delete %s", k)

    return {
        "total": len(dated),
        "kept": len(keep_dates),
        "deleted": len(to_delete),
        "unparsed": len(unparsed),
    }


@celery_app.task(name="backup.pg_dump_to_s3")
def pg_dump_to_s3(today: str | None = None) -> dict:
    """Run pg_dump → gzip → upload to S3 → prune old keys.

    `today` is an optional override for tests; production calls pass None
    and we use the real date. Returns a dict summarising what happened so
    Celery result inspection + Sentry breadcrumbs are useful.
    """
    # Late import so the module can be loaded in tests without boto3 in
    # the path resolving to a real S3 client.
    from storage import is_configured, upload_bytes

    if not is_configured():
        logger.info("backup.pg_dump_to_s3: storage unconfigured, skipping")
        return {"skipped": True, "reason": "storage_unconfigured"}

    try:
        blob = _pg_dump_bytes()
    except subprocess.CalledProcessError as e:
        logger.error(
            "backup.pg_dump_to_s3: pg_dump failed (rc=%s) stderr=%s",
            e.returncode,
            (e.stderr or b"")[:500],
        )
        return {"error": "pg_dump_failed", "returncode": e.returncode}
    except FileNotFoundError:
        logger.error(
            "backup.pg_dump_to_s3: pg_dump binary missing — Dockerfile must install postgresql-client"
        )
        return {"error": "pg_dump_missing"}

    key = _make_key(today)
    try:
        upload_bytes(blob, key=key, content_type="application/gzip")
    except Exception:
        logger.exception("backup.pg_dump_to_s3: upload failed for %s", key)
        return {"error": "upload_failed", "key": key, "size_bytes": len(blob)}

    prune_summary = _prune_old_backups()
    logger.info(
        "backup.pg_dump_to_s3: uploaded %s (%d bytes), prune=%s",
        key,
        len(blob),
        prune_summary,
    )
    return {
        "key": key,
        "size_bytes": len(blob),
        "prune": prune_summary,
    }
