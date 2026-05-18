import { create } from "zustand";
import type {
  CalendarEvent,
  ChatTurn,
  EmailItem,
  MessageItem,
  Mode,
  TaskItem,
  WakeState,
  ConnectorStatus,
} from "../types";

const API = import.meta.env.VITE_API_BASE || "";

interface JarvisState {
  wakeState: WakeState;
  mode: Mode;
  events: CalendarEvent[];
  emails: EmailItem[];
  messages: MessageItem[];
  tasks: TaskItem[];
  projects: TaskItem[];
  chat: ChatTurn[];
  connectors: ConnectorStatus[];
  setWakeState: (s: WakeState) => void;
  setMode: (m: Mode) => void;
  fetchFeed: () => Promise<void>;
  fetchConnectors: () => Promise<void>;
  sendChat: (text: string) => Promise<string>;
  appendChat: (turn: ChatTurn) => void;
}

export const useJarvisStore = create<JarvisState>((set, get) => ({
  wakeState: "idle",
  mode: "voice",
  events: [],
  emails: [],
  messages: [],
  tasks: [],
  projects: [],
  chat: [],
  connectors: [],
  setWakeState: (s) => set({ wakeState: s }),
  setMode: (m) => set({ mode: m }),
  fetchFeed: async () => {
    const r = await fetch(`${API}/api/feed`);
    if (!r.ok) return;
    const data = await r.json();
    set({
      events: data.events || [],
      emails: data.emails || [],
      messages: data.messages || [],
      tasks: data.tasks || [],
      projects: data.projects || [],
    });
  },
  fetchConnectors: async () => {
    const r = await fetch(`${API}/api/auth/status`);
    if (!r.ok) return;
    const data = await r.json();
    set({ connectors: data.connectors || [] });
  },
  sendChat: async (text: string) => {
    get().appendChat({ role: "user", text, timestamp: Date.now() });
    set({ wakeState: "processing" });
    const r = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
    });
    const data = await r.json();
    const reply = data.reply || "";
    get().appendChat({ role: "assistant", text: reply, timestamp: Date.now() });
    set({ wakeState: "responding" });
    setTimeout(() => set({ wakeState: "idle" }), 1500);
    return reply;
  },
  appendChat: (turn) => set((s) => ({ chat: [...s.chat, turn] })),
}));
