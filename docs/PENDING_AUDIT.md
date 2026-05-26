# JARVIS V2 — Pending Audit + Work Queue

**Generated:** 2026-05-20
**Source of truth for what's left.** Update after every commit that touches pending work.

When resuming a session, read this file first. Pick from "Work Queue (Priority Order)" at the bottom and start. Move items to "Done" once they ship.

---

## Status Overview

| Phase | Built | Partial | Not started | Blocked-on-user |
|---|---|---|---|---|
| Foundation (Steps 0–4, 21) | ✓ all | — | — | — |
| AI surfaces (Steps 5–8) | most | streaming UI, RAG ingest, file UI | — | OpenAI key for embeddings |
| Founder UI (Steps 11–14) | most | Celery beat schedules | — | Connector data |
| Integrations (Steps 9, 10) | — | — | both | Shopify + Freshdesk creds |
| Billing (Step 22) | — | — | full | Stripe account |
| Dev infra (Steps 23, 24, 25) | most | mock-oauth, env.dev, live deploy | — | Railway/Render |
| Phase 2 (Steps 26, 27) | — | — | both | — |
| Cross-cutting (15, 16, 17, 20) | — | — | partly | — |

---

## PARTIAL — backend ready, frontend or scheduler missing

### Step 5 — Streaming chat (UI)
- Backend: `POST /api/chat/stream` (SSE) done in commit 174be51.
- Missing: `frontend/src/components/interface/DraggableChat.tsx` still uses non-streaming `sendChat`. Need:
  - `StreamingChatBubble` component (renders tokens incrementally)
  - EventSource client OR `fetch + ReadableStream` reader
  - Cancel button using AbortController
  - Token usage rendered at end of stream
- Effort: ~30 min.
- No external blocker.

### Step 6 — Multimodal upload (UI + video)
- Backend full: `POST /api/files/upload` (20 MB cap), PDF/CSV/text extraction, image S3 storage, `ChatIn.file_ids` (commit ec5aa7a). Returns 402 until S3 keys set.
- Missing UI (6.7):
  - Paperclip button in `DraggableChat` opening native file picker
  - Drag-drop onto chat window
  - Thumbnail preview before send
  - Upload progress bar
  - Attachment chip in input
- Missing 6.5: video keyframe extraction (`opencv-python-headless`). +80 MB image. Defer until demand.
- Effort: ~45 min for UI. Skip 6.5.
- Blocker: actual uploads need S3_BUCKET/S3_ACCESS_KEY/S3_SECRET_KEY (USER_TASKS #9).

### Step 7 — Personality + quick actions inline UI
- Backend: 6 modes, 10 chips, `/api/chat/personalities`, `/api/chat/quick-actions` (commit cf09148).
- Missing in UI (7.4, 7.5):
  - `PersonalityModeSelector` pills row above chat input (already settable from Settings → AI, but not visible in chat surface)
  - `QuickActionChips` horizontally-scrollable row above input — click chip → submits prompt
- Effort: ~20 min.

### Step 8 — RAG Celery ingest (8.6)
- Backend store + search + inject done (commit 7412b8c). `POST /api/knowledge/note` works for manual adds.
- Missing: Celery beat tasks:
  - `ingest_emails(user_id)` — fetch last 50 from Gmail/Outlook, chunk per thread, embed, upsert
  - `ingest_tasks(user_id)` — Linear/Jira/Notion descriptions → embed
  - `ingest_shopify(user_id)` — order summaries (blocked until Step 9)
  - `ingest_file(file_upload_id)` — newly uploaded file → embed text → chunks
- Effort: ~60 min total, but each requires the corresponding connector to be live.
- Blocker for full coverage: OPENAI_API_KEY (embeddings) + Shopify/Freshdesk for those flavours.

### Step 14 — Founder intelligence Celery jobs
- Done: Decision Inbox CRUD (POST/PATCH/DELETE), DecisionInbox UI, `push_to_github` tool (commit 030c7b2).
- Missing 14.1 auto-populate: `build_decision_inbox(user_id)` Celery task every 15 min. Sources: GitHub PRs awaiting review, Shopify orders >$1k, Freshdesk urgent/aging tickets, Linear/Jira blocked issues.
- Missing 14.2: `prepare_meeting_brief(user_id, event_id)` — 20 min before each calendar event, synthesize attendee context + recent emails + tickets, push as in-app notification + "📋 Brief me" button on CalendarPanel event card.
- Missing 14.3: `analyze_email_commitments(user_id)` — for each new email, ask Claude "does this contain a commitment/deadline?" If yes, show suggestion chip in EmailPanel; one-click creates Linear issue.
- Missing 14.4: Weekly brief — Monday 8am UTC, synthesize Shopify week-on-week + Freshdesk volume + Linear completion + email throughput → top-3 priorities. Deliver in-app + send via Gmail.
- Effort: ~30 min per job + Celery beat infra (~30 min one-time setup).
- Blocker: Celery beat service not in compose. Shopify/Freshdesk integrations not built.

### Step 23 — Local dev (the 3 deferred sub-tasks)
- 23.3 `tools/mock-oauth/` — minimal FastAPI app simulating Google/Microsoft/Slack/GitHub OAuth callbacks for offline E2E tests. Effort ~45 min. Only useful for tests; not blocking.
- 23.5 `backend/.env.dev` — safe local defaults, `MOCK_OAUTH=true`. Effort ~5 min.
- 23.6 `.gitignore` audit — confirm `.env`, `.env.dev`, `*.pyc`, `__pycache__/`, `node_modules/`, `frontend/dist/`, `backups/` are ignored. Effort ~5 min.

### Step 24.4 — Branch protection
- USER TODO — set in GitHub UI on `main` + `staging`: require PR, 1 approval, CI green, no force push.

### Step 25 — Live staging + prod
- USER TODO — needs Railway/Render account (USER_TASKS #10). Runbook in `docs/DEPLOYMENT.md`.

---

## NOT STARTED — needs your credentials

### Step 9 — Shopify
- New connector + `routers/shopify.py` + AI tools + `ShopifyPanel` UI.
- Blocker: SHOPIFY_CLIENT_ID + SHOPIFY_CLIENT_SECRET (USER_TASKS #6 — Shopify Partner account, takes ~30 min).
- Once unlocked: ~3 hours of work for OAuth flow + read methods + 4 tools (orders, products, customers, create_discount) + panel.

### Step 10 — Freshdesk
- New `FreshdeskConnector` (API key auth, NOT OAuth — simpler than Shopify), `/api/freshdesk/status`, AI tools, ticket panel, crisis radar Celery task (30 min schedule).
- Blocker: FRESHDESK_SUBDOMAIN + FRESHDESK_API_KEY (USER_TASKS #7 — free trial).
- Once unlocked: ~2 hours.

### Step 22 — Stripe billing
- `subscription_plan` + `subscription_status` on User. `/billing/checkout` (Stripe Checkout session), `/billing/webhook` (invoice.paid, subscription.deleted), `/billing/portal` (customer portal link). Feature-gate middleware. In-app upgrade prompts at limits.
- Blocker: Stripe account + price IDs (USER_TASKS #8). Identity verification takes 1–3 days.
- Once unlocked: ~3 hours.

### Step 28 — MS Dynamics 365 connector (sales + purchase)
- New `backend/connectors/ms_dynamics.py` (OAuth via Azure AD), AI tools `get_dynamics_sales`, `get_dynamics_purchase_orders`, `get_dynamics_accounts`, optional `create_quote`. Panel + canned prompts.
- Blocker: Azure AD app registration with Dynamics scope + tenant_id + client_id + client_secret. Microsoft creds may share infra with existing outlook_mail / outlook_calendar / teams (same `microsoft` vendor group in `oauth_refresh.py`) but Dynamics scope must be added to the consent screen.
- Once unlocked: ~4 hours (auth flow + 4 tools + UI).

### Step 29 — Freshcaller (CRM call updates)
- New `backend/connectors/freshcaller.py` (API key auth, like planned Freshdesk). AI tool `get_recent_calls`. Surfaces recent calls + missed calls into Decision Inbox.
- Blocker: FRESHCALLER_SUBDOMAIN + FRESHCALLER_API_KEY (Freshworks free trial, ~5 min). Pair with Freshdesk USER_TASKS #7 if user buys the same suite.
- Once unlocked: ~1.5 hours.

### Step 30 — Competitor Ads watcher (Meta Ads Library)
- New `backend/intel/ads_watcher.py` using the Facebook Ad Library API (covers Instagram + Facebook simultaneously — Meta merged the libraries). Daily fetch of `latest ads` per competitor page id, diff against previous run, surface new creatives as Decision rows.
- Phase 2 prerequisite: an auto-discovery pass over Reddit chatter + linked-out vendor lists on wholesalebodyjewellery / tishlyon proposes a competitor list for the user to approve.
- Blocker: Meta developer app + system user access token with `ads_archive` scope. Free, instant approval — see https://www.facebook.com/ads/library/api/ docs.
- Once unlocked: ~3 hours (per-page id resolver + fetcher + diff + UI).

### Step 31 — Celebrity / influencer mention monitor
- Wire celebrity-mention sources into the existing Intel Brief synth pipeline:
  - Reddit (already wired — keyword filter on piercing/jewellery subs)
  - Google News RSS (free, no key): `https://news.google.com/rss/search?q=<query>`
  - Public RSS feeds of jewellery/tattoo trade press (TPS Magazine, Pain Magazine, Inked Mag, BMEzine archive)
- Hard NO on X / Twitter API (paid). Instagram has no clean search API outside Ads Library.
- Effort: ~2 hours; no creds required.

### Step 26 — Unicorn features (Phase 2, post-launch)
- 26.1 Explicit persistent memories ("remember that X")
- 26.2 Relationship graph (enhanced `SenderProfile`)
- 26.3 Platform API (developer access)
- 26.4 Cash-flow watch (Stripe + accounting integration)
- 26.5 Achievement system + shareable weekly card
- 26.6 Daily 7am HTML digest email
- 26.7 White-label config
- Effort: ~2 days per feature. Defer until V1 has paying users.

### Step 27 — Growth / viral mechanics
- Not started. Spec is in master prompt lines 2084+. Mostly product decisions, not code.

---

## CROSS-CUTTING — small gaps

### Step 15 — Frontend updates summary
- Spec lists components to create. Audit which are missing vs which were covered implicitly:
  - `IntelligenceTierSelector` pills above chat — NOT BUILT (lives in Settings instead)
  - Other components — most landed via Settings/TokenMonitor/DecisionInbox/IntelBriefs
- Effort: 1 hour to audit + add tier pills if wanted.

### Step 16 — Things to delete
- Master prompt has explicit deletion list. Never audited. Likely candidates:
  - `tests/test_chat.py` mock target (already updated to JarvisAI; verify nothing else lingers)
  - Old comments referencing claude_client.py (file removed but search for references)
- Effort: 30 min audit.

### Step 17 — Things to amend
- Never audited. Read master prompt lines 1004–1018.
- Effort: 30 min.

### Step 18 — New backend deps
- Implicitly covered (anthropic >=0.40, openai >=1.40, google-generativeai, pypdf, pandas, pgvector, redis, celery, boto3, alembic). Cross-check with master prompt list.

### Step 19 — New frontend deps
- No new deps added beyond what was already in package.json (zustand, framer-motion, three, react-three-fiber). Cross-check with master prompt list. May want `recharts` for richer charts later but inline SVG sparkline ships now.

### Step 20 — `.env.example`
- NOT WRITTEN. `backend/.env` has real values; canonical template missing. Important for new contributors + deploy automation.
- Effort: 10 min. Copy `backend/.env` → `backend/.env.example`, blank all secret values, add comments.

---

## EXTRA — beyond original spec

These shipped on top of the master prompt:

- **Industry signup** (mandatory text field, drives Intel Briefs)
- **Intel Briefs** (periodic public-web monitor: Reddit + HN → Claude synthesis)
- **5 legal/policy docs** in `legal/` — privacy, terms, AI disclosure, cookies, acceptable use

Document references: see `docs/BUILD_PROGRESS.md` for full step-by-step status.

---

## WORK QUEUE (priority order)

Pick the top item; ship; move to "Done"; commit.

**Unblocked, ready to ship:**

1. **Step 14.3** — Email-commitment Celery task. Needs scheduled Gmail/Outlook ingest first (Step 8.6 ingest_emails — needs OPENAI_API_KEY for embeddings).
2. **Step 14.2** — Smart meeting-prep Celery task. Fires 20 min before each calendar event. Needs calendar-fetch loop + reliable scheduling per-event (currently no easy way to schedule one-off tasks; would need celery-beat dynamic schedule or a periodic scanner).
3. **Step 14.4** — Weekly business brief Celery beat at Monday 8am UTC. Synthesises Shopify week-on-week + Freshdesk volume + Linear completion + email throughput → top-3 priorities. Blocked on Shopify + Freshdesk being live.
4. **Step 8.6** — Celery ingest tasks: ingest_emails / ingest_tasks / ingest_shopify / ingest_file. Pulls connector data → embeds → upserts KnowledgeChunk. Needs OPENAI_API_KEY for embeddings (or fallback to per-provider).
5. **mock-oauth wiring** — `MOCK_OAUTH=true` env switch in routers/auth.py that points all `/authorize` + `/token` URLs at the mock server. ~30 min.
6. **JWT refresh endpoint** — 30d → 7d access token + 30d refresh token. POST /api/users/refresh. Needs RefreshToken table + frontend silent-refresh logic. ~1 hr.
7. **Connector token auto-refresh** — Each connector's `access()` should catch 401 → use stored refresh_token → retry. Per-provider logic (Google/Microsoft use OAuth2 refresh). ~3 hr.
8. **feed.py Redis cache** — 2-min TTL per user. /feed hits 11 APIs per call; should hit cache instead. ~30 min.
9. **slowapi per-user keying** — When authenticated, rate-limit by user_id, not IP. ~20 min.

**Blocked on user credentials:**

10. **Step 9 — Shopify** — UNBLOCK when SHOPIFY_CLIENT_ID is set (USER_TASKS #6).
11. **Step 10 — Freshdesk** — UNBLOCK when FRESHDESK_API_KEY is set (USER_TASKS #7).
12. **Step 22 — Stripe** — UNBLOCK when STRIPE_SECRET_KEY is set (USER_TASKS #8).
13. **Step 25 — Live deploy** — UNBLOCK when Railway/Render account exists (USER_TASKS #10).

**Phase 2 (defer until paying users):**

14. **Step 26** — Unicorn features: persistent memories, relationship graph, platform API, cash-flow watch, achievements, weekly digest email, white-label config.
15. **Step 27** — Growth / viral mechanics.

---

## Done log (move items here as they ship)

- 2026-05-26 5f08ec5: Phase 1 industry product-release watcher (Shopify storefront JSON, daily Celery beat, ProductRelease model + alembic 0005, /api/product-releases endpoints, aggregated Decision rows, jewellery/piercing/tattoo subreddit defaults). Fix: lstrip→removeprefix in domain normaliser.
- 2026-05-26 377a7e6: streaming tool-use end-to-end (backend AIChunk(type=tool_call), JarvisAI.stream tool loop) + frontend tool_start/tool_end pills.
- 2026-05-20 7fdf358: queue 12 — mock-oauth FastAPI server (port 9100, single-use codes, canned API data)
- 2026-05-20 78eb2b0: queue 10 — build_decision_inbox Celery task + 15-min beat schedule
- 2026-05-20 6cfce57: queue 9 — Step 16/17 cleanup (JWT_SECRET hard requirement, VITE_API_BASE env)
- 2026-05-20 686a603: queue 5/6/7/8 — streaming SSE chat UI + cancel + paperclip+drag-drop upload + tier pills + personality cycler + quick-action chips
- 2026-05-20 3cada91: queue 4 — Celery beat service + intel.run_due 10-min schedule
- 2026-05-20 2048977: queue 1/2/3 — .env.example + .env.dev + hardened .gitignore
- 2026-05-20 b769046: Industry signup + Intel Briefs + 5 legal docs
- 2026-05-20 a03b2f3: Step 25 deployment runbook (docs only)
- 2026-05-20 030c7b2: Step 14 decision inbox + push_to_github tool
- 2026-05-20 873d76c: Step 11 dashboard use-case prompts
- 2026-05-20 d1ac49c: Steps 13 + 12 settings page + token monitor
- 2026-05-20 60ac358: Steps 23 + 24 dev setup + CI/CD
- 2026-05-20 ec5aa7a: Step 6 multimodal file upload (backend)
- 2026-05-20 174be51: Step 5 streaming SSE (backend)
- 2026-05-20 7412b8c: Step 8 user context + RAG (backend)
- 2026-05-20 cf09148: Step 7 personality + quick actions (backend)
- 2026-05-20 e88332a: Step 4 BYOAK backend
- 2026-05-20 37ed1e2: Steps 21 + 3 provider-agnostic AI + tier system
- 2026-05-20 0455cf8: Step 2 v2 models
- 2026-05-20 6c31b99: Step 1 postgres + redis + celery + s3 + alembic
- 2026-05-20 3f4c2e4: Step 0 security hardening
