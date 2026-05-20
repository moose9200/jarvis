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
  // Actions — data
  setWakeState: (s: WakeState) => void;
  setMode: (m: Mode) => void;
  fetchFeed: () => Promise<void>;
  fetchConnectors: () => Promise<void>;
  sendChat: (text: string) => Promise<string>;
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
