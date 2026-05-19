# JARVIS Build Progress Tracker

> Claude Code: Read this first every session. Update after every sub-task. Commit after every step.

## Current Status
**Last session:** 2026-05-20  
**Last completed:** Step 13 (Settings page, 6 tabs) + Step 12 (Token Monitor slide-out) — full frontend wiring done.
**Next task:** Step 11 (dashboard use-case prompts) OR Step 14 (founder intelligence features)
**Blocked by:** Nothing autonomously. Several features blocked-on-user for credentials (see USER_TASKS.txt): Shopify/Freshdesk integrations (Step 9/10), Stripe billing (Step 22), S3 file uploads (Step 6 backend works, needs S3 keys to be useful).

---

## HOW TO UPDATE THIS FILE
After each sub-task: change `[ ]` to `[x]` and update "Current Status" above.
After each full step: git commit with message `step X: description`.

---

## STEP 0 — Security Fixes (do first, blocks everything)
- [x] 0.1 Crash on missing JWT_SECRET / SESSION_SECRET (also TOKEN_ENCRYPTION_KEY)
- [x] 0.2 Remove ?token= query param from get_current_user, add one-time code exchange
- [x] 0.3 Encrypt OAuth tokens at rest (create backend/crypto.py)
- [x] 0.4 Fix error leakage in chat.py (no detail=str(e), no traceback.print_exc)
- [x] 0.5 Rate limit /register and /login (5/minute)
- [x] 0.6 Add max_length=2000 to ChatIn message field
- [x] 0.7 CORS from ALLOWED_ORIGINS env var

**Commit:** `git commit -m "step 0: security hardening"`

---

## STEP 1 — Infrastructure Migration
- [x] 1.1 SQLite → PostgreSQL (update DATABASE_URL, docker-compose.yml)
- [x] 1.2 Add Redis service to docker-compose.yml
- [x] 1.3 Switch slowapi rate limiter to Redis backend
- [x] 1.4 Celery worker setup (backend/worker.py + docker-compose service)
- [x] 1.5 S3/R2 file storage (backend/storage.py)
- [x] 1.6 Alembic init (replace migrations.py)

**Commit:** `git commit -m "step 1: postgres + redis + celery + s3"`

---

## STEP 2 — New DB Models
- [x] 2.1 UserSettings model (ai_provider, default_model, api keys per provider)
- [x] 2.2 UserContext model (about_me, communication_style, priorities, team)
- [x] 2.3 TokenUsage model (date, model, input/output tokens, cost_usd)
- [x] 2.4 KnowledgeChunk model (pgvector embedding, source_type, content)
- [x] 2.5 FileUpload model (s3_key, file_type, processed)
- [x] 2.6 Decision model (source, title, status, ai_suggestion)
- [x] 2.7 ShopifyConfig model (shop_domain, access_token_encrypted)
- [x] 2.8 FreshdeskConfig model (subdomain, api_key_encrypted)
- [x] 2.9 Alembic migration: hand-written 0002_v2_models.py (autogen output was noisy, hand-write was cleaner)

**Commit:** `git commit -m "step 2: v2 database models + migration"`

---

## STEP 21 — Provider-Agnostic AI Layer (build before Step 3)
- [x] 21.1 backend/ai/providers/base.py (AIProvider ABC, AIResponse, AIChunk)
- [x] 21.2 backend/ai/providers/anthropic_provider.py
- [x] 21.3 backend/ai/providers/openai_provider.py (covers OpenAI + Groq + Mistral)
- [x] 21.4 backend/ai/providers/google_provider.py (lazy import)
- [x] 21.5 backend/ai/providers/factory.py (get_provider factory)
- [x] 21.6 backend/ai/tiers.py (TIER_MODELS + TIER_COSTS for all providers)
- [x] 21.7 Update JarvisAI class to use abstraction (replace direct anthropic import) — renamed claude_client.py → jarvis_ai.py, deleted legacy file
- [x] 21.8 Add provider-specific deps to requirements.txt (openai>=1.40, google-generativeai>=0.8, anthropic>=0.40)

**Commit:** `git commit -m "step 21: provider-agnostic AI abstraction layer"`

---

## STEP 3 — Intelligence Tier System
- [x] 3.1 Tier config wired through provider abstraction (not direct Anthropic)
- [x] 3.2 Extended thinking plumbed (Anthropic thinking_budget param; openai/o3 reasoning is internal; Sonnet 4.5 thinking off by default in `intelligent`, on for `scientist`)
- [x] 3.3 Token usage tracked after every complete() call → TokenUsage table
- [x] 3.4 Prompt caching on system prompt (Anthropic: cache_control ephemeral) — verified cache_read=1197 on 2nd request
- [x] 3.5 Token usage returned in chat response: {reply, usage: {provider, model, input, output, cache_read, cache_write, thinking, cost_usd}}

**Commit:** `git commit -m "step 3: intelligence tier system with thinking"`

---

## STEP 4 — BYOAK (Bring Your Own API Key)
- [x] 4.1 Settings endpoint: PUT /api/settings/api-keys (all 5 providers + elevenlabs + github_pat) + GET /api/settings + POST /api/settings/test-key + PUT /api/settings/preferences + PUT /api/settings/active-provider
- [x] 4.2 JarvisAI reads user's provider + key from UserSettings (decrypted), falls back to env
- [x] 4.3 Graceful 402 if no API key configured for chosen provider (NoAPIKeyError → 402)
- [x] 4.4 GET /api/tokens/today, /api/tokens/history, /api/tokens/session

**Commit:** `git commit -m "step 4: BYOAK multi-provider support"`

---

## STEP 23 — Local Dev Setup
- [x] 23.1 docker-compose.dev.yml with hot reload for backend (uvicorn --reload via volume mount) and celery debug logging
- [x] 23.2 Makefile (dev / prod / down / build / migrate / migrate-new / seed / test / lint / shell / psql / redis-cli / logs / backup)
- [ ] 23.3 tools/mock-oauth/ — DEFERRED. Frontend uses real OAuth via the one-time code exchange; mock server adds value only for offline E2E tests.
- [x] 23.4 backend/seed.py — 3 test users (founder/pro/free, pw test1234), UserContext for founder, 5 RAG chunks, 30 days of TokenUsage history
- [ ] 23.5 backend/.env.dev — DEFERRED. Current .env is reused; .env.dev would only matter once mock-oauth lands.
- [ ] 23.6 .gitignore additions — TODO if not already covered

**Commit:** `git commit -m "step 23: local dev setup + seed data"`

---

## STEP 24 — Version Control + CI/CD
- [x] 24.1 .github/workflows/ci.yml — 3 jobs: backend-test (pytest + postgres + redis), frontend-build (tsc + vite build), docker-build smoke. Runs on push to main/staging + PRs.
- [x] 24.2 .pre-commit-config.yaml — ruff (auto-fix), trailing-whitespace, end-of-file-fixer, check-added-large-files, detect-private-key, gitleaks.
- [x] 24.3 CHANGELOG.md with current unreleased entries summarizing steps 0–6, 21, 23, 24.
- [ ] 24.4 Branch protection rules — USER TODO (must set in GitHub UI; see USER_TASKS.txt #11).

**Commit:** `git commit -m "step 24: CI/CD + pre-commit hooks"`

---

## STEP 5 — Streaming Chat (SSE)
- [x] 5.1 POST /api/chat/stream SSE endpoint (text/event-stream with X-Accel-Buffering:no)
- [x] 5.2 JarvisAI.stream() yields dicts {type:"token", text}, {type:"done", usage}, {type:"error", text}
- [ ] 5.3 Frontend StreamingChatBubble component (deferred to frontend pass)
- [ ] 5.4 Cancel button mid-stream (deferred to frontend pass — AbortController)
- [x] 5.5 Token usage emitted in the done event (provider, model, in, out, cache, cost_usd)

**Commit:** `git commit -m "step 5: streaming SSE chat"`

---

## STEP 6 — Multimodal File Upload
- [x] 6.1 POST /api/files/upload (multipart, 20MB max) + GET /files, GET /files/{id}, DELETE /files/{id}
- [x] 6.2 Image processing → S3 URL stored in FileUpload.s3_key for vision use at chat time
- [x] 6.3 PDF text extraction via pypdf (caps 50 pages)
- [x] 6.4 CSV → markdown table via pandas (caps 100 rows)
- [ ] 6.5 Video → key frame extraction — DEFERRED (opencv-python-headless adds ~80MB; can land in a follow-up commit when video uploads are wanted)
- [x] 6.6 ChatIn extended with file_ids: list[int] (max 10); JarvisAI builds multimodal content array
- [ ] 6.7 Frontend: paperclip button + drag-drop + thumbnail preview — DEFERRED to frontend pass

**Commit:** `git commit -m "step 6: multimodal file upload"`

**BLOCKED-ON-USER:** uploads return 402 until S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY are set in backend/.env (USER_TASKS #9 — Cloudflare R2 free 10GB).

---

## STEP 7 — Personality Modes + Quick Actions
- [x] 7.1 PERSONALITY_INJECTIONS dict in persona.py (6 modes: caveman/expert/creative/executive/devils_advocate/coach)
- [x] 7.2 Default: caveman (injected into ALL prompts — saves tokens). Reads from UserSettings.personality_mode.
- [x] 7.3 GET /api/chat/quick-actions (10 chips) + GET /api/chat/personalities
- [ ] 7.4 Frontend: PersonalityModeSelector pills above chat  (Step 13 frontend)
- [ ] 7.5 Frontend: QuickActionChips row (horizontally scrollable)  (Step 13 frontend)

**Commit:** `git commit -m "step 7: personality modes + quick action chips"`

---

## STEP 8 — User Profile + RAG Knowledge Base
- [x] 8.1 GET/PUT /api/context endpoints
- [x] 8.2 UserContext injected into every JARVIS session (via _build_context_block in jarvis_ai.py)
- [x] 8.3 backend/ai/embedder.py (text-embedding-3-small, 1536-dim; graceful None if no OpenAI key)
- [x] 8.4 backend/ai/knowledge.py (search via pgvector cosine `<=>`)
- [x] 8.5 Relevant chunks injected before each AI response (via _build_knowledge_block)
- [ ] 8.6 Celery tasks: ingest_emails, ingest_tasks, ingest_shopify, ingest_file — deferred to a follow-up commit (needs connector data pipeline)
- [x] 8.7 GET /api/knowledge/status + POST /api/knowledge/note + GET /api/knowledge/search

**Commit:** `git commit -m "step 8: user context + RAG knowledge base"`

---

## STEP 13 — Settings Page (Frontend)
- [x] 13.1 Settings modal opened from ProfileDropdown → Settings menu item (overlay modal, not route — fits the dashboard model better)
- [x] 13.2 AI tab: active provider cards (gated on key presence), 3 tier cards, 6 personality pills, response length toggle, daily budget + alert %
- [x] 13.3 API Keys tab: 5 providers + ElevenLabs, masked previews, Save/Test/Remove per row
- [x] 13.4 About Me tab: about_me, communication_style, priorities, business_context (autosave on blur), team_members read-only display
- [x] 13.5 Integrations tab: points back to existing IntegrationsModal (already production-ready)
- [x] 13.6 GitHub tab: repo URL + PAT (KeyRow reused)
- [x] 13.7 Account tab: Sign Out works; Change Password / Export / Delete are stubs marked "pending"

**Commit:** `git commit -m "step 13: settings page (6 tabs)"`

---

## STEP 12 — Token Monitor UI
- [x] 12.1 /api/tokens/today + /api/tokens/history + /api/tokens/session (built in Step 3)
- [x] 12.2 TokenMonitor slide-out panel (right side, triggered by $ button in top bar)
- [x] 12.3 Tier selector lives in Settings → AI (one source of truth)
- [x] 12.4 Daily usage progress bar (green < 60%, yellow < 90%, red ≥ 90%)
- [x] 12.5 7-day sparkline — inline SVG gradient polyline (no recharts dep)
- [x] 12.6 Budget settings wired to UserSettings via Settings → AI tab

**Commit:** `git commit -m "step 12: token monitor UI"`

---

## STEP 22 — Billing + Stripe
- [ ] 22.1 Stripe account setup (user does this — see USER TODOS)
- [ ] 22.2 Add subscription_plan + subscription_status to User model
- [ ] 22.3 POST /api/billing/checkout (create Stripe checkout session)
- [ ] 22.4 POST /api/billing/webhook (handle invoice.paid, subscription.deleted)
- [ ] 22.5 GET /api/billing/portal (Stripe Customer Portal link)
- [ ] 22.6 Feature gate middleware (check plan before premium endpoints)
- [ ] 22.7 In-app upgrade prompts at usage limits

**Commit:** `git commit -m "step 22: stripe billing + plan gates"`

---

## STEP 9 — Shopify Integration
- [ ] 9.1 Shopify OAuth flow (shop-specific, permanent token)
- [ ] 9.2 backend/connectors/shopify.py (all read + write methods)
- [ ] 9.3 Shopify AI tools added to tools.py
- [ ] 9.4 Shopify pre-built prompt suggestions
- [ ] 9.5 Frontend ShopifyPanel dashboard component
- [ ] 9.6 Cross-integration: Shopify + Freshdesk customer lookup

**Commit:** `git commit -m "step 9: shopify integration"`

---

## STEP 10 — Freshdesk Integration
- [ ] 10.1 FreshdeskConnector (API key auth, not OAuth)
- [ ] 10.2 GET /api/freshdesk/status verification
- [ ] 10.3 Freshdesk AI tools added to tools.py
- [ ] 10.4 Customer crisis radar Celery task (30min schedule)
- [ ] 10.5 Frontend: ticket panel + top issues widget

**Commit:** `git commit -m "step 10: freshdesk integration + crisis radar"`

---

## STEP 11 — Dashboard Use-Case Prompts
- [x] 11.1 UseCasePromptDrawer component — opens on ? button in any PanelWrapper, sends selected prompt to chat (switches to text mode).
- [x] 11.2 Email panel: 5 prompts (GET /api/chat/suggestions/email)
- [x] 11.3 Calendar panel: 5 prompts
- [x] 11.4 Tasks panel: 5 prompts
- [x] 11.5 Shopify panel: 5 prompts (will surface once panel is added in Step 9)
- [x] 11.6 Freshdesk panel: 5 prompts (will surface once panel is added in Step 10)
- [x] 11.7 Home/general: 5 daily-use prompts via `home` panel key
- [x] BONUS: Projects panel: 5 prompts; GET /api/chat/suggestions (bulk) for prefetch

**Commit:** `git commit -m "step 11: dashboard use-case prompts"`

---

## STEP 14 — Founder Intelligence Features
- [ ] 14.1 Decision inbox: GET/PATCH /api/decisions, Celery build job
- [ ] 14.2 Smart meeting prep: Celery task 20min before events
- [ ] 14.3 Proactive task creation: email commitment detection
- [ ] 14.4 Weekly business brief: Monday 8am Celery beat
- [ ] 14.5 GitHub push tool: push_to_github in tools.py
- [ ] 14.6 Frontend: DecisionInboxPanel, MeetingPrepBanner

**Commit:** `git commit -m "step 14: founder intelligence features"`

---

## STEP 26 — Unicorn Features (Phase 2, post-launch)
- [ ] 26.1 JARVIS Memory (explicit persistent memories)
- [ ] 26.2 Relationship graph (enhanced SenderProfile)
- [ ] 26.3 Platform API (developer access)
- [ ] 26.4 Cash flow watch (Stripe + accounting integration)
- [ ] 26.5 Achievement system + shareable weekly card
- [ ] 26.6 JARVIS Digest Email (daily 7am HTML email)
- [ ] 26.7 White-label config

**Commit:** `git commit -m "step 26: unicorn features phase 1"`

---

## STEP 25 — Deployment
- [ ] 25.1 Staging environment on Railway/Render
- [ ] 25.2 Production environment configured
- [ ] 25.3 Enhanced /api/health checks (DB + Redis)
- [ ] 25.4 Alembic runs in Dockerfile CMD before app start
- [ ] 25.5 Blue-green deploy tested
- [ ] 25.6 Domain + Cloudflare configured (user does this)

**Commit:** `git commit -m "step 25: production deployment setup"`

---

## USER TODOS (you do these, not Claude Code)
- [ ] Buy domain + set up Cloudflare
- [ ] Submit Google OAuth verification (console.cloud.google.com)
- [ ] Submit Microsoft Azure app verification
- [ ] Write privacy policy (iubenda.com or termly.io)
- [ ] Create Shopify Partner account + app (partners.shopify.com)
- [ ] Create Stripe account
- [ ] Set up Cloudflare R2 storage (free 10GB)
- [ ] Create Railway/Render account for hosting
- [ ] Set up Freshdesk trial + get API key

---

## NOTES / DECISIONS LOG
_Add notes here as you make architecture decisions or discover issues_

- 2026-05-20: Spec written. Provider-agnostic AI layer required — no direct Anthropic imports in business logic.
- 2026-05-20: BYOAK model confirmed. Users bring their own API key (Anthropic/OpenAI/Groq/Mistral/Google).
- 2026-05-20: Default personality = caveman (saves ~60% output tokens for users).
- 2026-05-20: Steps 21 + 3 complete (+ 3 of 4 BYOAK sub-tasks). Notes:
  - claude_client.py REMOVED. New entrypoint: backend/ai/jarvis_ai.py (JarvisAI class).
  - AIProvider abstraction in backend/ai/providers/{base,anthropic_provider,openai_provider,google_provider,factory}.py. OpenAICompatibleProvider covers OpenAI + Groq + Mistral via base_url.
  - Tier system in backend/ai/tiers.py with TIER_MODELS (model + thinking_budget + max_tokens) and TIER_COSTS (USD/1M) for all 5 providers x 3 tiers.
  - Thinking budget is plumbed but OFF for `intelligent` tier (saves cost) — ON for `scientist`.
  - Prompt caching: system prompt wrapped with cache_control: ephemeral. Verified cache_read=1197 tokens on 2nd request.
  - TokenUsage row written after every model call. Multi-turn tool loops accumulate into one usage block returned in the chat response.
  - New endpoints under /api/tokens: today / history?days=N / session?limit=N. Today endpoint reports budget headroom.
  - chat now returns {"reply": str, "usage": {provider, model, input, output, cache_read, cache_write, thinking, cost_usd}}. Frontend is backward-compat (ignores usage if unread).
  - NoAPIKeyError → 402 with friendly "Add yours in Settings → AI Keys" message.
  - tests/test_chat.py updated for JarvisAI mock target.
- 2026-05-20: Step 2 complete. Notes:
  - UserSettings carries BYOAK keys for 5 providers (anthropic, openai, groq, mistral, google) + elevenlabs + github PAT. All *_encrypted columns must be wrapped with crypto.{encrypt,decrypt}.
  - FileUpload added `extracted_text` and `extra` fields beyond the spec to capture PDF/CSV/transcript output and arbitrary processor metadata.
  - Decision added `source_id`, `snoozed_until`, `decided_at` for richer state.
  - TokenUsage tracks cache_write_tokens + thinking_tokens too (Anthropic prompt caching + extended thinking).
  - 15 tables total now (incl. alembic_version).
- 2026-05-20: Step 1 complete. Notes:
  - Postgres uses pgvector/pgvector:pg16 — vector extension created in initial migration for Step 8 RAG.
  - Postgres + Redis are NOT exposed on host ports (port 6379 conflicted with local brew redis). They're reachable via compose internal network only. Use `docker compose exec postgres psql -U jarvis jarvis` to inspect.
  - Existing SQLite data was dropped — fresh Postgres DB. Acceptable for dev.
  - Dockerfile CMD runs `alembic upgrade head` before uvicorn so a stale schema can't boot.
  - oauth_code now backed by Redis (GETDEL atomic single-use). Falls back to in-memory dict when REDIS_URL is unset (for tests).
  - storage.py is stubbed — is_configured() returns false until user sets S3_* env vars (USER_TASKS #9). All file-upload calls raise StorageUnconfiguredError until then.
  - Health check now reports per-dep status: {database, redis, storage}.
- 2026-05-20: Step 0 complete. Notes:
  - Added TOKEN_ENCRYPTION_KEY as a required boot-time secret (in addition to JWT_SECRET, SESSION_SECRET).
  - One-time OAuth code store is in-memory (backend/oauth_code.py) — single-worker only. Migrate to Redis in Step 1.3.
  - crypto.decrypt() falls back to plaintext passthrough for legacy rows so existing OAuth connections keep working until the next reconnect. New writes are always Fernet-encrypted.
  - Shared `backend/rate_limit.py` exports a single Limiter so router decorators and main.py exception handler bind to the same instance.
