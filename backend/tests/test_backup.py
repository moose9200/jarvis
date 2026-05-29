"""Nightly pg_dump backup task — unit tests.

We don't shell out to a real `pg_dump` here; we patch the subprocess
call so the test runs without postgres-client installed locally. The
storage layer is patched the same way so we don't talk to a real S3.
"""
from datetime import date
from unittest.mock import patch, MagicMock

import pytest

from tasks import backup as backup_mod


# ── pg_dump_to_s3 — orchestrator ─────────────────────────────────────────


def test_skips_when_storage_unconfigured():
    """When `storage.is_configured()` returns False, the task must
    short-circuit BEFORE shelling out to pg_dump."""
    with patch.object(backup_mod, "_pg_dump_bytes") as dump_mock, \
         patch("storage.is_configured", return_value=False):
        result = backup_mod.pg_dump_to_s3()
    assert result == {"skipped": True, "reason": "storage_unconfigured"}
    dump_mock.assert_not_called()


def test_happy_path_uploads_and_prunes():
    """When configured, the task pg_dumps, uploads with the right key
    + content type, then runs the retention prune."""
    fake_blob = b"\x1f\x8b\x08\x00fake-gzipped-dump"
    with patch.object(backup_mod, "_pg_dump_bytes", return_value=fake_blob), \
         patch("storage.is_configured", return_value=True), \
         patch("storage.upload_bytes") as upload_mock, \
         patch.object(backup_mod, "_prune_old_backups", return_value={"total": 1, "kept": 1, "deleted": 0, "unparsed": 0}) as prune_mock:
        result = backup_mod.pg_dump_to_s3(today="20260529")

    expected_key = "backups/jarvis_20260529.sql.gz"
    upload_mock.assert_called_once_with(
        fake_blob, key=expected_key, content_type="application/gzip"
    )
    prune_mock.assert_called_once()
    assert result["key"] == expected_key
    assert result["size_bytes"] == len(fake_blob)
    assert "prune" in result


def test_returns_error_when_pg_dump_missing():
    """If pg_dump isn't installed in the image, the task must NOT
    attempt to upload — it should surface a structured error so the
    operator can fix the Dockerfile."""
    with patch.object(backup_mod, "_pg_dump_bytes", side_effect=FileNotFoundError()), \
         patch("storage.is_configured", return_value=True), \
         patch("storage.upload_bytes") as upload_mock:
        result = backup_mod.pg_dump_to_s3()
    assert result == {"error": "pg_dump_missing"}
    upload_mock.assert_not_called()


# ── _classify_keep — retention windows ───────────────────────────────────


def test_classify_keep_keeps_recent_dailies():
    """All dates within the last KEEP_DAILY days should be kept."""
    today = date(2026, 5, 29)
    dates = [date.fromordinal(today.toordinal() - i) for i in range(10)]
    kept = backup_mod._classify_keep(dates, today=today)
    # all 10 daily dates fit under the KEEP_DAILY=14 budget
    assert set(dates).issubset(kept)


def test_classify_keep_prunes_very_old_dates():
    """Dates older than weekly + monthly windows get dropped."""
    today = date(2026, 5, 29)
    # 40 dates spanning ~280 days back — well past every window
    dates = [date.fromordinal(today.toordinal() - 7 * i) for i in range(40)]
    kept = backup_mod._classify_keep(dates, today=today)
    assert len(kept) < len(dates)


def test_classify_keep_picks_one_per_iso_week():
    """Two backups in the same ISO week — only one survives the weekly
    window once they fall outside the daily window."""
    today = date(2026, 5, 29)
    # Two adjacent days within the same ISO week, but well outside
    # KEEP_DAILY=14 (set them ~100 days back).
    old_a = date.fromordinal(today.toordinal() - 100)  # Wed
    old_b = date.fromordinal(today.toordinal() - 99)   # Thu — same ISO week
    assert old_a.isocalendar()[:2] == old_b.isocalendar()[:2]
    kept = backup_mod._classify_keep([old_a, old_b], today=today)
    intersection = kept & {old_a, old_b}
    # weekly window picks the most-recent of the two same-week dates
    assert len(intersection) == 1
    assert old_b in intersection  # most-recent wins


# ── _parse_key_date — key format guard ───────────────────────────────────


def test_parse_key_date_accepts_valid_format():
    assert backup_mod._parse_key_date("backups/jarvis_20260529.sql.gz") == date(2026, 5, 29)


def test_parse_key_date_rejects_garbage():
    assert backup_mod._parse_key_date("backups/not-a-backup.txt") is None
    assert backup_mod._parse_key_date("uploads/jarvis_20260529.sql.gz") is None
    assert backup_mod._parse_key_date("backups/jarvis_99999999.sql.gz") is None


# ── _prune_old_backups — wires through delete() ──────────────────────────


def test_prune_calls_delete_for_old_keys_only():
    """Stale keys should be removed; recent ones must survive."""
    today = date(2026, 5, 29)
    very_old = date(2020, 1, 1)
    recent = today
    keys = [
        f"backups/jarvis_{recent.strftime('%Y%m%d')}.sql.gz",
        f"backups/jarvis_{very_old.strftime('%Y%m%d')}.sql.gz",
        "backups/junk.txt",  # unparseable — should be left alone
    ]
    with patch.object(backup_mod, "_list_existing_keys", return_value=keys), \
         patch("storage.delete") as del_mock:
        summary = backup_mod._prune_old_backups(today=today)
    # very_old key should be the only one deleted
    deleted_keys = [c.args[0] for c in del_mock.call_args_list]
    assert any("2020" in k for k in deleted_keys)
    assert not any(recent.strftime("%Y%m%d") in k for k in deleted_keys)
    assert summary["unparsed"] == 1
