import { create } from "zustand";
import type {
  CalendarEvent,
  ChatTurn,
  EmailItem,
  MessageItem,
  Mode,
  PanelKey,
  TaskItem,
  ToastItem,
  ToolEvent,
  WakeState,
  ConnectorStatus,
} from "../types";

const API = import.meta.env.VITE_API_BASE || "";

const storedToken = typeof window !== "undefined" ? localStorage.getItem("jarvis_token") : null;

const storedPanels = (() => {
  try { return JSON.parse(localStorage.getItem("jarvis_panels") || "{}"); } catch { return {}; }
})();
const defaultPanelVisibility: Record<PanelKey, boolean> = {
  calendar: storedPanels.calendar ?? true,
  email: storedPanels.email ?? true,
  tasks: storedPanels.tasks ?? true,
  projects: storedPanels.projects ?? true,
};

interface JarvisState {
  // Auth
  token: string | null;
  user: { email: string } | null;
  isAuthenticated: boolean;
  authError: string | null;
  // Data
  wakeState: WakeState;
  mode: Mode;
  events: CalendarEvent[];
  emails: EmailItem[];
  messages: MessageItem[];
  tasks: TaskItem[];
  projects: TaskItem[];
  chat: ChatTurn[];
  connectors: ConnectorStatus[];
  // UI state
  panelVisibility: Record<PanelKey, boolean>;
  toasts: ToastItem[];
  // Actions — auth
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, industry: string) => Promise<void>;
  logout: () => void;
  /** Hit /api/users/me with the current token. If 401, clear localStorage
   *  and flip isAuthenticated to false — kicks stale JWT sessions left
   *  over from old dev logins. Returns true if the token is still valid. */
  validateSession: () => Promise<boolean>;
  // Actions — data
  setWakeState: (s: WakeState) => void;
  setMode: (m: Mode) => void;
  fetchFeed: () => Promise<void>;
  fetchConnectors: () => Promise<void>;
  sendChat: (text: string) => Promise<string>;
  streamChat: (
    text: string,
    callbacks: {
      onToken?: (delta: string) => void;
      onToolStart?: (name: string) => void;
      onToolEnd?: (name: string, ok: boolean) => void;
      onCorrection?: (correctedText: string, violations: Array<{ phrase: string; required_tools: string[] }>) => void;
      onDone?: (usage: any) => void;
      onError?: (error: string) => void;
    },
    signal?: AbortSignal,
    file_ids?: number[],
  ) => Promise<void>;
  appendChat: (turn: ChatTurn) => void;
  // Actions — UI
  setPanelVisibility: (key: PanelKey, visible: boolean) => void;
  addToast: (toast: Omit<ToastItem, "id">) => void;
  removeToast: (id: string) => void;
}

function authHeaders(token: string | null): HeadersInit {
  const h: HeadersInit = { "Content-Type": "application/json" };
  if (token) h["Authorization"] = `Bearer ${token}`;
  return h;
}

export const useJarvisStore = create<JarvisState>((set, get) => ({
  // Auth initial state — restore from localStorage
  token: storedToken,
  user: null,
  isAuthenticated: !!storedToken,
  authError: null,

  // Data initial state
  wakeState: "idle",
  mode: "voice",
  events: [],
  emails: [],
  messages: [],
  tasks: [],
  projects: [],
  chat: [],
  connectors: [],

  // UI initial state
  panelVisibility: defaultPanelVisibility,
  toasts: [],

  // ── Auth actions ──────────────────────────────────────────────────────────

  login: async (email, password) => {
    set({ authError: null });
    const r = await fetch(`${API}/api/users/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      set({ authError: data.detail || "Login failed" });
      return;
    }
    const data = await r.json();
    localStorage.setItem("jarvis_token", data.access_token);
    set({ token: data.access_token, isAuthenticated: true, user: { email } });
  },

  register: async (email, password, industry) => {
    set({ authError: null });
    const r = await fetch(`${API}/api/users/register`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password, industry }),
    });
    if (!r.ok) {
      const data = await r.json().catch(() => ({}));
      set({ authError: data.detail || "Registration failed" });
      return;
    }
    const data = await r.json();
    localStorage.setItem("jarvis_token", data.access_token);
    set({ token: data.access_token, isAuthenticated: true, user: { email } });
  },

  logout: () => {
    localStorage.removeItem("jarvis_token");
    set({ token: null, user: null, isAuthenticated: false });
  },

  validateSession: async () => {
    // Re-read from localStorage — covers multi-tab case where another tab
    // logged in as a different user and updated the storage. Our in-memory
    // copy may be a stale token from an older session.
    const fresh = typeof window !== "undefined" ? localStorage.getItem("jarvis_token") : null;
    if (fresh && fresh !== get().token) {
      set({ token: fresh });
    }
    const token = fresh || get().token;
    if (!token) {
      set({ token: null, user: null, isAuthenticated: false });
      return false;
    }
    try {
      const r = await fetch(`${API}/api/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (r.status === 401) {
        // Stale / revoked JWT — drop it. Forces a fresh login + prevents
        // OAuth flows from minting one-time codes for the wrong user.
        localStorage.removeItem("jarvis_token");
        set({ token: null, user: null, isAuthenticated: false });
        return false;
      }
      if (!r.ok) return false;
      const u = await r.json();
      set({ user: { email: u.email } });
      return true;
    } catch {
      // Network failure — assume token still good; we'll re-check next boot.
      return true;
    }
  },

  // ── Data actions ──────────────────────────────────────────────────────────

  setWakeState: (s) => set({ wakeState: s }),
  setMode: (m) => set({ mode: m }),

  fetchFeed: async () => {
    const { token } = get();
    try {
      const r = await fetch(`${API}/api/feed`, { headers: authHeaders(token) });
      if (!r.ok) return;
      const data = await r.json();
      set({
        events: data.events || [],
        emails: data.emails || [],
        messages: data.messages || [],
        tasks: data.tasks || [],
        projects: data.projects || [],
      });
    } catch { /* network or parse error — silently ignore */ }
  },

  fetchConnectors: async () => {
    const { token } = get();
    try {
      const r = await fetch(`${API}/api/auth/status`, { headers: authHeaders(token) });
      if (!r.ok) return;
      const data = await r.json();
      set({ connectors: data.connectors || [] });
    } catch { /* silently ignore */ }
  },

  sendChat: async (text: string) => {
    const { token } = get();
    get().appendChat({ role: "user", text, timestamp: Date.now() });
    set({ wakeState: "processing" });
    try {
      const r = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ message: text }),
      });
      if (!r.ok) {
        const err = await r.json().catch(() => ({ reply: "Error contacting JARVIS." }));
        const reply = err.detail || err.reply || "Something went wrong.";
        get().appendChat({ role: "assistant", text: reply, timestamp: Date.now() });
        set({ wakeState: "idle" });
        return reply;
      }
      const data = await r.json();
      const reply = data.reply || "";
      get().appendChat({ role: "assistant", text: reply, timestamp: Date.now() });
      set({ wakeState: "responding" });
      setTimeout(() => set({ wakeState: "idle" }), 1500);
      return reply;
    } catch {
      const reply = "Network error — check connection.";
      get().appendChat({ role: "assistant", text: reply, timestamp: Date.now() });
      set({ wakeState: "idle" });
      return reply;
    }
  },

  streamChat: async (text, callbacks, signal, file_ids) => {
    const { token } = get();
    get().appendChat({ role: "user", text, timestamp: Date.now() });
    set({ wakeState: "processing" });
    try {
      const r = await fetch(`${API}/api/chat/stream`, {
        method: "POST",
        headers: authHeaders(token),
        body: JSON.stringify({ message: text, file_ids: file_ids || [] }),
        signal,
      });
      if (!r.ok || !r.body) {
        const errMsg = `HTTP ${r.status}`;
        callbacks.onError?.(errMsg);
        set({ wakeState: "idle" });
        return;
      }

      const reader = r.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      let assembled = "";
      const tools: ToolEvent[] = [];

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });

        // SSE messages are separated by \n\n
        let nl;
        while ((nl = buf.indexOf("\n\n")) >= 0) {
          const event = buf.slice(0, nl).trim();
          buf = buf.slice(nl + 2);
          if (!event.startsWith("data:")) continue;
          const payload = event.slice(5).trim();
          if (payload === "[DONE]") {
            // graceful end
            continue;
          }
          try {
            const parsed = JSON.parse(payload);
            if (parsed.type === "token" && parsed.text) {
              assembled += parsed.text;
              callbacks.onToken?.(parsed.text);
            } else if (parsed.type === "tool_start" && parsed.name) {
              tools.push({ name: parsed.name, status: "running" });
              callbacks.onToolStart?.(parsed.name);
            } else if (parsed.type === "tool_end" && parsed.name) {
              // Mark the most recent matching "running" entry. Multiple
              // calls to the same tool in one turn are rare but possible.
              for (let i = tools.length - 1; i >= 0; i--) {
                if (tools[i].name === parsed.name && tools[i].status === "running") {
                  tools[i] = { name: parsed.name, status: parsed.ok ? "ok" : "fail" };
                  break;
                }
              }
              callbacks.onToolEnd?.(parsed.name, !!parsed.ok);
            } else if (parsed.type === "correction" && parsed.text) {
              // Server-side guardrail caught the model claiming an action
              // it never invoked the tool for. Replace the streamed-in
              // (lying) text with the corrected, prefixed version so the
              // user sees the honesty correction instead of the lie.
              assembled = parsed.text;
              callbacks.onCorrection?.(parsed.text, parsed.violations || []);
            } else if (parsed.type === "done") {
              callbacks.onDone?.(parsed.usage || {});
            } else if (parsed.type === "error") {
              callbacks.onError?.(parsed.text || "stream error");
            }
          } catch {
            // ignore malformed chunk
          }
        }
      }

      // Persist assistant turn to local chat history
      if (assembled || tools.length) {
        get().appendChat({
          role: "assistant",
          text: assembled,
          timestamp: Date.now(),
          tools: tools.length ? tools : undefined,
        });
      }
      set({ wakeState: "responding" });
      setTimeout(() => set({ wakeState: "idle" }), 800);
    } catch (e: any) {
      if (e?.name === "AbortError") {
        callbacks.onError?.("aborted");
      } else {
        callbacks.onError?.(e?.message || "network error");
      }
      set({ wakeState: "idle" });
    }
  },

  appendChat: (turn) => set((s) => ({ chat: [...s.chat, turn] })),

  // ── UI actions ────────────────────────────────────────────────────────────

  setPanelVisibility: (key, visible) => set((s) => {
    const next = { ...s.panelVisibility, [key]: visible };
    localStorage.setItem("jarvis_panels", JSON.stringify(next));
    return { panelVisibility: next };
  }),

  addToast: (toast) => {
    const id = Math.random().toString(36).slice(2);
    const item: ToastItem = { ...toast, id, duration: toast.duration ?? 4000 };
    set((s) => ({ toasts: [...s.toasts, item] }));
    setTimeout(() => get().removeToast(id), item.duration);
  },

  removeToast: (id) => set((s) => ({ toasts: s.toasts.filter((t) => t.id !== id) })),
}));
