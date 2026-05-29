# Changelog

All notable changes to JARVIS V2.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: [SemVer](https://semver.org).

## [Unreleased]

### Changed
- /api/feed now caches its 11-connector fan-out in Redis (key `feed:<user_id>`, TTL 120 s). Subsequent dashboard refreshes hit Redis (~ms) instead of fan-out (~seconds). Invalidated on connector disconnect.
- Migration safety: alembic upgrade head moved off the Dockerfile CMD; only the backend service (via docker-compose / Railway deploy command) runs migrations. Worker and beat boot without racing on schema.
- Rate limiter (slowapi) now keys on `user:<id>` for authenticated requests (was IP-only). Users behind shared NAT no longer share buckets.

### Added
- Hallucination guardrail (`backend/ai/guardrails.py`): regex detector that flags past-tense action-claim phrases ("Done, boss", "I sent the email", "Created a task", "Scheduled a meeting", etc.) when the matching tool was NOT invoked in the same chat turn. Wired into both `JarvisAI.respond()` and `JarvisAI.stream()` — final response is annotated with a `[guardrail]` correction header, and stream emits a new `{"type": "correction", ...}` SSE event. Persona system prompt hardened with a non-negotiable Action Policy section. 12 new unit tests in `tests/test_guardrails.py`.
- Frontend wired to the `correction` SSE event in `jarvisStore.streamChat` + `DraggableChat`: when the backend guardrail fires, the streamed (lying) assistant text is replaced with the corrected version and an 8-second error toast surfaces the flagged phrase. Users now see when JARVIS catches itself.
- GDPR routes: DELETE /api/users/me (cascade-deletes all user-owned rows; rate-limited 3/hour; requires email-confirm in body) and GET /api/users/me/export (streams a zip of every user-owned table as JSON; secrets redacted; rate-limited 5/hour). Settings → Account stub buttons now functional.
- Celebrity / influencer mention monitor (Phase 3): Google News RSS + trade-press RSS + Reddit keyword filter. New Mention model + alembic 0007 + Celery beat every 12 h (gated on jewellery/piercing/tattoo industry keywords). New endpoints: GET /api/mentions, POST /refresh, GET /sources. New chat tool: get_recent_mentions.
- Pre-push hook (.githooks/pre-push) runs backend pytest + frontend tsc before allowing a push to main. Activate once per clone with `make setup`. Use `git push --no-verify` only in emergencies.
- Rate limits on `/api/chat` (30/min per user) and `/api/chat/stream` (20/min per user) to bound AI-cost runaway. JarvisAI also enforces `UserSettings.daily_token_budget` before each provider call — raises `TokenBudgetExceededError` (returns 429) if today's input+output tokens already exceeded the budget.
- Step 0: Security hardening — fatal boot check on missing secrets, Fernet at-rest
  encryption for OAuth tokens, one-time code exchange for OAuth-redirect flows
  (no more ?token=JWT in URLs), rate-limited register/login (5/min), 2000-char
  chat input cap, env-driven CORS.
- Step 1: PostgreSQL + Redis + Celery + Cloudflare R2 / S3-compatible storage +
  Alembic. Removed legacy startup migration script.
- Step 2: 8 new tables — user_settings, user_context, token_usage,
  knowledge_chunks (pgvector 1536-dim), file_uploads, decisions,
  shopify_configs, freshdesk_configs.
- Step 21: Provider-agnostic AI layer — Anthropic, OpenAI, Groq, Mistral,
  Google Gemini behind a single AIProvider interface.
- Step 3: Tier system (eco / intelligent / scientist) with per-provider model
  mapping + cost tables. Anthropic prompt caching enabled. Token usage tracked
  per call. Cache hits visible (cache_read_tokens).
- Step 4: BYOAK — encrypted per-user API keys via PUT /api/settings/api-keys,
  Test-key endpoint, preferences and active-provider toggles. /api/tokens/today,
  /history, /session dashboards.
- Step 7: 6 personality modes (caveman default — saves ~60% output tokens).
  GET /api/chat/quick-actions returns 10 pre-built chips.
- Step 8: UserContext CRUD + pgvector RAG knowledge base (semantic search with
  OpenAI text-embedding-3-small, graceful no-op without OpenAI key).
- Step 5: SSE streaming chat at POST /api/chat/stream with per-token deltas
  and final usage event.
- Step 6: Multimodal file upload — POST /api/files/upload (20 MB cap), PDF text
  extraction, CSV → markdown, image references via S3, chat ChatIn.file_ids
  attaches files to the user turn.
- Step 23: docker-compose.dev.yml hot-reload override, Makefile (dev / prod /
  migrate / seed / test / lint / shell / psql / logs / backup), seed.py with
  3 test users + 30 days of fake usage + 5 RAG chunks.
- Step 24: GitHub Actions CI (Postgres + Redis services, pytest, frontend
  type-check + build, Docker image smoke build), .pre-commit-config.yaml
  (ruff, gitleaks, trailing whitespace), CHANGELOG.md.
- Sentry SDK scaffolded backend (FastAPI + SQLAlchemy + Celery integrations) and frontend (React). No-op until SENTRY_DSN_BACKEND / VITE_SENTRY_DSN are set in env.

### Changed
- backend/ai/claude_client.py REMOVED; logic moved to backend/ai/jarvis_ai.py.
- /api/chat now returns `{"reply": ..., "usage": {...}}` (backward compatible
  — frontend can ignore the new field).

## [0.1.0] — 2026-05-19
- Initial JARVIS V1 baseline (login/signup, OAuth connectors, chat, voice
  HUD, draggable resizable chat window, profile dropdown, dashboard
  customizer, toast notifications).
