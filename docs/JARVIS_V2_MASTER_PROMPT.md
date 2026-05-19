# JARVIS v2 — Master Build Prompt for Claude Code

## WHO YOU ARE AND WHAT YOU'RE BUILDING

You are building JARVIS — a web-based AI personal assistant for founders and busy non-technical people. Target users: people who use Gmail, ChatGPT, basic computer tools but cannot code. The UI is a 3D holographic Iron Man-style HUD.

This is an existing codebase. Do NOT start from scratch. Read every file before touching anything.

**Repo:** `/Users/hemant/jarvis`  
**Stack:** FastAPI (Python 3.11) + React 18 + Vite + Three.js + SQLite → PostgreSQL + Docker Compose  
**Current branch:** `main`

---

## CURRENT CODEBASE — READ BEFORE TOUCHING ANYTHING

```
backend/
  main.py              — FastAPI app, CORS, rate limiting, router registration
  models.py            — SQLAlchemy models (User, OAuthToken, EmailHistory, SenderProfile, ConversationTurn, ConversationSummary)
  database.py          — DB engine + session
  migrations.py        — manual migrations
  requirements.txt     — Python deps
  routers/
    auth.py            — OAuth flows for 11 connectors
    users.py           — register, login, /me, get_current_user dependency
    feed.py            — aggregated feed from all 11 connectors
    chat.py            — POST /api/chat (sync, non-streaming)
    email_intelligence.py — email collect + priority endpoints
  connectors/
    base.py            — abstract Connector class
    gmail.py, outlook_mail.py, outlook_calendar.py, google_calendar.py
    slack.py, teams.py, whatsapp.py, github.py, linear.py, jira.py, notion.py
  intelligence/
    email_scorer.py    — relationship + recency + urgency scoring
    history_collector.py — pulls email history into DB
  ai/
    claude_client.py   — JarvisClaude class, tool loop, MAX_TOOL_TURNS=8
    tools.py           — 13 tool schemas + dispatch function
    memory.py          — ConversationMemory (window=20, compression via Haiku)
    persona.py         — SYSTEM_PROMPT ("You are JARVIS, address user as boss...")

frontend/src/
  App.tsx              — main app, auth gate, HUD + panels
  store/jarvisStore.ts — Zustand store
  components/
    hud/HUDScene.tsx
    panels/ (CalendarPanel, EmailPanel, TaskPanel, ProjectPanel)
    interface/ (DraggableChat, VoiceVisualizer, ModeToggle)
    onboarding/IntegrationsModal.tsx
    auth/AuthPage.tsx
    ui/ (Toast, ProfileDropdown, DashboardCustomizer)
  hooks/ (useWakeWord, useVoice)
```

**Known issues already identified:**
- SQLite (not production-ready, breaks under concurrent writes)
- OAuth tokens stored plaintext in DB
- JWT secret has hardcoded fallback "jarvis-jwt-2026"
- Session secret has hardcoded fallback "dev-secret"
- ?token= query param leaks JWT into server logs
- detail=str(e) in chat.py leaks stack traces to browser
- CORS hardcoded to localhost
- Rate limiter is in-memory (breaks multi-worker + restart)
- No rate limit on /register and /login endpoints
- Chat message has no max length
- Model hardcoded as "claude-sonnet-4-5" (outdated)

---

## STEP 0: SECURITY FIXES — DO THESE FIRST, BEFORE ANYTHING ELSE

### 0.1 Crash on missing secrets
In `backend/main.py`, add at the top (after load_dotenv):
```python
import sys
if not os.getenv("JWT_SECRET"):
    print("FATAL: JWT_SECRET env var not set", file=sys.stderr)
    sys.exit(1)
if not os.getenv("SESSION_SECRET"):
    print("FATAL: SESSION_SECRET env var not set", file=sys.stderr)
    sys.exit(1)
```
Remove all default fallback strings. Never `os.getenv("JWT_SECRET", "some-default")`.

### 0.2 Remove ?token= query param auth
In `backend/routers/users.py` `get_current_user()`, remove the `token_param` Query parameter entirely. OAuth redirect flows must use a short-lived one-time code instead:
- Add endpoint `GET /api/auth/token-exchange?code=XXX` that exchanges a 60-second one-time code for a JWT
- OAuth callback sets the one-time code in Redis, frontend polls/redirects to exchange it
- This keeps JWT out of URLs, server logs, referrer headers

### 0.3 Encrypt OAuth tokens at rest
In `backend/models.py`, `OAuthToken.access_token` and `refresh_token` are plaintext. Create `backend/crypto.py`:
```python
from cryptography.fernet import Fernet
import os, base64

def _key():
    raw = os.getenv("TOKEN_ENCRYPTION_KEY", "")
    if not raw:
        raise RuntimeError("TOKEN_ENCRYPTION_KEY not set")
    return Fernet(raw.encode() if len(raw) == 44 else base64.urlsafe_b64encode(raw.encode()[:32]))

def encrypt(value: str) -> str:
    return _key().encrypt(value.encode()).decode()

def decrypt(value: str) -> str:
    return _key().decrypt(value.encode()).decode()
```
Wrap all `tok.access_token = ...` writes with `encrypt()`, all `.access_token` reads with `decrypt()`. Add `TOKEN_ENCRYPTION_KEY` to `.env.example`.

### 0.4 Fix error leakage in chat.py
Replace:
```python
except Exception as e:
    traceback.print_exc()
    raise HTTPException(status_code=500, detail=str(e))
```
With:
```python
except Exception:
    import logging
    logging.getLogger("jarvis").exception("chat error")
    raise HTTPException(status_code=500, detail="Internal error. Try again.")
```

### 0.5 Rate limit auth endpoints
Add `@limiter.limit("5/minute")` to `/api/users/register` and `/api/users/login`.

### 0.6 Add input length limit
In `chat.py` ChatIn model: `message: str = Field(..., max_length=2000, min_length=1)`

### 0.7 Fix CORS
In `main.py`, replace hardcoded origins list with:
```python
origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost").split(",")]
```
Add `ALLOWED_ORIGINS=https://yourdomain.com` to `.env.example`.

---

## STEP 1: INFRASTRUCTURE MIGRATION

### 1.1 SQLite → PostgreSQL
- Replace `DATABASE_URL=sqlite:///./data/jarvis.db` with `DATABASE_URL=postgresql://...` in `.env.example`
- Install `psycopg2-binary` and `pgvector` in `requirements.txt`
- Install `alembic` — replace `migrations.py` with proper Alembic setup: `alembic init alembic`
- Run `alembic revision --autogenerate -m "initial"` after all models defined
- Update `docker-compose.yml`: add `postgres` service:
```yaml
postgres:
  image: pgvector/pgvector:pg16
  environment:
    POSTGRES_DB: jarvis
    POSTGRES_USER: jarvis
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
  volumes:
    - jarvis_pg:/var/lib/postgresql/data
  ports:
    - "5432:5432"
```
- Add `depends_on: [postgres]` to backend service

### 1.2 Redis
Add to `docker-compose.yml`:
```yaml
redis:
  image: redis:7-alpine
  ports:
    - "6379:6379"
```
Install `redis`, `celery[redis]` in requirements. Add `REDIS_URL=redis://redis:6379/0` to `.env.example`.

### 1.3 Switch rate limiter to Redis
```python
from slowapi import Limiter
from slowapi.util import get_remote_address
limiter = Limiter(key_func=get_remote_address, storage_uri=os.getenv("REDIS_URL"))
```

### 1.4 Celery setup
Create `backend/worker.py`:
```python
from celery import Celery
import os
celery_app = Celery("jarvis", broker=os.getenv("REDIS_URL"), backend=os.getenv("REDIS_URL"))
celery_app.conf.timezone = "UTC"
```
Add celery worker to `docker-compose.yml`:
```yaml
worker:
  build: ./backend
  command: celery -A worker worker --loglevel=info
  env_file: backend/.env
  depends_on: [postgres, redis]
```

### 1.5 File storage
Install `boto3`. Add to `.env.example`: `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ENDPOINT_URL` (use Cloudflare R2 or AWS S3). Create `backend/storage.py` with `upload_file(bytes, filename) -> str` returning public URL.

---

## STEP 2: NEW DATABASE MODELS

Add to `backend/models.py`:

```python
from pgvector.sqlalchemy import Vector

class UserSettings(Base):
    __tablename__ = "user_settings"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    default_model = Column(String, default="claude-sonnet-4-6")  # eco/intelligent/scientist
    response_length = Column(String, default="detailed")  # brief/detailed/deep
    daily_token_budget = Column(Integer, default=100000)
    budget_alert_pct = Column(Integer, default=80)
    personality_mode = Column(String, default="caveman")
    anthropic_api_key_encrypted = Column(Text, nullable=True)  # BYOAK
    elevenlabs_api_key_encrypted = Column(Text, nullable=True)
    github_repo_url = Column(String, nullable=True)
    github_pat_encrypted = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class UserContext(Base):
    __tablename__ = "user_context"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    about_me = Column(Text, nullable=True)           # role, company, industry
    communication_style = Column(Text, nullable=True) # how they like emails written
    priorities = Column(Text, nullable=True)          # what matters most
    team_members = Column(JSON, nullable=True)        # [{name, role, relationship}]
    business_context = Column(Text, nullable=True)    # key business info
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class TokenUsage(Base):
    __tablename__ = "token_usage"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    date = Column(String, index=True)   # "2026-05-20"
    model = Column(String)
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    cost_usd = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source_type = Column(String)  # email/calendar/task/shopify/upload
    source_id = Column(String)
    content = Column(Text)
    embedding = Column(Vector(1536), nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class FileUpload(Base):
    __tablename__ = "file_uploads"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String)
    file_type = Column(String)  # image/pdf/video/csv/text
    s3_key = Column(String)
    size_bytes = Column(Integer)
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

class Decision(Base):
    __tablename__ = "decisions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    source = Column(String)   # github_pr/shopify_order/freshdesk_ticket/linear_issue
    title = Column(String)
    context_json = Column(JSON)
    status = Column(String, default="pending")  # pending/approved/rejected/delegated/snoozed
    ai_suggestion = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ShopifyConfig(Base):
    __tablename__ = "shopify_configs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    shop_domain = Column(String)   # mystore.myshopify.com
    access_token_encrypted = Column(Text)
    scope = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

class FreshdeskConfig(Base):
    __tablename__ = "freshdesk_configs"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    subdomain = Column(String)  # yourcompany.freshdesk.com
    api_key_encrypted = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
```

---

## STEP 3: INTELLIGENCE TIER SYSTEM

### 3.1 Model mapping
In `backend/ai/claude_client.py`, replace the single MODEL constant with:

```python
INTELLIGENCE_TIERS = {
    "eco": {
        "model": "claude-haiku-4-5-20251001",
        "thinking_budget": 1024,
        "max_tokens": 2048,
        "cost_per_1k_input": 0.00025,
        "cost_per_1k_output": 0.00125,
    },
    "intelligent": {
        "model": "claude-sonnet-4-6",
        "thinking_budget": 4096,
        "max_tokens": 4096,
        "cost_per_1k_input": 0.003,
        "cost_per_1k_output": 0.015,
    },
    "scientist": {
        "model": "claude-opus-4-7",
        "thinking_budget": 10000,
        "max_tokens": 8192,
        "cost_per_1k_input": 0.015,
        "cost_per_1k_output": 0.075,
    },
}
```

In `JarvisClaude.__init__`, read user's tier from `UserSettings.default_model`, fall back to "intelligent". Apply `thinking` parameter block:
```python
thinking = {"type": "enabled", "budget_tokens": tier["thinking_budget"]}
```
Pass `thinking=thinking` in `client.messages.create(...)`. Extended thinking requires `betas=["interleaved-thinking-2025-05-14"]` for Opus 4.7.

### 3.2 Token usage tracking
After every `client.messages.create()` call, record usage:
```python
usage = resp.usage
cost = (usage.input_tokens * tier["cost_per_1k_input"] / 1000 +
        usage.output_tokens * tier["cost_per_1k_output"] / 1000)
db.add(TokenUsage(
    user_id=self.user_id,
    date=datetime.utcnow().strftime("%Y-%m-%d"),
    model=tier["model"],
    input_tokens=usage.input_tokens,
    output_tokens=usage.output_tokens,
    cache_read_tokens=getattr(usage, "cache_read_input_tokens", 0),
    cost_usd=cost,
))
db.commit()
```
Return token usage in every chat response: `{"reply": text, "usage": {"input": N, "output": N, "cost_usd": X}}`.

### 3.3 Prompt caching
System prompt is expensive to re-send. Add cache_control to system:
```python
system=[{
    "type": "text",
    "text": system_text,
    "cache_control": {"type": "ephemeral"}
}]
```
This caches the system prompt for 5 minutes — saves ~80% of input tokens for active users.

---

## STEP 4: BYOAK — BRING YOUR OWN API KEY

### 4.1 Backend
Add to `backend/routers/settings.py` (new file):
```python
@router.put("/settings/api-keys")
def save_api_keys(payload: ApiKeysIn, db=Depends(get_db), user=Depends(get_current_user)):
    settings = get_or_create_settings(db, user.id)
    if payload.anthropic_api_key:
        settings.anthropic_api_key_encrypted = encrypt(payload.anthropic_api_key)
    if payload.elevenlabs_api_key:
        settings.elevenlabs_api_key_encrypted = encrypt(payload.elevenlabs_api_key)
    db.commit()
    return {"saved": True}
```

In `JarvisClaude.__init__`, pull API key from user settings first, fall back to env:
```python
settings = db.query(UserSettings).filter_by(user_id=user_id).first()
api_key = (decrypt(settings.anthropic_api_key_encrypted)
           if settings and settings.anthropic_api_key_encrypted
           else os.getenv("ANTHROPIC_API_KEY", ""))
if not api_key:
    raise HTTPException(status_code=402, detail="No Anthropic API key. Add yours in Settings.")
self.client = anthropic.AsyncAnthropic(api_key=api_key)
```

### 4.2 Token usage endpoints
```python
GET /api/tokens/today      → {input, output, cost_usd, budget, pct_used}
GET /api/tokens/history    → [{date, input, output, cost_usd}] last 7 days
GET /api/tokens/session    → tokens for current session (pass session_id)
```

---

## STEP 5: STREAMING CHAT (SSE)

### 5.1 New endpoint
Add `backend/routers/chat.py`:
```python
from fastapi.responses import StreamingResponse
import json

@router.post("/chat/stream")
async def chat_stream(payload: ChatIn, db=Depends(get_db), user=Depends(get_current_user)):
    async def generate():
        client = JarvisClaude(db, user.id)
        async for chunk in client.stream(payload.message, payload.tier, payload.personality):
            yield f"data: {json.dumps(chunk)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(generate(), media_type="text/event-stream",
                             headers={"X-Accel-Buffering": "no"})
```

Add `stream()` method to `JarvisClaude` that yields `{"type": "token", "text": "..."}` chunks, then a final `{"type": "done", "usage": {...}}` chunk. Use `client.messages.stream()` async context manager.

### 5.2 Frontend
Replace `fetch("/api/chat")` with EventSource or `fetch + ReadableStream`. Show tokens as they arrive in the chat bubble. Add a cancel button that aborts the stream. Keep the old `/api/chat` endpoint for fallback.

---

## STEP 6: MULTIMODAL INPUT

### 6.1 File upload endpoint
```python
POST /api/files/upload
- Accept: multipart/form-data
- Fields: file (binary), type hint optional
- Returns: {file_id, filename, file_type, preview_url}
- Max size: 20MB
- Supported: .jpg .jpeg .png .gif .webp .pdf .txt .csv .md .mp4 .mov
```

Processing per type:
- **Images**: Store in S3, return S3 URL for Claude vision
- **PDFs**: Extract text with `pypdf2`, store extracted text in KnowledgeChunk
- **CSV**: Parse with pandas, convert to markdown table string for Claude
- **Text/Markdown**: Store as-is
- **Video**: Extract 5 key frames with `cv2` (opencv-python-headless), send as images array to Claude

### 6.2 Chat with attachments
Extend `ChatIn`:
```python
class ChatIn(BaseModel):
    message: str = Field(..., max_length=2000)
    tier: str = "intelligent"           # eco/intelligent/scientist
    personality: str = "caveman"
    file_ids: list[int] = []            # IDs from /api/files/upload
```

In `JarvisClaude.respond()`, if `file_ids` present, build multimodal message content array:
```python
content = []
for fid in file_ids:
    fu = db.query(FileUpload).get(fid)
    if fu.file_type == "image":
        content.append({"type": "image", "source": {"type": "url", "url": fu.s3_url}})
    else:
        content.append({"type": "text", "text": fu.extracted_text})
content.append({"type": "text", "text": user_message})
```

### 6.3 Frontend upload UI
Add a paperclip icon button in DraggableChat. On click: opens file picker. Shows preview thumbnail in chat bubble before sending. Drag-and-drop onto chat window. Show upload progress bar. After upload, file appears as attachment chip in message input.

---

## STEP 7: CHAT PERSONALITY MODES + TOKEN EFFICIENCY

### 7.1 Personality mode system prompts
In `backend/ai/persona.py`, add personality injections:

```python
PERSONALITY_INJECTIONS = {
    "caveman": """RESPONSE STYLE — MANDATORY: Drop all articles (a/an/the). Drop filler words (just/really/basically/actually). Drop pleasantries. Use fragments. Short synonyms. Pattern: [thing] [action] [reason]. This saves tokens. Still technically precise.""",

    "expert": """RESPONSE STYLE: Structured, thorough analysis. Use headers for complex answers. Cite sources when possible. Explain reasoning. Suitable for technical deep-dives.""",

    "creative": """RESPONSE STYLE: Lateral thinking mode. Explore multiple angles. Challenge assumptions. Brainstorm options before converging. Use bullet lists for options.""",

    "executive": """RESPONSE STYLE: Decision-focused. Lead with recommendation. Use bullet points. End with clear next action. No padding. Optimized for time-poor executives.""",

    "devils_advocate": """RESPONSE STYLE: Challenge the user's assumptions. Point out risks. Play devil's advocate. Steelman counterarguments before agreeing.""",

    "coach": """RESPONSE STYLE: Socratic, question-based coaching. Ask clarifying questions. Help user think through problems rather than giving answers directly. Encouraging.""",
}
```

Inject chosen personality into system prompt:
```python
system_text = SYSTEM_PROMPT + "\n\n" + PERSONALITY_INJECTIONS.get(personality, PERSONALITY_INJECTIONS["caveman"])
```

Default personality: **caveman** — every user starts on caveman mode to protect tokens. User can change.

### 7.2 Quick-action chips
Add `GET /api/chat/quick-actions` returning:
```json
[
  {"id": "day_plan", "label": "What's my day?", "prompt": "Give me a complete briefing for today: meetings, priority emails, and top 3 tasks I should focus on."},
  {"id": "priority_emails", "label": "Priority emails", "prompt": "What are my most important emails right now that need action?"},
  {"id": "draft_replies", "label": "Draft top replies", "prompt": "Draft replies to my top 3 priority emails. Show me each draft for approval."},
  {"id": "blockers", "label": "What's blocking me?", "prompt": "Look at my tasks and tell me what's overdue or blocked and what I should do about it."},
  {"id": "week_summary", "label": "Week summary", "prompt": "Summarize what happened this week: emails, tasks completed, meetings, Shopify performance."},
  {"id": "meeting_prep", "label": "Next meeting prep", "prompt": "Brief me for my next meeting. Pull attendee context, related emails, and any relevant tasks."},
  {"id": "shopify_today", "label": "Shopify today", "prompt": "What's my Shopify revenue today vs yesterday? Top selling product? Any orders needing attention?"},
  {"id": "customer_issues", "label": "Customer issues", "prompt": "What are the top customer support issues this week? Any spikes or patterns I should know about?"},
  {"id": "decide_today", "label": "What to decide?", "prompt": "What things need my decision today? PRs, orders, tickets, anything waiting for me to act."},
  {"id": "delegate", "label": "What to delegate?", "prompt": "Look at my task list. What can be delegated? Draft delegation messages for the top 3 candidates."}
]
```

---

## STEP 8: USER PROFILE + RAG KNOWLEDGE BASE

### 8.1 User context endpoints
```python
GET  /api/context         → returns UserContext for current user
PUT  /api/context         → update all fields
```

In `JarvisClaude`, inject context into system prompt:
```python
ctx = db.query(UserContext).filter_by(user_id=self.user_id).first()
if ctx:
    context_block = f"""
USER CONTEXT — USE THIS TO PERSONALIZE ALL RESPONSES:
About: {ctx.about_me}
Communication style: {ctx.communication_style}
Priorities: {ctx.priorities}
Team: {json.dumps(ctx.team_members)}
Business context: {ctx.business_context}
"""
    system_text += context_block
```

### 8.2 RAG knowledge base
Install: `pgvector`, `anthropic` (for embeddings via Voyage, or use `sentence-transformers` locally).

For embeddings, use Anthropic's embedding API or OpenAI-compatible endpoint. Create `backend/ai/embedder.py`:
```python
async def embed(text: str, api_key: str) -> list[float]:
    # Use voyage-3-lite via anthropic or text-embedding-3-small
    # Returns 1536-dim vector
```

Create `backend/ai/knowledge.py`:
```python
async def search_knowledge(query: str, user_id: int, db, limit=5) -> list[str]:
    query_vec = await embed(query)
    results = db.execute(
        "SELECT content FROM knowledge_chunks WHERE user_id = :uid ORDER BY embedding <=> :vec LIMIT :n",
        {"uid": user_id, "vec": query_vec, "n": limit}
    ).fetchall()
    return [r[0] for r in results]
```

In `JarvisClaude.respond()`, before building messages, search knowledge:
```python
relevant = await search_knowledge(user_message, self.user_id, self.db)
if relevant:
    system_text += "\n\nRELEVANT KNOWLEDGE FROM USER'S DATA:\n" + "\n---\n".join(relevant)
```

### 8.3 Celery ingestion jobs
```python
@celery_app.task
def ingest_emails(user_id: int):
    # Fetch recent emails, chunk by email, embed, upsert into knowledge_chunks

@celery_app.task
def ingest_tasks(user_id: int):
    # Fetch Linear/Jira/Notion tasks, embed, upsert

@celery_app.task
def ingest_shopify(user_id: int):
    # Fetch recent orders, products, embed summaries

@celery_app.task
def ingest_file(file_upload_id: int):
    # Process uploaded file, chunk, embed, store
```

Celery beat schedule: run `ingest_emails` + `ingest_tasks` every 30 minutes per active user.

Add endpoint: `GET /api/knowledge/status` → `{chunks: N, last_updated: "...", sources: {email: N, tasks: N, files: N}}` so user can see what JARVIS knows.

---

## STEP 9: SHOPIFY INTEGRATION

### 9.1 OAuth flow
Add to `backend/connectors/shopify.py`:
- OAuth 2.0 with scopes: `read_orders,read_products,read_inventory,write_orders,write_products,read_customers,read_analytics`
- Shop domain entered by user in Integrations modal
- Token saved encrypted to `ShopifyConfig` table
- Connector extends `base.Connector`

Add to `PROVIDERS` list in `auth.py`: `("shopify", "Shopify")`

Shopify OAuth is different (shop-specific):
```python
# Step 1: user enters shop domain in UI
# Step 2: redirect to https://{shop}.myshopify.com/admin/oauth/authorize
# Step 3: Shopify redirects back with code
# Step 4: exchange for permanent access token (no refresh needed)
```

### 9.2 Shopify connector capabilities
```python
class ShopifyConnector(Connector):
    provider = "shopify"

    # READ
    async def fetch(self, **_):
        return await self.get_dashboard_summary()

    async def get_orders(self, status="any", limit=50, since_days=7) -> list
    async def get_products(self, limit=50) -> list
    async def get_inventory_levels(self) -> list
    async def get_customers(self, limit=50) -> list
    async def get_analytics(self, days=7) -> dict  # revenue, orders, avg_order_value
    async def get_revenue_today(self) -> dict
    async def get_low_stock_products(self, threshold=5) -> list
    async def get_open_refunds(self) -> list
    async def get_customer_order_history(self, customer_id: str) -> list

    # WRITE
    async def create_order(self, line_items: list, customer: dict) -> dict
    async def create_discount_code(self, code: str, value: float, type: str) -> dict
    async def update_inventory(self, variant_id: str, quantity: int) -> dict
    async def cancel_order(self, order_id: str, reason: str) -> dict
```

### 9.3 Shopify AI tools
Add to `tools.py` TOOL_SCHEMAS:
```
get_shopify_revenue       — params: days (default 7)
get_shopify_orders        — params: status, limit
get_shopify_products      — top products by sales
get_low_stock_products    — products below threshold
get_customer_history      — params: customer_id or email
get_shopify_refunds       — open refunds
create_shopify_discount   — params: code, percent_off, expires_days
create_shopify_order      — params: items, customer_email
draft_customer_reply      — given order_id + issue, draft support reply
```

### 9.4 Shopify pre-built prompt suggestions
Add to `/api/chat/quick-actions` when Shopify connected:
- "What's my revenue today vs last week?"
- "Which products are low on stock?"
- "Show me all unfulfilled orders"
- "Draft a win-back email for customers who haven't ordered in 60 days"
- "How many refunds this month and what's the reason breakdown?"
- "Create a 15% discount code for VIP customers expiring in 7 days"
- "Who are my top 10 customers by lifetime value?"
- "What's my average order value trending?"

---

## STEP 10: FRESHDESK INTEGRATION

### 10.1 Config (API key, no OAuth)
- User enters Freshdesk subdomain + API key in Integrations modal
- Stored encrypted in `FreshdeskConfig` table
- Add `GET /api/freshdesk/status` to verify connection

### 10.2 Freshdesk connector
```python
class FreshdeskConnector:
    BASE = "https://{subdomain}.freshdesk.com/api/v2"

    async def get_tickets(self, status="open", page=1) -> list
    async def get_ticket(self, ticket_id: int) -> dict
    async def get_ticket_conversations(self, ticket_id: int) -> list
    async def get_contacts(self, email: str = None) -> list
    async def get_reports_summary(self, days=7) -> dict
    async def reply_to_ticket(self, ticket_id: int, body: str) -> dict
    async def get_top_issues(self, days=7) -> list  # Claude-analyzed clusters
    async def get_overdue_tickets(self) -> list
```

### 10.3 Customer crisis radar (Celery task)
```python
@celery_app.task
def check_ticket_spikes(user_id: int):
    # Fetch tickets from last 2 hours
    # Use Claude to cluster by topic
    # If any cluster has 5+ tickets, create a Decision record + push notification
    # "Boss, 7 customers reporting checkout errors in last 2 hours"
```
Schedule: every 30 minutes.

### 10.4 Freshdesk AI tools
```
get_freshdesk_tickets     — params: status, limit
get_top_customer_issues   — AI-clustered issues summary
get_ticket_detail         — params: ticket_id
reply_freshdesk_ticket    — params: ticket_id, draft body
get_support_metrics       — avg resolution time, CSAT, volume
```

### 10.5 Cross-integration: Shopify + Freshdesk
When JARVIS looks up a customer complaint, if both Shopify and Freshdesk connected:
- Pull customer's Freshdesk ticket
- Pull their Shopify order history
- Combine: "Customer Sarah had 3 tickets. Last order was $245 3 days ago, status: processing. Draft a priority reply offering express shipping upgrade."

---

## STEP 11: DASHBOARD — USE-CASE PROMPTS PER PANEL

Each dashboard panel gets a "Suggestions" button that shows pre-built prompts relevant to that panel. These are polished, ready-to-use prompts for non-technical founders.

### Email panel suggestions:
```
"Summarize all unread emails in one paragraph"
"Which emails need a reply today? List them with who sent it and why it matters."
"Draft replies to my top 3 priority emails and show each for my approval"
"Flag any emails I've been ignoring too long"
"Is there anything in my inbox that could be a legal or financial risk?"
```

### Calendar panel suggestions:
```
"Brief me for my next meeting — who's attending, what's the context, what should I know?"
"What's eating most of my time this week? Any patterns?"
"I need 2 hours of focused work today — when's the best slot?"
"What meetings this week could be an email instead?"
"Any conflicts or double bookings I should know about?"
```

### Tasks panel suggestions:
```
"What's my single most important task today and why?"
"Which tasks are overdue? What should I do about each?"
"Break down [task name] into smaller steps I can action today"
"What on my task list can I delegate? Draft the delegation messages."
"What tasks haven't moved in a week? Should I drop them?"
```

### Shopify panel suggestions:
```
"How is my store performing this week vs last week?"
"What are my top 3 selling products and what's driving their success?"
"Which products should I restock urgently?"
"I want to run a promotion. What products and discount would maximize revenue?"
"Show me customers who spent over $500 but haven't ordered in 30 days"
```

### Freshdesk panel suggestions:
```
"What are my customers most frustrated about this week?"
"Are there any tickets that have been waiting too long? Who's affected?"
"Draft a reply to my most urgent open ticket"
"What's my team's support response time looking like?"
"Are there any recurring complaints I should fix at the product level?"
```

### General daily use-case prompts (shown on dashboard home):
```
"Good morning — give me my complete daily brief"
"What are the 3 most important things I need to do today?"
"Is anything on fire right now that needs my immediate attention?"
"What decisions am I avoiding that I should make today?"
"End of day review — what got done, what's still open, what's tomorrow's priority?"
```

---

## STEP 12: TOKEN MONITOR UI

### 12.1 Backend endpoint
```python
GET /api/tokens/dashboard
Returns:
{
  "today": {"input": 12400, "output": 3200, "cost_usd": 0.082, "budget": 100000, "pct_used": 15.6},
  "session": {"input": 2100, "output": 540, "cost_usd": 0.014},
  "history": [{"date": "2026-05-19", "cost_usd": 0.21}, ...],  // 7 days
  "model": "intelligent",
  "tier_info": {"name": "Intelligent", "model": "claude-sonnet-4-6", "cost_per_1k_input": 0.003}
}
```

### 12.2 Frontend TokenMonitor component
Position: slide-out panel on right side of chat, toggled by a small "$" or token icon button.

Contents:
- **Tier selector**: Three pills — ECO / INTELLIGENT / SCIENTIST with model name and cost shown below each
  - Eco: "Haiku 4.5 · $0.00025/1k" 
  - Intelligent: "Sonnet 4.6 · $0.003/1k"
  - Scientist: "Opus 4.7 · $0.015/1k"
- **Session usage**: "This session: 2,640 tokens · $0.014"
- **Today's usage**: Progress bar (green → yellow → red), "15,600 / 100,000 tokens today"
- **7-day sparkline**: Mini chart of daily spend
- **Cost estimate**: "At this pace: ~$2.50/month"
- **Budget settings**: Input to set daily token budget + alert threshold
- Color codes: green < 50%, yellow 50-80%, red > 80%

---

## STEP 13: SETTINGS PAGE (FULL)

New route: `/settings` — tabs UI, non-technical friendly language.

### Tab 1: AI & Intelligence
- Tier selector (Eco/Intelligent/Scientist) — visual cards with description
- Default personality mode — dropdown (Caveman/Expert/Creative/Executive/etc)
- Default response length — Brief / Detailed / Deep
- Daily token budget — slider or number input
- Budget alert at — percentage slider

### Tab 2: API Keys
- Anthropic API key — input field, masked, with "Test connection" button
  - Show: "Connected ✓ — claude-sonnet-4-6 available" or error
- ElevenLabs API key — same pattern
- Note: "We encrypt your keys. We never use them without your request."

### Tab 3: About Me (context)
- "Who are you?" — text area: name, role, company, industry
- "What matters to you?" — text area: top priorities, goals
- "How do you like to communicate?" — text area: formal/casual, brief/detailed preferences
- "Your team" — add team members: name + role + how you work with them
- "Business context" — free text: key info JARVIS should always know
- Save button → PUT /api/context

### Tab 4: Integrations
- Existing integrations modal content moved here
- Show status: Connected / Disconnected / Token expired (with Reconnect button)
- Add Shopify: "Enter your store URL (e.g. mystore.myshopify.com)"
- Add Freshdesk: "Enter subdomain + API key"

### Tab 5: GitHub
- Repo URL input
- Personal Access Token input (masked)
- Default branch (main)
- Test connection button
- Used for: pushing reports and briefs from JARVIS to your repo

### Tab 6: Account
- Change password
- Change email
- Delete account (requires typing "DELETE" + confirmation)
- Export my data (generates JSON of all user data)

---

## STEP 14: FOUNDER INTELLIGENCE FEATURES

### 14.1 Decision Inbox
New component: `DecisionInbox` — shows as a badge on the header and a full-page view.

Backend: `GET /api/decisions` — returns pending decisions sorted by urgency.

Sources that create Decision records:
- GitHub PRs awaiting your review (from existing GitHub connector)
- Shopify orders above $1000 with flags
- Freshdesk tickets marked urgent or waiting 24h+
- Linear/Jira issues marked "blocked" or "waiting on you"

Each decision card shows:
- Source + title
- Context summary (AI-generated, 2 sentences)
- AI recommendation
- Action buttons: ✓ Approve / ✗ Reject / → Delegate / 💤 Snooze

When Delegate clicked: dropdown of team members (from UserContext.team_members), JARVIS drafts delegation message, user can edit + send via Slack/email.

Celery task: `build_decision_inbox(user_id)` runs every 15 minutes, syncs from all sources.

### 14.2 Smart Meeting Prep
Celery task: `prepare_meeting_brief(user_id, event_id)` — scheduled 20 minutes before each calendar event.

Brief generation:
1. Parse attendee emails from calendar event
2. Search knowledge base for those emails
3. Pull last 5 emails exchanged with each attendee
4. Pull any Shopify orders linked to their domain
5. Pull any Freshdesk tickets from their email
6. Claude synthesizes into 3-5 bullet brief

Push as in-app notification: "Meeting in 15: [title]. Tap to see your brief."
Also visible as button on CalendarPanel event card: "📋 Brief me"

### 14.3 Proactive Task Creation from Emails
Add Celery task: `analyze_email_commitments(user_id)` — after each email sync:

For each new email, prompt Claude:
```
Does this email contain a commitment, deadline, or action required from the user?
If yes: return {title, due_date, source_email_id}
If no: return null
```
If yes: show suggestion chip in EmailPanel: "Create task: [title] due [date]?"
One-click creates Linear issue with pre-filled content.

### 14.4 Weekly Business Brief
Celery beat: every Monday at 8am UTC, `send_weekly_brief(user_id)`.

Brief sections:
1. Revenue: Shopify this week vs last week, trend
2. Customer health: Freshdesk volume, avg response time, top complaint
3. Work: Linear/Jira tasks completed vs added, blockers
4. Communications: emails received/sent, longest unanswered thread
5. Priorities for this week: AI-generated top 3 recommendations

Delivered as:
- In-app notification with full content
- Email via user's connected Gmail (subject: "Your JARVIS Weekly Brief — May 20")

### 14.5 GitHub Integration (Push from JARVIS)
Add to `tools.py`:
```python
{
  "name": "push_to_github",
  "description": "Save a document, report, or draft to the user's GitHub repository.",
  "input_schema": {
    "properties": {
      "filename": {"type": "string"},
      "content": {"type": "string"},
      "commit_message": {"type": "string"},
      "path": {"type": "string", "description": "folder path, e.g. reports/ or drafts/"}
    },
    "required": ["filename", "content"]
  }
}
```
Implementation uses GitHub API `PUT /repos/{owner}/{repo}/contents/{path}`. Token from `UserSettings.github_pat_encrypted`.

Add "Push to GitHub" button on every JARVIS response. One click → saves current response as `.md` file to configured repo.

---

## STEP 15: FRONTEND UPDATES SUMMARY

### 15.1 New components to create:
- `IntelligenceTierSelector` — 3-pill selector (Eco/Intelligent/Scientist) shown above chat input
- `PersonalityModeSelector` — pill row: Caveman/Expert/Creative/Executive/Devil's Advocate/Coach
- `QuickActionChips` — row of 10 chip buttons above chat input, scrollable horizontally
- `FileUploadZone` — paperclip button + drag-drop in chat, shows preview thumbnails
- `StreamingChatBubble` — shows tokens as they arrive, animated cursor, cancel button
- `TokenMonitor` — slide-out right panel, tier selector, usage stats, sparkline chart
- `ShopifyPanel` — dashboard panel: revenue today, orders, top product, alert badges
- `DecisionInboxPanel` — decision cards with approve/reject/delegate actions
- `SettingsPage` — 6-tab settings UI (full page, route /settings)
- `MeetingPrepBanner` — "Meeting in 15 min" alert with brief expandable
- `UseCasePromptDrawer` — per-panel suggestion prompts, shown on "?" button click
- `KnowledgeStatusWidget` — shows how much JARVIS knows (chunks count, last updated)

### 15.2 Existing components to update:
- `DraggableChat`: add tier selector + personality pills + quick action chips + file upload + streaming
- `IntegrationsModal`: add Shopify + Freshdesk sections
- `EmailPanel`: add "Create task?" suggestion chips + "Suggestions" button
- `CalendarPanel`: add "Brief me" button per event + pre-meeting alert banner
- `TaskPanel`: add suggestion prompts + delegation quick action
- `ProjectPanel`: add GitHub push button + decision badges
- `ProfileDropdown`: add Settings link + token usage summary
- `App.tsx`: add `/settings` route, add TokenMonitor component

### 15.3 Store updates (jarvisStore.ts)
Add to Zustand store:
- `intelligenceTier: "eco" | "intelligent" | "scientist"`
- `personalityMode: string`
- `tokenUsage: {today: {...}, session: {...}}`
- `decisions: Decision[]`
- `uploadedFiles: FileUpload[]`
- `shopifyConnected: boolean`
- `freshdeskConnected: boolean`
- `settings: UserSettings`
- `userContext: UserContext`

---

## STEP 16: THINGS TO DELETE

Remove these from the codebase:

1. `backend/migrations.py` — replace with Alembic entirely
2. Hardcoded `"jarvis-jwt-2026"` default in `users.py`
3. Hardcoded `"dev-secret"` default in `main.py`
4. `?token=` query param auth in `get_current_user()`
5. `traceback.print_exc()` in `chat.py`
6. `detail=str(e)` in `chat.py`
7. `claude-sonnet-4-5` hardcoded model (replaced by tier system)
8. `claude-haiku-4-5` hardcoded compression model — update to `claude-haiku-4-5-20251001`
9. Any `print()` debug statements in production code

---

## STEP 17: THINGS TO AMEND

| File | Location | Current | Change to |
|------|----------|---------|-----------|
| `main.py` | CORS origins | hardcoded localhost list | `ALLOWED_ORIGINS` env var |
| `main.py` | slowapi | `get_remote_address` | per-user key if authenticated, else IP |
| `users.py` | JWT expiry | 30 days | 7 days + add `POST /api/users/refresh` endpoint |
| `ai/memory.py` | COMPRESSION_MODEL | `claude-haiku-4-5` | `claude-haiku-4-5-20251001` |
| `docker-compose.yml` | backend VITE_API_BASE | `http://localhost:8000` | `${API_BASE_URL}` from env |
| `ai/tools.py` | create_task | inline httpx calls | use LinearConnector properly |
| All connectors | token refresh | none | add auto-refresh logic when token expires (401 → try refresh → if fails, mark expired in DB) |
| `feed.py` | no caching | hits 11 APIs every request | Redis cache per user, 2-minute TTL |

---

## STEP 18: NEW BACKEND DEPENDENCIES (add to requirements.txt)

```
pgvector>=0.2.5
alembic>=1.13.0
psycopg2-binary>=2.9.9
redis>=5.0.0
celery[redis]>=5.3.6
cryptography>=42.0.0
boto3>=1.34.0
pypdf2>=3.0.0
opencv-python-headless>=4.9.0
pandas>=2.2.0
sentence-transformers>=3.0.0
httpx[http2]>=0.27.0
python-jose[cryptography]>=3.3.0
```

---

## STEP 19: NEW FRONTEND DEPENDENCIES (add to package.json)

```json
"recharts": "^2.12.0",
"@radix-ui/react-tabs": "^1.0.4",
"@radix-ui/react-dialog": "^1.0.5",
"@radix-ui/react-select": "^2.0.0",
"react-dropzone": "^14.2.3",
"eventsource-parser": "^1.1.2",
"date-fns": "^3.6.0"
```

---

## STEP 20: ENVIRONMENT VARIABLES (full .env.example)

```bash
# Required — app crashes without these
JWT_SECRET=change-me-min-32-chars
SESSION_SECRET=change-me-min-32-chars
TOKEN_ENCRYPTION_KEY=change-me-must-be-32-url-safe-base64-chars

# Database
DATABASE_URL=postgresql://jarvis:password@postgres:5432/jarvis
REDIS_URL=redis://redis:6379/0
POSTGRES_PASSWORD=change-me

# Storage
S3_BUCKET=jarvis-uploads
S3_ENDPOINT_URL=https://your-r2-endpoint.r2.cloudflarestorage.com
S3_ACCESS_KEY=
S3_SECRET_KEY=

# CORS
ALLOWED_ORIGINS=http://localhost,https://yourdomain.com
FRONTEND_URL=https://yourdomain.com

# OAuth providers (platform-level, for users who haven't added BYOAK)
ANTHROPIC_API_KEY=          # fallback only
ELEVENLABS_API_KEY=         # fallback only
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
MS_CLIENT_ID=
MS_CLIENT_SECRET=
SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
SHOPIFY_CLIENT_ID=
SHOPIFY_CLIENT_SECRET=
LINEAR_API_KEY=
JIRA_TOKEN=
NOTION_TOKEN=
WHATSAPP_TOKEN=
```

---

## USER TODOs — THINGS ONLY YOU CAN DO

These cannot be automated. Do them in parallel while building.

### Week 1 (start immediately — long lead times):
- [ ] **Submit Google OAuth verification** — go to console.cloud.google.com → APIs & Services → OAuth consent screen → Submit for verification. Requires privacy policy URL. Takes 4-12 weeks. Gmail + Google Calendar blocked for real users until approved.
- [ ] **Submit Microsoft Azure app verification** — portal.azure.com → App registrations → your app → Branding & properties. Same purpose. Outlook + Teams blocked until approved.
- [ ] **Write privacy policy** — use iubenda.com or termly.io ($0-$10). Must explicitly state: you use email content for AI processing at user's explicit request, you don't train on user data, users can delete all data. Deploy at yourdomain.com/privacy BEFORE submitting Google verification.
- [ ] **Buy domain** — namecheap.com or cloudflare.com. Pick something clean.
- [ ] **Set up Cloudflare** — free CDN, HTTPS, DDoS protection.

### Week 2:
- [ ] **Shopify Partner account** — partners.shopify.com → Create app. Get SHOPIFY_CLIENT_ID and SHOPIFY_CLIENT_SECRET.
- [ ] **Freshdesk trial** — freshdesk.com → Free trial → Get your subdomain + API key. Test the connector.
- [ ] **Stripe account** — stripe.com → Create account → Get API keys for billing (add later).
- [ ] **Cloudflare R2** — free S3-compatible storage for file uploads (10GB free). Get endpoint + keys.

### Ongoing:
- [ ] **Push ALL code to GitHub** — keep main branch updated. `git push origin main` after every feature.
- [ ] **Test as a real user** — create a test account, add your real Gmail/Shopify/Freshdesk, use it daily. Fix what feels broken.

---

## TESTING CHECKLIST — VERIFY EACH STEP

After each phase, manually test:

**Phase 0 (Security):**
- [ ] App crashes with helpful message if JWT_SECRET not in env
- [ ] ?token= param rejected with 401
- [ ] OAuth token in DB is encrypted (check DB directly — should not be readable)
- [ ] /api/chat returns generic 500, not stack trace, on error
- [ ] /api/users/register rate-limited after 5 attempts in 1 minute

**Phase 1 (Infrastructure):**
- [ ] PostgreSQL accepting connections, migrations ran
- [ ] Redis accepting connections
- [ ] Celery worker starts without errors
- [ ] File upload to S3/R2 works, returns URL

**Phase 3 (Intelligence tiers):**
- [ ] Eco tier uses Haiku, faster + cheaper
- [ ] Scientist tier uses Opus with thinking (tokens visible in usage log)
- [ ] Token usage recorded in DB after every message
- [ ] Prompt cache hit visible in usage (cache_read_input_tokens > 0 on repeated prompts)

**Phase 4 (BYOAK):**
- [ ] New user with no API key sees "Add your Anthropic key" gate
- [ ] After adding key, all AI features work
- [ ] Wrong key shows "Invalid API key" not 500 error

**Phase 5 (Streaming):**
- [ ] Tokens appear word-by-word in chat bubble
- [ ] Cancel button stops stream and shows partial response
- [ ] Token usage shown at end of stream

**Phase 9 (Shopify):**
- [ ] OAuth connect flow works for a test Shopify dev store
- [ ] "What's my revenue today?" returns real data
- [ ] "Create a 10% discount code" creates it in Shopify and shows confirmation

---

## IMPLEMENTATION ORDER (SUGGESTED)

1. Step 0 (security fixes) — no new features, just fixes
2. Step 1 (infrastructure migration) — Postgres + Redis + Celery + S3
3. Step 2 (new DB models) + Alembic migrations
4. Step 3 (intelligence tiers) + Step 4 (BYOAK) — these are tightly coupled
5. Step 13 (settings page) — needed to configure BYOAK + tier
6. Step 12 (token monitor UI) — depends on token usage tracking from Step 3
7. Step 5 (streaming chat) — major UX improvement
8. Step 6 (multimodal input) — file upload
9. Step 7 (personality modes + quick actions) — chat UX
10. Step 8 (user profile + RAG) — knowledge base
11. Step 9 (Shopify) + Step 10 (Freshdesk)
12. Step 11 (dashboard prompts)
13. Step 14 (founder intelligence) — decision inbox, meeting prep, weekly brief
14. Step 15 (frontend updates) — polish + new components
15. Step 16+17 (cleanup)

---

## GENERAL RULES FOR THIS CODEBASE

- UI language: non-technical. No "API key", say "Your Anthropic account key". No "OAuth", say "Connect your account". No "token", say "credit" or "usage".
- Every new endpoint must have `Depends(get_current_user)` — no unprotected endpoints except /register, /login, /health.
- Every new DB write must use the existing session pattern (`db: Session = Depends(get_db)`).
- Follow existing file structure. New connectors go in `connectors/`. New AI tools go in `ai/tools.py`. New routers go in `routers/` and must be registered in `main.py`.
- Keep the 3D HUD aesthetic on all new UI: dark background `#0a0e1a`, cyan `#00d4ff`, blue `#0066ff`, white text. No light themes, no white backgrounds on new panels.
- New frontend components: use existing Tailwind + Framer Motion patterns from other panels. Match the glass-morphism card style.
- All new secrets go in `.env.example` with placeholder values and a comment explaining what it is and where to get it.
- After every major step: `git add -A && git commit -m "feat: [description]" && git push origin main`.

---

## STEP 21: PROVIDER-AGNOSTIC AI ABSTRACTION LAYER

### CRITICAL ARCHITECTURE RULE
**Never import `anthropic` directly in business logic.** All AI calls go through the abstraction layer. This means switching from Anthropic to OpenAI requires changing ONE file, not hunting through 20 files.

### 21.1 Unified AI interface
Create `backend/ai/providers/__init__.py` and the following files:

**`backend/ai/providers/base.py`**:
```python
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, Any

@dataclass
class AIMessage:
    role: str       # "user" | "assistant" | "system"
    content: Any    # str or list (multimodal)

@dataclass
class AITool:
    name: str
    description: str
    input_schema: dict

@dataclass
class AIResponse:
    text: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int = 0
    thinking: str | None = None     # extended thinking output
    tool_calls: list = None

@dataclass
class AIChunk:
    type: str   # "token" | "tool_call" | "done" | "thinking"
    text: str = ""
    tool_name: str = ""
    tool_input: dict = None
    usage: dict = None

class AIProvider(ABC):
    name: str = ""

    @abstractmethod
    async def complete(
        self,
        messages: list[AIMessage],
        system: str,
        tools: list[AITool] | None,
        model: str,
        max_tokens: int,
        thinking_budget: int | None = None,
    ) -> AIResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[AIMessage],
        system: str,
        tools: list[AITool] | None,
        model: str,
        max_tokens: int,
        thinking_budget: int | None = None,
    ) -> AsyncIterator[AIChunk]: ...
```

**`backend/ai/providers/anthropic_provider.py`**:
```python
import anthropic
from .base import AIProvider, AIMessage, AITool, AIResponse, AIChunk

class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str):
        self.client = anthropic.AsyncAnthropic(api_key=api_key)

    def _build_tools(self, tools):
        return [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools] if tools else []

    async def complete(self, messages, system, tools, model, max_tokens, thinking_budget=None) -> AIResponse:
        kwargs = dict(model=model, max_tokens=max_tokens, messages=self._msgs(messages),
                      system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                      tools=self._build_tools(tools))
        if thinking_budget:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
            kwargs["betas"] = ["interleaved-thinking-2025-05-14"]
        resp = await self.client.messages.create(**kwargs)
        text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        tool_calls = [{"name": b.name, "input": b.input, "id": b.id}
                      for b in resp.content if b.type == "tool_use"]
        return AIResponse(text=text, input_tokens=resp.usage.input_tokens,
                          output_tokens=resp.usage.output_tokens,
                          cache_read_tokens=getattr(resp.usage, "cache_read_input_tokens", 0),
                          tool_calls=tool_calls)

    def _msgs(self, messages):
        return [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]

    async def stream(self, messages, system, tools, model, max_tokens, thinking_budget=None):
        # Yields AIChunk objects
        kwargs = dict(model=model, max_tokens=max_tokens, messages=self._msgs(messages),
                      system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
                      tools=self._build_tools(tools))
        if thinking_budget:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": thinking_budget}
        async with self.client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield AIChunk(type="token", text=text)
            final = await s.get_final_message()
            yield AIChunk(type="done", usage={
                "input": final.usage.input_tokens,
                "output": final.usage.output_tokens,
                "cache_read": getattr(final.usage, "cache_read_input_tokens", 0),
            })
```

**`backend/ai/providers/openai_provider.py`**:
```python
# Works for OpenAI, Groq (OpenAI-compatible), and any OpenAI-compatible endpoint
from openai import AsyncOpenAI
from .base import AIProvider, AIMessage, AITool, AIResponse, AIChunk
import json

class OpenAICompatibleProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, base_url: str = None, provider_name: str = "openai"):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.name = provider_name

    def _build_tools(self, tools):
        return [{"type": "function", "function": {
            "name": t.name, "description": t.description, "parameters": t.input_schema
        }} for t in tools] if tools else []

    def _msgs(self, messages, system):
        result = [{"role": "system", "content": system}]
        for m in messages:
            result.append({"role": m.role, "content": m.content if isinstance(m.content, str)
                           else self._flatten_content(m.content)})
        return result

    async def complete(self, messages, system, tools, model, max_tokens, thinking_budget=None) -> AIResponse:
        resp = await self.client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=self._msgs(messages, system),
            tools=self._build_tools(tools) or None,
        )
        msg = resp.choices[0].message
        tool_calls = []
        if msg.tool_calls:
            tool_calls = [{"name": tc.function.name,
                           "input": json.loads(tc.function.arguments), "id": tc.id}
                          for tc in msg.tool_calls]
        return AIResponse(text=msg.content or "", input_tokens=resp.usage.prompt_tokens,
                          output_tokens=resp.usage.completion_tokens, tool_calls=tool_calls)

    async def stream(self, messages, system, tools, model, max_tokens, thinking_budget=None):
        stream = await self.client.chat.completions.create(
            model=model, max_tokens=max_tokens, messages=self._msgs(messages, system),
            tools=self._build_tools(tools) or None, stream=True,
        )
        total_in = total_out = 0
        async for chunk in stream:
            delta = chunk.choices[0].delta if chunk.choices else None
            if delta and delta.content:
                yield AIChunk(type="token", text=delta.content)
            if chunk.usage:
                total_in = chunk.usage.prompt_tokens
                total_out = chunk.usage.completion_tokens
        yield AIChunk(type="done", usage={"input": total_in, "output": total_out, "cache_read": 0})

    def _flatten_content(self, content):
        # Convert multimodal content list to OpenAI format
        result = []
        for item in content:
            if item.get("type") == "text":
                result.append({"type": "text", "text": item["text"]})
            elif item.get("type") == "image":
                result.append({"type": "image_url", "image_url": {"url": item["source"]["url"]}})
        return result
```

**`backend/ai/providers/google_provider.py`**:
```python
import google.generativeai as genai
from .base import AIProvider, AIResponse, AIChunk
# Implement Gemini via google-generativeai SDK
# Same interface as above
```

**`backend/ai/providers/factory.py`**:
```python
from .base import AIProvider
from .anthropic_provider import AnthropicProvider
from .openai_provider import OpenAICompatibleProvider

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
MISTRAL_BASE_URL = "https://api.mistral.ai/v1"

def get_provider(provider_name: str, api_key: str) -> AIProvider:
    match provider_name:
        case "anthropic": return AnthropicProvider(api_key)
        case "openai":    return OpenAICompatibleProvider(api_key)
        case "groq":      return OpenAICompatibleProvider(api_key, GROQ_BASE_URL, "groq")
        case "mistral":   return OpenAICompatibleProvider(api_key, MISTRAL_BASE_URL, "mistral")
        case _: raise ValueError(f"Unknown provider: {provider_name}")
```

### 21.2 Tier → model mapping per provider
```python
# backend/ai/tiers.py
TIER_MODELS = {
    "eco": {
        "anthropic": ("claude-haiku-4-5-20251001", 1024, 2048),
        "openai":    ("gpt-4o-mini", None, 4096),
        "groq":      ("llama-3.3-70b-versatile", None, 4096),
        "mistral":   ("mistral-small-latest", None, 4096),
        "google":    ("gemini-2.5-flash-lite", None, 4096),
    },
    "intelligent": {
        "anthropic": ("claude-sonnet-4-6", 4096, 4096),
        "openai":    ("gpt-4o", None, 4096),
        "groq":      ("llama-3.1-70b-versatile", None, 4096),
        "mistral":   ("mistral-large-latest", None, 4096),
        "google":    ("gemini-2.5-pro", None, 4096),
    },
    "scientist": {
        "anthropic": ("claude-opus-4-7", 10000, 8192),
        "openai":    ("o3", None, 8192),   # o3 has internal reasoning, no thinking param
        "groq":      ("llama-3.1-70b-versatile", None, 8192),  # Groq no 405B in prod yet
        "mistral":   ("mistral-large-latest", None, 8192),
        "google":    ("gemini-2.5-pro", None, 8192),
    },
}

# Cost per 1M tokens (input, output) — used for cost estimation display
TIER_COSTS = {
    "eco":         {"anthropic": (1.00, 5.00), "openai": (0.15, 0.60),
                    "groq": (0.59, 0.79), "mistral": (0.10, 0.30), "google": (0.10, 0.40)},
    "intelligent": {"anthropic": (3.00, 15.00), "openai": (2.50, 10.00),
                    "groq": (0.59, 0.79), "mistral": (2.00, 6.00), "google": (1.25, 10.00)},
    "scientist":   {"anthropic": (5.00, 25.00), "openai": (2.00, 8.00),
                    "groq": (0.59, 0.79), "mistral": (2.00, 6.00), "google": (2.50, 15.00)},
}
```

### 21.3 Update UserSettings model
Add to `UserSettings`:
```python
ai_provider = Column(String, default="anthropic")  # anthropic/openai/groq/mistral/google
anthropic_api_key_encrypted = Column(Text, nullable=True)
openai_api_key_encrypted = Column(Text, nullable=True)
groq_api_key_encrypted = Column(Text, nullable=True)
mistral_api_key_encrypted = Column(Text, nullable=True)
google_api_key_encrypted = Column(Text, nullable=True)
```

### 21.4 Update JarvisClaude to use abstraction
```python
# backend/ai/claude_client.py  (rename to jarvis_ai.py eventually)
from .providers.factory import get_provider
from .tiers import TIER_MODELS, TIER_COSTS
from crypto import decrypt

class JarvisAI:
    def __init__(self, db, user_id):
        self.db = db
        self.user_id = user_id
        settings = db.query(UserSettings).filter_by(user_id=user_id).first()
        provider_name = settings.ai_provider if settings else "anthropic"
        # Get encrypted key for chosen provider
        key_field = f"{provider_name}_api_key_encrypted"
        encrypted_key = getattr(settings, key_field, None) if settings else None
        api_key = decrypt(encrypted_key) if encrypted_key else os.getenv(f"{provider_name.upper()}_API_KEY", "")
        if not api_key:
            raise HTTPException(402, f"No {provider_name} API key. Add yours in Settings → AI Keys.")
        self.provider = get_provider(provider_name, api_key)
        self.provider_name = provider_name
        tier_name = settings.default_model if settings else "intelligent"
        model, thinking_budget, max_tokens = TIER_MODELS[tier_name][provider_name]
        self.model = model
        self.thinking_budget = thinking_budget
        self.max_tokens = max_tokens
        self.tier_costs = TIER_COSTS[tier_name][provider_name]
        self.memory = ConversationMemory(db, user_id)
```

### 21.5 Install new dependencies
```
openai>=1.40.0          # OpenAI + Groq + Mistral (OpenAI-compatible)
google-generativeai>=0.8.0
anthropic>=0.40.0
```

### 21.6 Frontend: Provider selector in Settings
In Settings → AI Keys tab, show 5 provider cards:
- Anthropic, OpenAI, Groq, Mistral, Google
- Each card: logo, name, "Recommended" badge (Anthropic), key input, Test button
- Dropdown: "Active provider" — whichever has a valid key
- Show cost comparison: "Groq is 20x cheaper for Eco tier"
- Non-technical copy: "Your AI brain. Enter the key from your account."

---

## STEP 22: PRICING PLANS (RESEARCHED)

### Competitive landscape
| Competitor | Price | What it does |
|---|---|---|
| Superhuman | $30/mo | Email AI only |
| Motion | $19/mo | Calendar + tasks AI |
| Reclaim.ai | $12/mo | Calendar only |
| Notion AI | $10/mo add-on | Notes AI |
| ChatGPT Plus | $20/mo | General AI |
| **Combined stack** | **$91/mo** | All the above |
| **JARVIS Pro** | **$49/mo** | Replaces all of them + adds more |

### Three plans

#### Plan 1: STARTER — $19/month (or $14/month annually, billed $168/year)
**Target**: Solo founder just starting, freelancer, consultant
**Positioning**: "Try JARVIS before going all-in"

Includes:
- 3 integrations (pick from: Gmail, Google Calendar, Linear, Notion, Slack, GitHub)
- 100 AI messages/day (BYOAK — their API bill)
- Eco + Intelligent tiers (Haiku or Sonnet-equivalent)
- Chat personality modes
- Quick-action chips
- Basic email priority scoring
- Token usage monitor
- 7-day conversation history

Excludes:
- No voice interaction
- No file upload
- No Shopify/Freshdesk
- No RAG knowledge base
- No morning brief
- No decision inbox
- No meeting prep
- No weekly brief

#### Plan 2: PRO — $49/month (or $39/month annually, billed $468/year)
**Target**: Active founder, e-commerce operator, busy executive
**Positioning**: "Your AI chief of staff"

Includes everything in Starter plus:
- All 15+ integrations (unlimited)
- Unlimited AI messages (BYOAK)
- All tiers including Scientist (Opus/o3/Gemini Pro equivalent)
- Voice interaction (ElevenLabs)
- File upload: images, PDFs, CSVs, video (5GB/month)
- RAG knowledge base (100k chunks, auto-ingested)
- Daily morning brief (7am automated)
- Shopify full integration (read + write)
- Freshdesk integration
- Decision inbox
- Smart meeting prep (auto-brief 15min before)
- Weekly business brief (email + in-app)
- Proactive task creation from emails
- GitHub push integration
- Customer crisis radar
- 90-day conversation history
- 1 user

#### Plan 3: TEAM — $39/user/month min 3 seats (or $29/user annually)
**Target**: Small team (3-20 people), startup with distributed team
**Positioning**: "JARVIS for your whole team"

Includes everything in Pro plus:
- Shared team knowledge base (everyone's context merged)
- Team member profiles (JARVIS knows who does what)
- Cross-team queries: "What is everyone working on this week?"
- Delegation workflow (delegate with context via Slack/email)
- Admin dashboard: usage per member, cost breakdown
- Shared prompt template library
- Team morning brief (one brief covering whole team)
- Priority support (email, 24h response)
- 3-50 seats
- Single billing for team

#### Enterprise — custom pricing (est. $200-500/user/month)
- Unlimited seats
- SSO / SAML
- Custom integrations (Salesforce, HubSpot, custom CRM)
- Data residency (EU, US, custom)
- Private deployment (your own cloud)
- Dedicated customer success manager
- SLA (99.9% uptime guarantee)
- Custom model fine-tuning

### Freemium strategy
- **14-day Pro trial** on signup (no credit card required)
- After trial: drops to Starter if no payment
- Monthly users who hit Starter limits see upgrade prompt
- In-app usage bar: "You've used 87/100 messages today. Upgrade to Pro for unlimited."

### Revenue model math (3-year unicorn path)
```
Year 1: 2,000 Pro users = $49 × 2,000 × 12 = $1.18M ARR
Year 2: 20,000 Pro + 500 Team seats = $11.8M + $2.3M = $14.1M ARR
Year 3: 80,000 Pro + 5,000 Team + 20 Enterprise = $47M + $23M + $6M = $76M ARR
         + Marketplace rev share (15%) + API platform = ~$100M ARR
```
At $100M ARR with 10x SaaS multiple = **$1B valuation**.

### Billing implementation
- Stripe for all subscriptions
- Stripe metered billing for Team plan (per seat)
- Stripe Customer Portal for self-serve plan changes
- Webhook events to handle: `customer.subscription.created`, `invoice.payment_failed`, `customer.subscription.deleted`
- Subscription status stored on `User.subscription_plan` + `User.subscription_status`
- Feature gates: middleware checks plan before allowing premium endpoints

---

## STEP 23: LOCAL DEVELOPMENT SETUP

### 23.1 Docker Compose dev override
Create `docker-compose.dev.yml`:
```yaml
version: "3.9"
services:
  backend:
    build:
      context: ./backend
      target: dev
    volumes:
      - ./backend:/app     # hot reload
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      - ENV=development
      - DATABASE_URL=postgresql://jarvis:dev@postgres:5432/jarvis_dev
      - REDIS_URL=redis://redis:6379/0
      - JWT_SECRET=local-dev-jwt-secret-min-32-chars-ok
      - SESSION_SECRET=local-dev-session-secret-min-32-ok
      - TOKEN_ENCRYPTION_KEY=bG9jYWwtZGV2LWVuY3J5cHRpb24ta2V5LTMyYg==
      - ALLOWED_ORIGINS=http://localhost:5173,http://localhost:80

  frontend:
    volumes:
      - ./frontend/src:/app/src    # hot reload via Vite
    command: npm run dev -- --host 0.0.0.0
    environment:
      - VITE_API_BASE=http://localhost:8000

  worker:
    volumes:
      - ./backend:/app
    command: celery -A worker worker --loglevel=debug --autoreload

  mock-oauth:
    build: ./tools/mock-oauth     # see 23.3
    ports:
      - "9000:9000"
```

Run dev: `docker compose -f docker-compose.yml -f docker-compose.dev.yml up`

### 23.2 Makefile commands
Create `Makefile` in repo root:
```makefile
.PHONY: dev prod seed test lint migrate

dev:
	docker compose -f docker-compose.yml -f docker-compose.dev.yml up

prod:
	docker compose up -d

seed:
	docker compose exec backend python seed.py

test:
	docker compose exec backend pytest backend/tests/ -v
	docker compose exec frontend npm run test

lint:
	docker compose exec backend ruff check . && mypy .
	docker compose exec frontend npm run lint

migrate:
	docker compose exec backend alembic upgrade head

migrate-new:
	docker compose exec backend alembic revision --autogenerate -m "$(name)"

shell:
	docker compose exec backend python

logs:
	docker compose logs -f backend worker

stop:
	docker compose down
```

### 23.3 Mock OAuth server (bypass Google/Microsoft for local dev)
Create `tools/mock-oauth/main.py` — a minimal FastAPI app that:
- Accepts OAuth authorize redirects for all providers
- Immediately redirects back with a fake `code=mock_code_123`
- On token exchange, returns a fake access_token
- Allows testing all 15 connector flows without real Google/Microsoft accounts

In `backend/.env.dev`, point OAuth redirect URIs and client IDs to `http://localhost:9000/mock-oauth/...`

Add env var: `MOCK_OAUTH=true` — when set, auth router uses mock tokens instead of real exchange.

### 23.4 Seed script
Create `backend/seed.py`:
```python
"""
Creates a test environment with realistic fake data.
Run: docker compose exec backend python seed.py
"""
# Creates:
# - 3 test users (founder@test.com / password: test123)
# - Mock OAuth tokens for all providers
# - 100 fake emails with varying priority scores
# - 10 calendar events (next 7 days)
# - 20 Linear tasks (mix of open/in-progress/done)
# - 5 Shopify orders
# - 10 Freshdesk tickets
# - 30 days of token usage history
# - Pre-populated knowledge chunks for RAG testing
```

### 23.5 Shopify dev store
1. Create Shopify Partner account (partners.shopify.com) — free
2. Create development store — free, unlimited test orders
3. Install your app on dev store using `localhost` redirect URIs via ngrok
4. Add to `Makefile`: `ngrok: ngrok http 8000` — exposes local backend for Shopify webhooks

### 23.6 Local environment file
Create `backend/.env.dev` (gitignored, only for local):
```bash
# Safe to commit placeholder, but actual values in .env.dev (gitignored)
ENV=development
JWT_SECRET=local-dev-jwt-secret-must-be-32-chars!
SESSION_SECRET=local-dev-session-secret-32chars!
TOKEN_ENCRYPTION_KEY=bG9jYWwtZGV2LWVuY3J5cHRpb24ta2V5LTMyYg==
DATABASE_URL=postgresql://jarvis:dev@localhost:5432/jarvis_dev
REDIS_URL=redis://localhost:6379/0
MOCK_OAUTH=true
# Add your own test API keys here (not committed):
ANTHROPIC_API_KEY=sk-ant-...
SHOPIFY_TEST_SHOP=yourdev.myshopify.com
```

---

## STEP 24: VERSION CONTROL + CI/CD

### 24.1 Git branch strategy
```
main          — production. Protected. Requires PR + passing CI.
staging       — staging environment. Auto-deploys on merge.
feature/*     — feature branches. Short-lived. PR into staging first.
hotfix/*      — emergency production fixes. PR directly into main.
```

Rules:
- `main` branch protection: require 1 PR approval + CI passing
- No direct commits to main or staging
- Merge staging → main for releases (weekly or on-demand)
- Use conventional commits: `feat:`, `fix:`, `chore:`, `docs:`

### 24.2 Semantic versioning
```
v1.0.0 — first production launch
v1.1.0 — new feature release
v1.0.1 — bug fix
v2.0.0 — breaking change (rare)
```
Tag releases: `git tag v1.0.0 && git push origin v1.0.0`

### 24.3 CHANGELOG.md
Create `CHANGELOG.md` in root. Update manually on each release:
```markdown
## [1.1.0] — 2026-06-01
### Added
- Shopify integration with full order management
- Freshdesk integration with crisis radar
- Intelligence tier selector (Eco/Intelligent/Scientist)

## [1.0.0] — 2026-05-20
### Added
- Initial production release
```

### 24.4 GitHub Actions CI/CD
Create `.github/workflows/ci.yml`:
```yaml
name: CI
on: [push, pull_request]
jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_DB: jarvis_test
          POSTGRES_USER: jarvis
          POSTGRES_PASSWORD: test
      redis:
        image: redis:7-alpine
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: "3.11"}
      - run: pip install -r backend/requirements.txt
      - run: pytest backend/tests/ -v --tb=short
        env:
          DATABASE_URL: postgresql://jarvis:test@localhost:5432/jarvis_test
          JWT_SECRET: test-secret-32-chars-minimum-here
          SESSION_SECRET: test-session-32-chars-minimum!!
          TOKEN_ENCRYPTION_KEY: dGVzdC1lbmNyeXB0aW9uLWtleS0zMmNoYXI=
          REDIS_URL: redis://localhost:6379/0

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: "20"}
      - run: cd frontend && npm ci && npm run build && npm run lint

  deploy-staging:
    needs: [backend-test, frontend-test]
    if: github.ref == 'refs/heads/staging'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to staging
        run: |
          # Railway/Render auto-deploy OR:
          # docker build + push to registry + SSH deploy

  deploy-prod:
    needs: [backend-test, frontend-test]
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest
    environment: production    # requires manual approval in GitHub UI
    steps:
      - uses: actions/checkout@v4
      - name: Deploy to production
        run: echo "Deploy steps here"
```

### 24.5 Pre-commit hooks
Create `.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.4.0
    hooks:
      - id: ruff
        args: [--fix]
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.9.0
    hooks:
      - id: mypy
        args: [--ignore-missing-imports]
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: check-merge-conflict
      - id: detect-private-key
```
Install: `pre-commit install`

---

## STEP 25: ZERO-DOWNTIME MIGRATION STRATEGY

### 25.1 Database migration rules (NEVER BREAK IN PROD)
Follow this sequence for every schema change:

**Adding a column:**
```
Deploy 1: Add column as nullable (ALTER TABLE ADD COLUMN x TEXT)
Deploy 2: Populate data, add NOT NULL constraint if needed
```

**Removing a column:**
```
Deploy 1: Stop reading/writing the column in code
Deploy 2: Remove column from DB (ALTER TABLE DROP COLUMN)
```

**Renaming a column:**
```
Deploy 1: Add new column, write to both old and new
Deploy 2: Read from new column
Deploy 3: Stop writing to old column
Deploy 4: Drop old column
```
**Never** rename a column in a single deploy. **Never** change a column type without a migration window.

### 25.2 Alembic migration workflow
Every DB change requires a migration:
```bash
# Create migration
make migrate-new name="add_user_settings_provider_column"

# Review generated file in alembic/versions/
# Test locally: make migrate

# In CI: alembic upgrade head runs before app starts
```

Backend Dockerfile CMD:
```dockerfile
CMD alembic upgrade head && uvicorn main:app --host 0.0.0.0 --port 8000
```

### 25.3 Deployment environments
```
local    → docker-compose.dev.yml (your machine)
staging  → Railway/Render staging env (mirrors prod, auto-deploy on staging branch)
prod     → Railway/Render prod env (manual approve in GitHub Actions)
```

Staging runs on real PostgreSQL, real Redis, real Celery. Only fake OAuth for integrations.

### 25.4 Rollback strategy
Every deploy: tag the Docker image with git SHA.
```
If prod breaks:
1. Railway/Render: one-click rollback to previous deploy
2. DB: alembic downgrade -1 (only works if migration was additive)
3. Hotfix branch → PR → deploy within 30 min
```

### 25.5 Health check endpoint (enhanced)
Update `/api/health` to test real dependencies:
```python
@app.get("/api/health")
async def health(db=Depends(get_db)):
    checks = {}
    # DB check
    try:
        db.execute("SELECT 1")
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"
    # Redis check
    try:
        r = redis.from_url(os.getenv("REDIS_URL"))
        r.ping()
        checks["redis"] = "ok"
    except:
        checks["redis"] = "error"
    status = "ok" if all(v == "ok" for v in checks.values()) else "degraded"
    return {"status": status, "version": "1.0.0", "checks": checks}
```

---

## STEP 26: UNICORN FEATURES — THINK BIGGER

These are the features that separate a $10M company from a $1B company.

### 26.1 JARVIS Memory (persistent explicit memory)
Users can explicitly tell JARVIS things to always remember:
- "Remember: My investor expects a monthly update every 1st of month"
- "Remember: Client Acme Corp is price-sensitive, always offer payment plans"
- "Remember: I'm trying to close a Series A by Q3 2026"

`GET /api/memories` — list all memories
`POST /api/memories` — add memory
`DELETE /api/memories/{id}` — forget

JARVIS injects all memories into every session. Switching products means losing this — huge lock-in.

### 26.2 JARVIS Relationship Graph
Build a graph of everyone the user communicates with:
- Score relationships: VIP / Regular / Cold / Risky
- Track: last contact, email frequency, response rate, sentiment trend
- Alert: "You haven't spoken to your top investor in 47 days"
- Suggest: "Sarah usually replies within 2 hours. It's been 3 days. Follow up?"

Stored as enhanced `SenderProfile` with graph edges.

### 26.3 Platform — JARVIS App Store
Third-party developers build "JARVIS Skills" (workflow integrations).
- `GET /api/skills/marketplace` — browse community skills
- Each skill: a config JSON + webhook that JARVIS calls
- Revenue: 15% rev share on paid skills
- Examples: "Salesforce Sync", "Twitter/X Monitor", "Amazon Seller", "Stripe Revenue"
- Viral: developers market their own skills → brings new JARVIS users

### 26.4 JARVIS API (developer platform)
Expose JARVIS intelligence as an API:
- Developers embed JARVIS in their own apps
- `POST /api/v1/query` with bearer token → JARVIS responds with context from that user
- Pricing: $0.05 per API call above free tier
- Use case: CRM company adds "Ask JARVIS" button powered by user's data

### 26.5 Sales Intelligence (CRM replacement)
JARVIS becomes a lightweight CRM:
- Identify leads in email (people who could become customers)
- Track deal stages in email threads (automatically)
- "You have 3 warm leads who haven't heard from you in 2 weeks. Draft follow-ups?"
- Win probability scoring based on response patterns
- Pipeline view: prospects → contacted → proposal → closed

### 26.6 Cash Flow Watch (Stripe + Xero integration)
Connect Stripe + Xero/QuickBooks:
- Real-time MRR, ARR, burn rate visible in dashboard
- "At current burn: 73 days runway"
- "3 invoices overdue totaling $12,400. Draft chase emails?"
- "Your biggest cost this month was AWS ($2,100). Want a cost breakdown?"
- Monthly P&L summary generated by JARVIS

### 26.7 JARVIS for Hiring
Connect LinkedIn (via RapidAPI) + email for hiring workflows:
- Parse resumes uploaded to JARVIS
- "Rank these 5 candidates against this job description"
- Auto-schedule interviews by checking calendar availability
- Draft offer letters, rejection emails
- Track candidate pipeline

### 26.8 JARVIS Voice App (standalone)
Separate mobile app: voice-only JARVIS.
- Open app, speak naturally
- JARVIS responds via ElevenLabs TTS
- Works while driving, walking, commuting
- "Hey JARVIS, any fires today?" → audio brief
- "Create a task to follow up with Sarah by Friday"
- Huge TAM: executives who hate typing

### 26.9 Achievement System (retention + virality)
Weekly stats shown to user:
- "You replied to 91% of priority emails this week 🏆"
- "Fastest response time this month: 4 min average"
- "You delegated 8 tasks this week — saved ~3 hours"
- Shareable weekly card (LinkedIn/Twitter): "My JARVIS week: 94% email response rate, 12 tasks completed"
- This is viral content + JARVIS brand exposure

### 26.10 White-label (agency play)
Agencies can resell branded JARVIS to their clients:
- Custom domain: `assistant.youragency.com`
- Custom branding: logo, colors, name ("ATLAS", "ARIA", etc)
- Agency pays wholesale, charges clients retail
- You take 20% rev share
- Zero sales effort — agencies do the selling

### 26.11 JARVIS Digest Email (zero app-open)
Daily email (opt-in) sent at 7am:
- Beautifully designed HTML email
- Contains: morning brief, priority emails, calendar, Shopify highlights
- "Open full brief in JARVIS" CTA
- Works even when user hasn't opened the app in days
- Critical for retention during low-engagement periods

### 26.12 Content Intelligence (marketing workflows)
Connect social platforms:
- LinkedIn + Twitter/X + Instagram via respective APIs
- "Draft a LinkedIn post about our product launch"
- "What content is performing best for our competitors?"
- "Schedule 5 posts for this week based on our brand voice"
- "Write a thread about [topic] in my voice" (learns from past posts via RAG)

### 26.13 Smart Templates (workflow automation)
Users create reusable JARVIS workflows:
- Trigger: "Every Monday 9am"
- Action: "Pull Shopify revenue + top 3 issues + email me a brief"
- Share templates with team or marketplace
- Pre-built templates for common roles:
  - E-commerce Founder Template Pack
  - SaaS Founder Template Pack
  - Consultant Template Pack
  - Agency Owner Template Pack

### 26.14 JARVIS Companion (browser extension)
Chrome/Firefox extension:
- "Add to JARVIS" button on any webpage (article, LinkedIn profile, email)
- Contextual AI: open in Gmail → JARVIS suggests reply
- "Summarize this page", "Create task from this", "Who is this person?"
- Brings JARVIS to where users already are
- Viral distribution: visible in everyone's browser

---

## STEP 27: GROWTH + VIRAL MECHANICS

### 27.1 Product-Led Growth (PLG)
The product sells itself through usage:
- **Morning brief sharing**: Auto-generated "Here's my day" card, shareable on LinkedIn
- **JARVIS signature**: Opt-in "Sent with JARVIS" footer on drafted emails (tiny, tasteful)
- **Template marketplace**: Users share workflows → brings new users
- **Team invites**: Pro users can invite teammates at Team pricing

### 27.2 Onboarding funnel
Day 0: Signup → "Connect your first tool" (Gmail) → First morning brief
Day 1: Automated email: "Your first JARVIS brief: here's what it found"
Day 3: Push: "You have 3 priority emails waiting"
Day 7: "Your weekly brief is ready"
Day 14: Trial ending → "You've saved X hours this week. Keep going?"

### 27.3 Acquisition channels
1. **Content**: "How I manage 300 emails/day as a founder" → JARVIS as solution
2. **Integrations**: Shopify app store listing → direct access to e-commerce founders
3. **Product Hunt**: Launch with morning brief demo video
4. **Founder communities**: Indie Hackers, Y Combinator forum, Twitter/X
5. **Agency partnerships**: "Offer JARVIS to your clients" white-label play

### 27.4 Retention metrics to track
- DAU/MAU ratio (target: >50% — people use it daily)
- Morning brief open rate (target: >70%)
- Messages per user per day (target: >5)
- Integrations per user (more integrations = stickier)
- 90-day retention (target: >60%)

---

## UPDATED IMPLEMENTATION ORDER (WITH ALL ADDITIONS)

```
Week 1:  Steps 0-1  — Security fixes + Infrastructure (Postgres, Redis, Celery)
         Step 24    — Git workflow + CI/CD setup (parallel, takes 1 day)
         Step 23    — Local dev setup with seed data

Week 2:  Step 21   — Provider-agnostic AI layer (build first, all AI on top of it)
         Steps 2-3  — New DB models + Intelligence tiers via abstraction layer
         Step 4     — BYOAK (all providers)

Week 3:  Steps 5-7  — Streaming + Multimodal + Personality modes
         Step 13    — Settings page (needed for BYOAK + provider selection)
         Step 12    — Token monitor

Week 4:  Step 8    — User profile + RAG knowledge base
         Step 22   — Implement billing/plans with Stripe

Week 5:  Steps 9-10 — Shopify + Freshdesk

Week 6:  Step 11   — Dashboard prompts
         Step 14   — Founder intelligence (decision inbox, meeting prep, weekly brief)

Week 7:  Steps 26.1-26.4 — Memory, relationship graph, achievement system, digest email
         Step 15   — Frontend polish

Week 8:  Beta with 10 real users. Fix what's broken. Ship.

Parallel (entire time):
- Google OAuth verification (submit Week 1, approve ~Week 8-16)
- Shopify Partner app review
- Write privacy policy + terms of service
- Set up staging + prod environments
```

---

## UPDATED GENERAL RULES

All rules from the original GENERAL RULES section still apply, plus:

- **Provider abstraction is non-negotiable**: Any call to an AI model must go through `AIProvider`. No raw `anthropic.AsyncAnthropic()` in business logic ever.
- **Environment parity**: local dev, staging, and prod must run identical Docker configs. "Works on my machine" is not acceptable.
- **Migration safety**: Every `alembic revision` must be reviewed for backwards compatibility before merge. No destructive migrations without a multi-step deploy plan.
- **Feature flags**: New features that are risky or incomplete get wrapped in `if settings.feature_X_enabled:` so they can be toggled per user without a deploy.
- **Telemetry**: Every significant user action gets logged: `{"event": "chat_message", "tier": "intelligent", "provider": "anthropic", "tokens": 1240}`. This is how you track DAU, feature adoption, and cost.
- **Graceful degradation**: If Shopify is down, feed still loads without it. If RAG search fails, chat continues without context. Never let one connector failure break the whole experience.
- **BYOAK first, platform-pays later**: For launch, users bring their own API key. When you reach 1,000+ users who struggle with API keys, add a platform-pays Stripe metered option. Don't build it now.
