export type WakeState = "idle" | "listening" | "processing" | "responding";

export type Mode = "voice" | "text";

export interface CalendarEvent {
  id: string;
  title: string;
  start: string;
  end: string;
  location?: string;
  attendees?: string[];
  source: "google" | "outlook";
}

export interface EmailItem {
  id: string;
  from: string;
  subject: string;
  snippet: string;
  received: string;
  priority: number;
  source: "gmail" | "outlook";
  unread: boolean;
}

export interface MessageItem {
  id: string;
  from: string;
  text: string;
  channel?: string;
  received: string;
  source: "slack" | "teams" | "whatsapp";
}

export interface TaskItem {
  id: string;
  title: string;
  due?: string;
  status: string;
  source: "linear" | "jira" | "notion" | "github";
  url?: string;
}

export interface ToolEvent {
  name: string;
  status: "running" | "ok" | "fail";
}

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  timestamp: number;
  tools?: ToolEvent[];
}

export interface ConnectorStatus {
  name: string;
  connected: boolean;
  configured: boolean;
  display: string;
}

export type PanelKey = "calendar" | "email" | "tasks" | "projects";

export interface ToastItem {
  id: string;
  type: "success" | "error" | "info" | "warning";
  message: string;
  duration?: number;
}

export type AIProvider = "anthropic" | "openai" | "groq" | "mistral" | "google";
export type Tier = "eco" | "intelligent" | "scientist";
export type Personality =
  | "all_purpose"
  | "coder"
  | "designer"
  | "writer"
  | "marketer"
  | "founder"
  | "researcher"
  | "analyst"
  | "coach"
  | "devils_advocate"
  | "creative";

export interface UserSettingsSnapshot {
  ai_provider: AIProvider;
  default_model: string;
  response_length: "brief" | "detailed" | "deep";
  personality_mode: Personality;
  daily_token_budget: number;
  budget_alert_pct: number;
  github_repo_url: string | null;
  keys_set: Record<string, boolean>;
  keys_masked: Record<string, string | null>;
  updated_at: string | null;
}

export interface UserContextSnapshot {
  about_me: string | null;
  communication_style: string | null;
  priorities: string | null;
  team_members: { name: string; role?: string; relationship?: string }[] | null;
  business_context: string | null;
  updated_at: string | null;
}

export interface TokenUsageToday {
  date: string;
  input: number;
  output: number;
  cache_read: number;
  cost_usd: number;
  calls: number;
  budget: number;
  used_total_tokens: number;
  used_pct: number;
}

export interface TokenUsageDay {
  date: string;
  input: number;
  output: number;
  cost_usd: number;
  calls: number;
}
