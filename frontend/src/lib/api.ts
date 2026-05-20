/**
 * Typed wrappers for the backend HTTP API.
 *
 * Centralized so:
 *   - Bearer header is attached in one place
 *   - Empty/non-JSON responses don't crash callers
 *   - Routes that change can be migrated by editing this file alone
 */
import type {
  TokenUsageDay,
  TokenUsageToday,
  UserContextSnapshot,
  UserSettingsSnapshot,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE || "";

function token(): string | null {
  return localStorage.getItem("jarvis_token");
}

async function call<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers as HeadersInit | undefined);
  if (!headers.has("Content-Type") && init.body) headers.set("Content-Type", "application/json");
  const t = token();
  if (t) headers.set("Authorization", `Bearer ${t}`);

  const r = await fetch(`${BASE}${path}`, { ...init, headers });
  if (!r.ok) {
    let detail = "";
    try {
      const j = await r.json();
      detail = j?.detail || JSON.stringify(j);
    } catch {
      detail = await r.text().catch(() => "");
    }
    throw new ApiError(r.status, detail || `HTTP ${r.status}`);
  }
  // Some endpoints return empty body
  if (r.status === 204) return undefined as T;
  const text = await r.text();
  if (!text) return undefined as T;
  try { return JSON.parse(text) as T; } catch { return text as unknown as T; }
}

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// ── Settings ────────────────────────────────────────────────────────────────

export const SettingsAPI = {
  get: () => call<UserSettingsSnapshot>("/api/settings"),

  putKeys: (keys: Partial<Record<
    "anthropic_api_key" | "openai_api_key" | "groq_api_key" | "mistral_api_key" |
    "google_api_key" | "elevenlabs_api_key" | "github_pat" | "github_repo_url",
    string
  >>) =>
    call<UserSettingsSnapshot>("/api/settings/api-keys", {
      method: "PUT",
      body: JSON.stringify(keys),
    }),

  testKey: (provider: string, api_key: string) =>
    call<{ ok: boolean; error?: string }>("/api/settings/test-key", {
      method: "POST",
      body: JSON.stringify({ provider, api_key }),
    }),

  putPreferences: (prefs: Partial<{
    default_model: string;
    response_length: "brief" | "detailed" | "deep";
    personality_mode: string;
    daily_token_budget: number;
    budget_alert_pct: number;
  }>) =>
    call<UserSettingsSnapshot>("/api/settings/preferences", {
      method: "PUT",
      body: JSON.stringify(prefs),
    }),

  putActiveProvider: (ai_provider: string) =>
    call<UserSettingsSnapshot>("/api/settings/active-provider", {
      method: "PUT",
      body: JSON.stringify({ ai_provider }),
    }),
};

// ── Context ─────────────────────────────────────────────────────────────────

export const ContextAPI = {
  get: () => call<UserContextSnapshot>("/api/context"),

  put: (ctx: Partial<UserContextSnapshot>) =>
    call<UserContextSnapshot>("/api/context", {
      method: "PUT",
      body: JSON.stringify(ctx),
    }),
};

// ── Tokens ──────────────────────────────────────────────────────────────────

export const TokensAPI = {
  today: () => call<TokenUsageToday>("/api/tokens/today"),

  history: (days = 7) =>
    call<{ days: number; series: TokenUsageDay[] }>(`/api/tokens/history?days=${days}`),

  session: (limit = 20) =>
    call<{ calls: Array<{ id: number; created_at: string; provider: string; model: string;
                          input: number; output: number; cache_read: number; cost_usd: number }> }>(
      `/api/tokens/session?limit=${limit}`,
    ),
};

// ── Decisions ──────────────────────────────────────────────────────────────

export interface DecisionRow {
  id: number;
  source: string;
  source_id: string | null;
  title: string;
  context_json: any;
  status: string;
  ai_suggestion: string | null;
  snoozed_until: string | null;
  created_at: string | null;
  decided_at: string | null;
}

export const DecisionsAPI = {
  list: (status: string = "pending") =>
    call<{ decisions: DecisionRow[] }>(`/api/decisions?status=${encodeURIComponent(status)}`),

  patch: (id: number, patch: { status?: string; ai_suggestion?: string; snooze_hours?: number }) =>
    call<DecisionRow>(`/api/decisions/${id}`, {
      method: "PATCH",
      body: JSON.stringify(patch),
    }),

  remove: (id: number) =>
    call<{ ok: boolean }>(`/api/decisions/${id}`, { method: "DELETE" }),

  create: (d: Partial<DecisionRow>) =>
    call<DecisionRow>("/api/decisions", {
      method: "POST",
      body: JSON.stringify(d),
    }),
};

// ── Intel briefs ────────────────────────────────────────────────────────────

export interface IntelBrief {
  id: number;
  name: string;
  topic: string;
  sources_json: any;
  prompt_template: string | null;
  frequency_minutes: number | null;
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  created_at: string | null;
}

export interface IntelBriefRun {
  id: number;
  brief_id: number;
  status: "pending" | "running" | "done" | "failed";
  output_text: string | null;
  sources_summary: Record<string, number> | null;
  error: string | null;
  cost_usd: number;
  started_at: string | null;
  finished_at: string | null;
}

export const IntelAPI = {
  list: () => call<{ briefs: IntelBrief[] }>("/api/intel-briefs"),
  create: (b: Partial<IntelBrief>) =>
    call<IntelBrief>("/api/intel-briefs", { method: "POST", body: JSON.stringify(b) }),
  update: (id: number, patch: Partial<IntelBrief>) =>
    call<IntelBrief>(`/api/intel-briefs/${id}`, { method: "PUT", body: JSON.stringify(patch) }),
  remove: (id: number) =>
    call<{ ok: boolean }>(`/api/intel-briefs/${id}`, { method: "DELETE" }),
  run: (id: number) =>
    call<IntelBriefRun>(`/api/intel-briefs/${id}/run`, { method: "POST" }),
  runs: (id: number, limit = 20) =>
    call<{ runs: IntelBriefRun[] }>(`/api/intel-briefs/${id}/runs?limit=${limit}`),
};

// ── Chat meta ───────────────────────────────────────────────────────────────

export const ChatMetaAPI = {
  personalities: () => call<{
    default: string;
    modes: Array<{ id: string; label: string; style: string }>;
  }>("/api/chat/personalities"),

  quickActions: () => call<{
    actions: Array<{ id: string; label: string; prompt: string }>;
  }>("/api/chat/quick-actions"),
};
