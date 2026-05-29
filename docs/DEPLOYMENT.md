# JARVIS V2 — Deployment Guide

Reference for shipping to staging + production. Most of the heavy lifting
(Postgres, Redis, Alembic, Docker) is already in place — this document
captures the runbook + rollback strategy.

---

## Environments

```
local    docker-compose.yml + docker-compose.dev.yml on your machine
staging  Railway/Render staging env, deploys on push to `staging` branch
prod     Railway/Render prod env, requires manual approval in GitHub Actions
```

Staging mirrors prod (real Postgres, real Redis, real Celery worker) so the
only thing that changes between staging and prod is the API keys and the
domain.

---

## First-time production setup (one-off, ~30 min)

1. **Provision hosting** (Railway recommended — see USER_TASKS.txt #10)
   - One Railway project, four services (all built from `./backend` unless noted):
     - `backend`  (custom start command:
                   `alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT`)
     - `worker`   (custom start command:
                   `celery -A worker worker --loglevel=info`)
     - `beat`     (custom start command:
                   `celery -A worker beat --loglevel=info` — ONE replica only)
     - `frontend` (build context: `./frontend`)
   - Add Railway add-ons: `PostgreSQL` (pick pgvector-enabled) and `Redis`.
   - Connect both add-ons to backend + worker + beat; Railway injects
     DATABASE_URL and REDIS_URL automatically.
   - **Migration ownership**: ONLY the `backend` service deploy command runs
     `alembic upgrade head`. Worker and beat services run plain `celery ...`
     commands — they must NOT run alembic, or you'll have N containers racing
     on schema migration. See "Migration ownership" below.

2. **Set environment variables** (Railway dashboard → service → Variables)

   Required (app will refuse to boot without these):
   ```
   JWT_SECRET             (≥32 chars, generate fresh: openssl rand -base64 32)
   SESSION_SECRET         (≥32 chars, fresh)
   TOKEN_ENCRYPTION_KEY   (44-char Fernet key: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
   ```

   Provider keys (at minimum Anthropic for chat to work without BYOAK):
   ```
   ANTHROPIC_API_KEY
   ```

   Domain + CORS:
   ```
   FRONTEND_URL=https://yourdomain.com
   ALLOWED_ORIGINS=https://yourdomain.com
   ```

   OAuth redirect URIs — update each provider's console to match:
   ```
   GOOGLE_REDIRECT_URI=https://yourdomain.com/api/auth/google/callback
   MS_REDIRECT_URI=https://yourdomain.com/api/auth/microsoft/callback
   SLACK_REDIRECT_URI=https://yourdomain.com/api/auth/slack/callback
   GITHUB_REDIRECT_URI=https://yourdomain.com/api/auth/github/callback
   ```

   Optional but recommended for full feature set:
   ```
   S3_BUCKET, S3_ENDPOINT_URL, S3_ACCESS_KEY, S3_SECRET_KEY   (file uploads)
   STRIPE_SECRET_KEY + STRIPE_WEBHOOK_SECRET                  (billing)
   ELEVENLABS_API_KEY                                         (voice)
   ```

3. **Point your domain at Railway** (cloudflare DNS → CNAME to railway domain).

4. **First deploy**
   - Push the current `main` branch to GitHub.
   - Railway auto-builds and runs `alembic upgrade head && uvicorn main:app`.
   - First migration creates pgvector extension + all 14 tables.

5. **Optional — seed a demo account**
   ```bash
   railway run --service=backend python seed.py
   ```
   This creates founder@test.com / pro@test.com / free@test.com (pw test1234).
   **DELETE these accounts after testing.** Do not leave seed users in prod.

---

## Routine deploys

```
feature/your-thing → PR into staging
                    → CI runs (.github/workflows/ci.yml: backend tests +
                      frontend type-check/build + docker smoke build)
                    → merge → Railway auto-deploys to staging
                    → manual test
                    → PR staging → main
                    → manual approve in GH Actions → prod deploy
```

Each backend deploy runs `alembic upgrade head` before uvicorn starts
(via the backend service deploy command). If the migration fails, the
container exits non-zero and Railway holds the previous deploy in place
— no half-migrated state. Worker and beat services do NOT run alembic.
See "Migration ownership" below.

---

## Zero-downtime migration rules

**Always** follow this sequence for schema changes. Single-deploy renames or
type changes are how production goes down.

### Adding a column
```
Deploy 1: ALTER TABLE ADD COLUMN x TEXT (nullable)
Deploy 2: backfill data + add NOT NULL if needed
```

### Removing a column
```
Deploy 1: stop reading + writing it in code
Deploy 2: ALTER TABLE DROP COLUMN
```

### Renaming a column
```
Deploy 1: add new column, write to BOTH old and new
Deploy 2: switch reads to new column
Deploy 3: stop writing to old column
Deploy 4: drop old column
```

### Generating migrations
```bash
make migrate-new name="add_user_settings_billing_plan"
# Review the generated file in backend/alembic/versions/
# Edit if autogen got something wrong (it often misses pgvector + JSON types)
# Test: make migrate
# Commit: git add backend/alembic/versions/<file>.py && git commit
```

---

## Migration ownership

`alembic upgrade head` is run by **exactly one service** per deploy: the
`backend` service. This is enforced by construction:

- `backend/Dockerfile` CMD is plain `uvicorn main:app ...` — no alembic.
- `docker-compose.yml` backend service has an explicit `command:` that
  prepends `alembic upgrade head && ...`.
- On Railway, set the backend service deploy command to:
  ```
  alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port $PORT
  ```
- Worker and beat services run plain `celery ...` commands — they share
  the schema written by backend and must NOT run alembic. With N worker
  replicas, having alembic in the image CMD would cause N containers to
  race on schema migration on every boot.

If you add a new service that uses the same backend image (e.g. a one-off
job runner), give it its own `command:` and do NOT include alembic unless
you are intentionally making it the migration leader and disabling
migration on backend.

---

## Rollback strategy

### Code rollback
- Railway/Render: one-click rollback to previous deploy in the dashboard.
- Or: revert the commit in main and push; CI redeploys.

### Database rollback
- `alembic downgrade -1` reverses the last migration **iff** it was
  additive (added columns/tables). Destructive ops can't be safely
  rolled back without a backup restore.
- Backup before every prod deploy:
  ```bash
  make backup  # dumps to backups/jarvis_YYYYMMDD_HHMMSS.sql
  ```
- Restore:
  ```bash
  docker compose exec -T postgres psql -U jarvis jarvis < backups/<file>.sql
  ```

---

## Health checks

`/api/health` returns:
```json
{
  "status": "ok",
  "version": "0.2.0",
  "api_keys": {"anthropic": true, "elevenlabs": false},
  "deps":     {"database": true, "redis": true, "storage": false}
}
```

- `deps.database == false` → Postgres is down/unreachable. Railway auto-
  restarts the service.
- `deps.redis == false` → rate limiting falls back to in-memory; oauth_code
  falls back to in-memory dict. Single-worker only — multi-worker deploys
  will see broken rate-limit + lost oauth codes until Redis is back.
- `deps.storage == false` → S3 not configured. File uploads return 402.

Set up Railway health-check on `/api/health` so Railway only routes traffic
to a backend that can talk to Postgres + Redis.

---

## Monitoring

Minimum production observability — set these up once you have paying users:

1. **Uptime** — UptimeRobot or Better Uptime (both have free tiers).
   Pings `/api/health` every 60s, alerts via Slack/email on failure.

2. **Error tracking** — Sentry (free tier 5k events/mo).
   ```bash
   pip install sentry-sdk
   # In main.py:
   import sentry_sdk
   sentry_sdk.init(dsn=os.getenv("SENTRY_DSN"), traces_sample_rate=0.1)
   ```

3. **Logs** — Railway/Render show stdout/stderr; pipe to BetterStack or Logtail
   for retention.

4. **Cost monitoring** — `/api/tokens/today` per user; aggregate via cron
   to a Slack channel daily so you spot a spend spike fast.

---

## Secret rotation

If a key leaks (gitleaks pre-commit catches most but not all):
1. **JWT_SECRET** — rotate → ALL users get logged out (they re-login).
2. **SESSION_SECRET** — rotate → mid-flight OAuth flows abort; users retry.
3. **TOKEN_ENCRYPTION_KEY** — DO NOT rotate without a re-encryption job. All
   stored OAuth tokens + BYOAK keys become unreadable. If you must:
   ```python
   # backend/scripts/rotate_encryption.py
   # 1. Decrypt all *_encrypted columns with OLD key
   # 2. Re-encrypt with NEW key
   # 3. Atomic UPDATE
   ```

---

## Branch protection (USER TODO)

Set in GitHub UI:
- `main`: require PR, require 1 approval, require CI green, no force push.
- `staging`: require PR, require CI green, no force push.
- Auto-delete head branches after merge.

---

## Pre-launch checklist

Before flipping the DNS to production:

- [ ] All Step 0 security fixes verified (boot crashes on missing secrets,
      OAuth tokens encrypted, no ?token= in URLs, rate limits enabled,
      chat input cap, env-driven CORS).
- [ ] Privacy policy live at yourdomain.com/privacy (USER_TASKS #3).
- [ ] Google OAuth verification submitted (USER_TASKS #1).
- [ ] Microsoft Azure verification submitted (USER_TASKS #2).
- [ ] HTTPS forced (Railway + Cloudflare both do this automatically).
- [ ] Backups scheduled (Railway has automatic Postgres snapshots; verify).
- [ ] Sentry DSN set, errors flow into your dashboard.
- [ ] Health endpoint reports `deps.database=true, deps.redis=true`.
- [ ] Stripe webhook signing secret matches the live key (USER_TASKS #8).
- [ ] At least one paying user invited as a beta tester before opening signups.
