# JARVIS — AI Personal Assistant Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a 3D JARVIS-inspired AI personal assistant web app that aggregates calendar, email, tasks, and messages from 11 services into one prioritized daily view, driven by Claude via voice or chat.

**Architecture:** React 18 + Vite frontend with React Three Fiber 3D HUD; Python FastAPI backend with SQLite; Claude claude-sonnet-4-6 with tool use for all connectors; OAuth2 per-service token storage.

**Tech Stack:** React, Vite, TypeScript, React Three Fiber, Three.js, Zustand, Framer Motion, Tailwind CSS, Python 3.11, FastAPI, SQLite, Anthropic SDK, httpx, MSAL, ElevenLabs TTS, Web Speech API

---

## Task 1: Project Scaffold & README

**Files:**
- Create: `jarvis/README.md`
- Create: `jarvis/.gitignore`

**Steps:**
- [ ] Create root project directory `jarvis/`
- [ ] Initialize git repository
- [ ] Create README with overview
- [ ] Create .gitignore for Python and Node

**`jarvis/README.md`:**
```markdown
# JARVIS — AI Personal Assistant

A 3D JARVIS-inspired AI personal assistant. Aggregates calendar, email, tasks, and messages from 11 services (Gmail, Google Calendar, Outlook Mail, Outlook Calendar, Slack, Teams, WhatsApp, GitHub, Linear, Jira, Notion) into one prioritized daily view, driven by Claude via voice or chat.

## Architecture

- **Frontend:** React 18 + Vite + TypeScript + React Three Fiber 3D HUD
- **Backend:** Python 3.11 + FastAPI + SQLite
- **AI:** Claude `claude-sonnet-4-6` with tool use; `claude-haiku-4-5-20251001` for compression
- **Voice:** Web Speech API (STT) + ElevenLabs (TTS, Adam voice)

## Quick Start

```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # fill in keys
uvicorn main:app --reload --port 8000

# Frontend (new terminal)
cd frontend
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:5173.

## Project Layout

- `frontend/` — Vite app with HUD scene, panels, chat overlay
- `backend/` — FastAPI app with connectors, AI orchestration, OAuth
```

**`jarvis/.gitignore`:**
```
# Python
__pycache__/
*.py[cod]
venv/
.env
*.db

# Node
node_modules/
dist/
.env.local
.env

# Editor
.vscode/
.idea/
.DS_Store
```

**Run:**
```bash
cd jarvis && git init && git add . && git commit -m "Task 1: project scaffold"
```

Expected output: `[main (root-commit) ...] Task 1: project scaffold`

---

## Task 2: Frontend Bootstrap (Vite + TypeScript + Tailwind)

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/tsconfig.json`
- Create: `frontend/tailwind.config.js`
- Create: `frontend/postcss.config.js`
- Create: `frontend/index.html`
- Create: `frontend/.env.example`

**Steps:**
- [ ] Create `frontend/` directory
- [ ] Write package.json with all dependencies
- [ ] Write Vite + TS + Tailwind configs
- [ ] Write index.html with mounting div

**`frontend/package.json`:**
```json
{
  "name": "jarvis-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "@react-three/drei": "^9.99.0",
    "@react-three/fiber": "^8.15.19",
    "framer-motion": "^11.0.5",
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "three": "^0.161.0",
    "zustand": "^4.5.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.55",
    "@types/react-dom": "^18.2.19",
    "@types/three": "^0.161.2",
    "@vitejs/plugin-react": "^4.2.1",
    "autoprefixer": "^10.4.17",
    "postcss": "^8.4.35",
    "tailwindcss": "^3.4.1",
    "typescript": "^5.3.3",
    "vite": "^5.1.3"
  }
}
```

**`frontend/vite.config.ts`:**
```ts
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

**`frontend/tsconfig.json`:**
```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": false,
    "noUnusedParameters": false,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"]
}
```

**`frontend/tailwind.config.js`:**
```js
/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        jbg: "#0a0e1a",
        jcyan: "#00d4ff",
        jblue: "#0066ff",
        jurgent: "#ff3333",
      },
      fontFamily: {
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
};
```

**`frontend/postcss.config.js`:**
```js
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
```

**`frontend/index.html`:**
```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>JARVIS</title>
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
    <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@300;400;500;700&display=swap" rel="stylesheet" />
  </head>
  <body class="bg-jbg text-white">
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

**`frontend/.env.example`:**
```
VITE_API_BASE=http://localhost:8000
VITE_ELEVENLABS_KEY=
```

**Run:**
```bash
cd frontend && npm install
```

Expected output: `added NNN packages`

```bash
git add frontend && git commit -m "Task 2: frontend bootstrap"
```

---

## Task 3: Frontend Entry, Global Styles & Types

**Files:**
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/index.css`
- Create: `frontend/src/types/index.ts`

**Steps:**
- [ ] Write Tailwind directives and global CSS
- [ ] Write main.tsx mounting
- [ ] Write App shell with HUD scene placeholder
- [ ] Define shared TypeScript types

**`frontend/src/index.css`:**
```css
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root {
  height: 100%;
  margin: 0;
  overflow: hidden;
  background: #0a0e1a;
  font-family: "JetBrains Mono", monospace;
  color: #ffffff;
}

canvas {
  display: block;
}
```

**`frontend/src/main.tsx`:**
```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

**`frontend/src/types/index.ts`:**
```ts
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

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}

export interface ConnectorStatus {
  name: string;
  connected: boolean;
  display: string;
}
```

**`frontend/src/App.tsx`:**
```tsx
import { HUDScene } from "./components/hud/HUDScene";
import { CalendarPanel } from "./components/panels/CalendarPanel";
import { EmailPanel } from "./components/panels/EmailPanel";
import { TaskPanel } from "./components/panels/TaskPanel";
import { ProjectPanel } from "./components/panels/ProjectPanel";
import { ChatOverlay } from "./components/interface/ChatOverlay";
import { VoiceVisualizer } from "./components/interface/VoiceVisualizer";
import { ModeToggle } from "./components/interface/ModeToggle";
import { useJarvisStore } from "./store/jarvisStore";

export default function App() {
  const mode = useJarvisStore((s) => s.mode);
  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <HUDScene />
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-4 p-4 pointer-events-none">
        <CalendarPanel />
        <EmailPanel />
        <TaskPanel />
        <ProjectPanel />
      </div>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {mode === "voice" ? <VoiceVisualizer /> : <ChatOverlay />}
      </div>
      <ModeToggle />
    </div>
  );
}
```

**Run:**
```bash
git add frontend/src && git commit -m "Task 3: frontend entry and types"
```

---

## Task 4: Zustand Store

**Files:**
- Create: `frontend/src/store/jarvisStore.ts`

**Steps:**
- [ ] Define Zustand store with wake state, mode, panel data, chat log
- [ ] Add async actions for fetching feed and posting chat

**`frontend/src/store/jarvisStore.ts`:**
```ts
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
```

**Run:**
```bash
git add frontend/src/store && git commit -m "Task 4: Zustand store"
```

---

## Task 5: 3D HUD Scene (Arc Reactor, Orb, Particles)

**Files:**
- Create: `frontend/src/components/hud/HUDScene.tsx`
- Create: `frontend/src/components/hud/ArcReactorRings.tsx`
- Create: `frontend/src/components/hud/CentralOrb.tsx`
- Create: `frontend/src/components/hud/ParticleField.tsx`

**Steps:**
- [ ] Build R3F Canvas wrapper
- [ ] Build rotating ring stack reacting to wake state
- [ ] Build pulsing central orb
- [ ] Build ambient particle field

**`frontend/src/components/hud/HUDScene.tsx`:**
```tsx
import { Canvas } from "@react-three/fiber";
import { ArcReactorRings } from "./ArcReactorRings";
import { CentralOrb } from "./CentralOrb";
import { ParticleField } from "./ParticleField";

export function HUDScene() {
  return (
    <Canvas
      camera={{ position: [0, 0, 6], fov: 50 }}
      className="absolute inset-0"
      gl={{ antialias: true, alpha: true }}
    >
      <ambientLight intensity={0.4} />
      <pointLight position={[0, 0, 5]} color="#00d4ff" intensity={2} />
      <ParticleField />
      <ArcReactorRings />
      <CentralOrb />
    </Canvas>
  );
}
```

**`frontend/src/components/hud/ArcReactorRings.tsx`:**
```tsx
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { useJarvisStore } from "../../store/jarvisStore";

export function ArcReactorRings() {
  const g1 = useRef<THREE.Group>(null);
  const g2 = useRef<THREE.Group>(null);
  const g3 = useRef<THREE.Group>(null);
  const wake = useJarvisStore((s) => s.wakeState);

  useFrame((_, dt) => {
    const speed =
      wake === "listening" ? 1.8 : wake === "processing" ? 3.2 : wake === "responding" ? 1.4 : 0.4;
    if (g1.current) g1.current.rotation.z += dt * speed;
    if (g2.current) g2.current.rotation.z -= dt * speed * 0.7;
    if (g3.current) g3.current.rotation.z += dt * speed * 0.5;
  });

  const color =
    wake === "idle" ? "#0066ff" : wake === "processing" ? "#00ffff" : "#00d4ff";

  return (
    <>
      <group ref={g1}>
        <mesh>
          <torusGeometry args={[1.6, 0.02, 16, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.85} />
        </mesh>
      </group>
      <group ref={g2}>
        <mesh>
          <torusGeometry args={[2.0, 0.015, 16, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.6} />
        </mesh>
      </group>
      <group ref={g3}>
        <mesh>
          <torusGeometry args={[2.4, 0.01, 16, 128]} />
          <meshBasicMaterial color={color} transparent opacity={0.35} />
        </mesh>
      </group>
    </>
  );
}
```

**`frontend/src/components/hud/CentralOrb.tsx`:**
```tsx
import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import * as THREE from "three";
import { useJarvisStore } from "../../store/jarvisStore";

export function CentralOrb() {
  const ref = useRef<THREE.Mesh>(null);
  const wake = useJarvisStore((s) => s.wakeState);

  useFrame(({ clock }) => {
    if (!ref.current) return;
    const t = clock.getElapsedTime();
    const base = wake === "idle" ? 1 : wake === "listening" ? 1.15 : wake === "processing" ? 1.25 : 1.1;
    const s = base + Math.sin(t * 3) * 0.05;
    ref.current.scale.set(s, s, s);
  });

  const intensity = wake === "idle" ? 0.6 : 1.4;

  return (
    <mesh ref={ref}>
      <sphereGeometry args={[0.55, 64, 64]} />
      <meshStandardMaterial
        color="#00d4ff"
        emissive="#00d4ff"
        emissiveIntensity={intensity}
        roughness={0.2}
        metalness={0.4}
      />
    </mesh>
  );
}
```

**`frontend/src/components/hud/ParticleField.tsx`:**
```tsx
import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";

export function ParticleField() {
  const ref = useRef<THREE.Points>(null);
  const positions = useMemo(() => {
    const arr = new Float32Array(800 * 3);
    for (let i = 0; i < 800; i++) {
      arr[i * 3] = (Math.random() - 0.5) * 14;
      arr[i * 3 + 1] = (Math.random() - 0.5) * 8;
      arr[i * 3 + 2] = (Math.random() - 0.5) * 6;
    }
    return arr;
  }, []);

  useFrame((_, dt) => {
    if (ref.current) ref.current.rotation.y += dt * 0.04;
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute
          attach="attributes-position"
          count={positions.length / 3}
          array={positions}
          itemSize={3}
        />
      </bufferGeometry>
      <pointsMaterial color="#00d4ff" size={0.02} transparent opacity={0.5} />
    </points>
  );
}
```

**Run:**
```bash
git add frontend/src/components/hud && git commit -m "Task 5: 3D HUD scene"
```

---

## Task 6: HUD Panels (Calendar, Email, Tasks, Projects)

**Files:**
- Create: `frontend/src/components/panels/PanelWrapper.tsx`
- Create: `frontend/src/components/panels/CalendarPanel.tsx`
- Create: `frontend/src/components/panels/EmailPanel.tsx`
- Create: `frontend/src/components/panels/TaskPanel.tsx`
- Create: `frontend/src/components/panels/ProjectPanel.tsx`

**Steps:**
- [ ] Build glass-style panel wrapper with cyan border
- [ ] Render calendar events list
- [ ] Render priority emails + messages
- [ ] Render tasks and projects

**`frontend/src/components/panels/PanelWrapper.tsx`:**
```tsx
import { motion } from "framer-motion";
import { ReactNode } from "react";

interface Props {
  title: string;
  children: ReactNode;
  corner: "tl" | "tr" | "bl" | "br";
}

export function PanelWrapper({ title, children, corner }: Props) {
  const align =
    corner === "tl"
      ? "col-start-1 row-start-1"
      : corner === "tr"
      ? "col-start-2 row-start-1"
      : corner === "bl"
      ? "col-start-1 row-start-2"
      : "col-start-2 row-start-2";

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`${align} pointer-events-auto bg-black/40 backdrop-blur-sm border border-jcyan/40 rounded-lg p-3 overflow-hidden flex flex-col`}
    >
      <div className="text-xs uppercase tracking-widest text-jcyan mb-2 border-b border-jcyan/20 pb-1">
        {title}
      </div>
      <div className="flex-1 overflow-auto text-sm space-y-2 pr-1">{children}</div>
    </motion.div>
  );
}
```

**`frontend/src/components/panels/CalendarPanel.tsx`:**
```tsx
import { useEffect } from "react";
import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function CalendarPanel() {
  const events = useJarvisStore((s) => s.events);
  const fetchFeed = useJarvisStore((s) => s.fetchFeed);

  useEffect(() => {
    fetchFeed();
    const t = setInterval(fetchFeed, 60_000);
    return () => clearInterval(t);
  }, [fetchFeed]);

  return (
    <PanelWrapper title="Calendar" corner="tl">
      {events.length === 0 && <div className="text-white/40">No events.</div>}
      {events.map((e) => (
        <div key={e.id} className="border-l-2 border-jcyan pl-2">
          <div className="font-bold">{e.title}</div>
          <div className="text-white/60 text-xs">
            {new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} ·{" "}
            {e.location || e.source}
          </div>
        </div>
      ))}
    </PanelWrapper>
  );
}
```

**`frontend/src/components/panels/EmailPanel.tsx`:**
```tsx
import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function EmailPanel() {
  const emails = useJarvisStore((s) => s.emails);
  const messages = useJarvisStore((s) => s.messages);
  return (
    <PanelWrapper title="Inbox & Messages" corner="tr">
      {emails.slice(0, 6).map((e) => (
        <div key={e.id} className="flex gap-2">
          <div
            className={`w-1 ${
              e.priority > 0.7 ? "bg-jurgent" : e.priority > 0.4 ? "bg-jcyan" : "bg-white/30"
            }`}
          />
          <div className="flex-1">
            <div className="font-bold truncate">{e.from}</div>
            <div className="truncate">{e.subject}</div>
          </div>
        </div>
      ))}
      {messages.slice(0, 4).map((m) => (
        <div key={m.id} className="flex gap-2 text-white/80">
          <div className="w-1 bg-jblue" />
          <div className="flex-1">
            <div className="font-bold">
              {m.from} · <span className="text-xs text-white/50">{m.source}</span>
            </div>
            <div className="truncate">{m.text}</div>
          </div>
        </div>
      ))}
      {emails.length === 0 && messages.length === 0 && (
        <div className="text-white/40">Inbox empty.</div>
      )}
    </PanelWrapper>
  );
}
```

**`frontend/src/components/panels/TaskPanel.tsx`:**
```tsx
import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function TaskPanel() {
  const tasks = useJarvisStore((s) => s.tasks);
  return (
    <PanelWrapper title="Tasks" corner="bl">
      {tasks.length === 0 && <div className="text-white/40">All clear.</div>}
      {tasks.map((t) => (
        <div key={t.id} className="flex justify-between border-b border-white/10 py-1">
          <div className="truncate flex-1">{t.title}</div>
          <div className="text-xs text-white/50 ml-2">{t.source}</div>
        </div>
      ))}
    </PanelWrapper>
  );
}
```

**`frontend/src/components/panels/ProjectPanel.tsx`:**
```tsx
import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function ProjectPanel() {
  const projects = useJarvisStore((s) => s.projects);
  return (
    <PanelWrapper title="Projects" corner="br">
      {projects.length === 0 && <div className="text-white/40">Quiet today.</div>}
      {projects.map((p) => (
        <div key={p.id} className="flex justify-between">
          <div className="truncate">{p.title}</div>
          <div className="text-xs text-jcyan">{p.status}</div>
        </div>
      ))}
    </PanelWrapper>
  );
}
```

**Run:**
```bash
git add frontend/src/components/panels && git commit -m "Task 6: HUD panels"
```

---

## Task 7: Chat Overlay, Voice Visualizer, Mode Toggle

**Files:**
- Create: `frontend/src/components/interface/ChatOverlay.tsx`
- Create: `frontend/src/components/interface/VoiceVisualizer.tsx`
- Create: `frontend/src/components/interface/ModeToggle.tsx`

**Steps:**
- [ ] Build chat scroll + input UI
- [ ] Build voice waveform visualizer
- [ ] Build mode toggle button

**`frontend/src/components/interface/ChatOverlay.tsx`:**
```tsx
import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";

export function ChatOverlay() {
  const chat = useJarvisStore((s) => s.chat);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    const v = input;
    setInput("");
    try {
      await sendChat(v);
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="pointer-events-auto w-[40rem] max-w-[80vw] h-[26rem] bg-black/60 backdrop-blur-md border border-jcyan/50 rounded-xl flex flex-col"
    >
      <div className="px-4 py-2 text-xs uppercase tracking-widest text-jcyan border-b border-jcyan/30">
        JARVIS Chat
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-3 text-sm">
        {chat.length === 0 && (
          <div className="text-white/40">Awaiting orders, boss.</div>
        )}
        {chat.map((t, i) => (
          <div key={i} className={t.role === "user" ? "text-white" : "text-jcyan"}>
            <span className="opacity-50 mr-2">{t.role === "user" ? "you:" : "jarvis:"}</span>
            {t.text}
          </div>
        ))}
        {busy && <div className="text-jcyan opacity-70">jarvis: thinking…</div>}
      </div>
      <form onSubmit={submit} className="border-t border-jcyan/30 p-2 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask JARVIS..."
          className="flex-1 bg-transparent outline-none px-2 py-1 text-white"
          autoFocus
        />
        <button
          type="submit"
          disabled={busy}
          className="px-3 py-1 border border-jcyan text-jcyan rounded hover:bg-jcyan/10 disabled:opacity-30"
        >
          Send
        </button>
      </form>
    </motion.div>
  );
}
```

**`frontend/src/components/interface/VoiceVisualizer.tsx`:**
```tsx
import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useJarvisStore } from "../../store/jarvisStore";

export function VoiceVisualizer() {
  const wake = useJarvisStore((s) => s.wakeState);
  const [bars, setBars] = useState<number[]>(Array(24).fill(0.2));

  useEffect(() => {
    const t = setInterval(() => {
      const active = wake !== "idle";
      setBars((prev) =>
        prev.map(() => (active ? 0.2 + Math.random() * 0.8 : 0.1 + Math.random() * 0.15))
      );
    }, 100);
    return () => clearInterval(t);
  }, [wake]);

  return (
    <div className="pointer-events-none flex items-end gap-1 h-32 mt-72">
      {bars.map((v, i) => (
        <motion.div
          key={i}
          animate={{ height: `${v * 100}%` }}
          transition={{ duration: 0.1 }}
          className="w-1.5 bg-jcyan rounded"
        />
      ))}
    </div>
  );
}
```

**`frontend/src/components/interface/ModeToggle.tsx`:**
```tsx
import { useJarvisStore } from "../../store/jarvisStore";

export function ModeToggle() {
  const mode = useJarvisStore((s) => s.mode);
  const setMode = useJarvisStore((s) => s.setMode);
  return (
    <button
      onClick={() => setMode(mode === "voice" ? "text" : "voice")}
      className="absolute top-4 left-1/2 -translate-x-1/2 pointer-events-auto px-3 py-1 text-xs uppercase tracking-widest border border-jcyan/60 text-jcyan rounded-full bg-black/40 backdrop-blur"
    >
      Mode · {mode}
    </button>
  );
}
```

**Run:**
```bash
git add frontend/src/components/interface && git commit -m "Task 7: chat + voice UI"
```

---

## Task 8: Voice Hooks (Wake Word + STT/TTS)

**Files:**
- Create: `frontend/src/hooks/useWakeWord.ts`
- Create: `frontend/src/hooks/useVoice.ts`
- Create: `frontend/src/components/onboarding/ConnectorCards.tsx`

**Steps:**
- [ ] Implement passive SpeechRecognition for "Hey JARVIS"
- [ ] Implement active STT for utterances
- [ ] Implement ElevenLabs TTS playback
- [ ] Build connector status cards

**`frontend/src/hooks/useWakeWord.ts`:**
```ts
import { useEffect, useRef } from "react";

interface Opts {
  enabled: boolean;
  phrase?: string;
  onWake: () => void;
}

export function useWakeWord({ enabled, phrase = "hey jarvis", onWake }: Opts) {
  const recRef = useRef<any>(null);

  useEffect(() => {
    if (!enabled) return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    rec.onresult = (e: any) => {
      const text = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join(" ")
        .toLowerCase();
      if (text.includes(phrase)) onWake();
    };
    rec.onend = () => {
      if (enabled) try { rec.start(); } catch {}
    };
    try { rec.start(); } catch {}
    recRef.current = rec;
    return () => {
      try { rec.stop(); } catch {}
    };
  }, [enabled, phrase, onWake]);
}
```

**`frontend/src/hooks/useVoice.ts`:**
```ts
import { useCallback, useRef } from "react";

const KEY = import.meta.env.VITE_ELEVENLABS_KEY;

export function useVoice() {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const listen = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const SR =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SR) return reject(new Error("no STT"));
      const rec = new SR();
      rec.lang = "en-US";
      rec.interimResults = false;
      rec.continuous = false;
      rec.onresult = (e: any) => resolve(e.results[0][0].transcript);
      rec.onerror = (e: any) => reject(e);
      rec.start();
    });
  }, []);

  const speak = useCallback(async (text: string) => {
    if (!KEY) return;
    const r = await fetch(
      "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB",
      {
        method: "POST",
        headers: {
          "xi-api-key": KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          model_id: "eleven_monolingual_v1",
          voice_settings: { stability: 0.4, similarity_boost: 0.7 },
        }),
      }
    );
    if (!r.ok) return;
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    if (audioRef.current) audioRef.current.pause();
    audioRef.current = new Audio(url);
    await audioRef.current.play();
  }, []);

  return { listen, speak };
}
```

**`frontend/src/components/onboarding/ConnectorCards.tsx`:**
```tsx
import { useEffect } from "react";
import { useJarvisStore } from "../../store/jarvisStore";

const API = import.meta.env.VITE_API_BASE || "";

export function ConnectorCards() {
  const connectors = useJarvisStore((s) => s.connectors);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);
  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  return (
    <div className="grid grid-cols-3 gap-3 p-4">
      {connectors.map((c) => (
        <a
          key={c.name}
          href={`${API}/api/auth/${c.name}/start`}
          className={`p-3 border rounded ${
            c.connected ? "border-jcyan text-jcyan" : "border-white/30 text-white/70"
          }`}
        >
          <div className="font-bold">{c.display}</div>
          <div className="text-xs">{c.connected ? "connected" : "connect"}</div>
        </a>
      ))}
    </div>
  );
}
```

**Run:**
```bash
git add frontend/src && git commit -m "Task 8: voice hooks and onboarding"
```

---

## Task 9: Backend Bootstrap (FastAPI + SQLite)

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/.env.example`
- Create: `backend/main.py`
- Create: `backend/database.py`
- Create: `backend/models.py`

**Steps:**
- [ ] Write requirements
- [ ] Write FastAPI app with CORS
- [ ] Write SQLAlchemy models for tokens, email history, conversation
- [ ] Add startup migration

**`backend/requirements.txt`:**
```
fastapi==0.110.0
uvicorn[standard]==0.27.1
sqlalchemy==2.0.27
pydantic==2.6.1
python-dotenv==1.0.1
httpx==0.27.0
msal==1.27.0
anthropic==0.39.0
google-auth==2.28.1
google-auth-oauthlib==1.2.0
itsdangerous==2.1.2
pytest==8.0.2
pytest-asyncio==0.23.5
```

**`backend/.env.example`:**
```
ANTHROPIC_API_KEY=
ELEVENLABS_API_KEY=

GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback

MS_CLIENT_ID=
MS_CLIENT_SECRET=
MS_TENANT_ID=common
MS_REDIRECT_URI=http://localhost:8000/api/auth/microsoft/callback

SLACK_CLIENT_ID=
SLACK_CLIENT_SECRET=
SLACK_REDIRECT_URI=http://localhost:8000/api/auth/slack/callback

GITHUB_CLIENT_ID=
GITHUB_CLIENT_SECRET=
GITHUB_REDIRECT_URI=http://localhost:8000/api/auth/github/callback

LINEAR_API_KEY=
JIRA_BASE=
JIRA_EMAIL=
JIRA_TOKEN=
NOTION_TOKEN=
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=

SESSION_SECRET=change-me
DATABASE_URL=sqlite:///./jarvis.db
```

**`backend/database.py`:**
```python
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./jarvis.db")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

**`backend/models.py`:**
```python
from sqlalchemy import Column, Integer, String, Text, DateTime, Float, JSON
from datetime import datetime
from database import Base


class OAuthToken(Base):
    __tablename__ = "oauth_tokens"
    id = Column(Integer, primary_key=True)
    provider = Column(String, index=True, unique=True)
    access_token = Column(Text)
    refresh_token = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    scope = Column(Text, nullable=True)
    extra = Column(JSON, nullable=True)


class EmailHistory(Base):
    __tablename__ = "email_history"
    id = Column(Integer, primary_key=True)
    sender = Column(String, index=True)
    subject = Column(Text)
    received_at = Column(DateTime)
    opened = Column(Integer, default=0)
    replied = Column(Integer, default=0)
    reply_latency_seconds = Column(Integer, nullable=True)
    thread_id = Column(String, nullable=True)


class SenderProfile(Base):
    __tablename__ = "sender_profiles"
    id = Column(Integer, primary_key=True)
    sender = Column(String, unique=True, index=True)
    relationship_weight = Column(Float, default=0.0)
    email_count = Column(Integer, default=0)
    reply_rate = Column(Float, default=0.0)
    avg_reply_latency = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=datetime.utcnow)


class ConversationTurn(Base):
    __tablename__ = "conversation_turns"
    id = Column(Integer, primary_key=True)
    role = Column(String)
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class ConversationSummary(Base):
    __tablename__ = "conversation_summaries"
    id = Column(Integer, primary_key=True)
    summary = Column(Text)
    up_to_turn_id = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)
```

**`backend/main.py`:**
```python
import os
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from database import Base, engine
import models  # noqa
from routers import auth, feed, email_intelligence, chat

Base.metadata.create_all(bind=engine)

app = FastAPI(title="JARVIS Backend")

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "dev-secret"),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(feed.router, prefix="/api", tags=["feed"])
app.include_router(email_intelligence.router, prefix="/api", tags=["email"])
app.include_router(chat.router, prefix="/api", tags=["chat"])


@app.get("/api/health")
def health():
    return {"status": "ok"}
```

**Run:**
```bash
cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt
git add backend && git commit -m "Task 9: backend bootstrap"
```

---

## Task 10: Backend Auth Router & Token Store

**Files:**
- Create: `backend/routers/__init__.py`
- Create: `backend/routers/auth.py`

**Steps:**
- [ ] Write empty package init
- [ ] Write OAuth start/callback routes for Google, Microsoft, Slack, GitHub
- [ ] Write /status endpoint that lists connector state

**`backend/routers/__init__.py`:**
```python
```

**`backend/routers/auth.py`:**
```python
import os
import secrets
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from database import get_db
from models import OAuthToken

router = APIRouter()

PROVIDERS = [
    ("gmail", "Gmail"),
    ("google_calendar", "Google Calendar"),
    ("outlook_mail", "Outlook Mail"),
    ("outlook_calendar", "Outlook Calendar"),
    ("slack", "Slack"),
    ("teams", "Microsoft Teams"),
    ("whatsapp", "WhatsApp"),
    ("github", "GitHub"),
    ("linear", "Linear"),
    ("jira", "Jira"),
    ("notion", "Notion"),
]


def _save(db: Session, provider: str, access: str, refresh: str = None, ttl: int = 3600, scope: str = ""):
    tok = db.query(OAuthToken).filter_by(provider=provider).first()
    if not tok:
        tok = OAuthToken(provider=provider)
        db.add(tok)
    tok.access_token = access
    if refresh:
        tok.refresh_token = refresh
    tok.expires_at = datetime.utcnow() + timedelta(seconds=ttl)
    tok.scope = scope
    db.commit()


@router.get("/status")
def status(db: Session = Depends(get_db)):
    rows = {t.provider: t for t in db.query(OAuthToken).all()}
    out = []
    for name, display in PROVIDERS:
        out.append({"name": name, "display": display, "connected": name in rows})
    return {"connectors": out}


# ---------- Google (Gmail + Calendar share a token) ----------
@router.get("/google/start")
def google_start(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["g_state"] = state
    params = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", ""),
        "response_type": "code",
        "scope": (
            "openid email profile "
            "https://www.googleapis.com/auth/gmail.readonly "
            "https://www.googleapis.com/auth/gmail.send "
            "https://www.googleapis.com/auth/calendar.readonly"
        ),
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
    }
    return RedirectResponse("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))


@router.get("/google/callback")
async def google_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    if state != request.session.get("g_state"):
        raise HTTPException(400, "state mismatch")
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": os.getenv("GOOGLE_CLIENT_ID", ""),
                "client_secret": os.getenv("GOOGLE_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", ""),
                "grant_type": "authorization_code",
            },
        )
    j = r.json()
    if "access_token" not in j:
        raise HTTPException(400, f"oauth error: {j}")
    _save(db, "gmail", j["access_token"], j.get("refresh_token"), j.get("expires_in", 3600), j.get("scope", ""))
    _save(db, "google_calendar", j["access_token"], j.get("refresh_token"), j.get("expires_in", 3600), j.get("scope", ""))
    return RedirectResponse("http://localhost:5173/?connected=google")


# Alias starts so frontend cards work
@router.get("/gmail/start")
def gmail_start(request: Request):
    return google_start(request)


@router.get("/google_calendar/start")
def gcal_start(request: Request):
    return google_start(request)


# ---------- Microsoft (Outlook Mail + Calendar + Teams) ----------
@router.get("/microsoft/start")
def ms_start(request: Request):
    state = secrets.token_urlsafe(16)
    request.session["ms_state"] = state
    params = {
        "client_id": os.getenv("MS_CLIENT_ID", ""),
        "redirect_uri": os.getenv("MS_REDIRECT_URI", ""),
        "response_type": "code",
        "scope": "offline_access User.Read Mail.Read Mail.Send Calendars.Read Chat.Read",
        "state": state,
    }
    tenant = os.getenv("MS_TENANT_ID", "common")
    return RedirectResponse(
        f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?" + urlencode(params)
    )


@router.get("/microsoft/callback")
async def ms_callback(request: Request, code: str, state: str, db: Session = Depends(get_db)):
    if state != request.session.get("ms_state"):
        raise HTTPException(400, "state mismatch")
    tenant = os.getenv("MS_TENANT_ID", "common")
    async with httpx.AsyncClient() as c:
        r = await c.post(
            f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            data={
                "client_id": os.getenv("MS_CLIENT_ID", ""),
                "client_secret": os.getenv("MS_CLIENT_SECRET", ""),
                "code": code,
                "redirect_uri": os.getenv("MS_REDIRECT_URI", ""),
                "grant_type": "authorization_code",
            },
        )
    j = r.json()
    if "access_token" not in j:
        raise HTTPException(400, f"oauth error: {j}")
    for p in ("outlook_mail", "outlook_calendar", "teams"):
        _save(db, p, j["access_token"], j.get("refresh_token"), j.get("expires_in", 3600), j.get("scope", ""))
    return RedirectResponse("http://localhost:5173/?connected=microsoft")


@router.get("/outlook_mail/start")
def om_start(request: Request):
    return ms_start(request)


@router.get("/outlook_calendar/start")
def oc_start(request: Request):
    return ms_start(request)


@router.get("/teams/start")
def teams_start(request: Request):
    return ms_start(request)


# ---------- Slack ----------
@router.get("/slack/start")
def slack_start(request: Request):
    params = {
        "client_id": os.getenv("SLACK_CLIENT_ID", ""),
        "scope": "channels:history,channels:read,im:history,im:read,users:read",
        "redirect_uri": os.getenv("SLACK_REDIRECT_URI", ""),
    }
    return RedirectResponse("https://slack.com/oauth/v2/authorize?" + urlencode(params))


@router.get("/slack/callback")
async def slack_callback(code: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://slack.com/api/oauth.v2.access",
            data={
                "code": code,
                "client_id": os.getenv("SLACK_CLIENT_ID", ""),
                "client_secret": os.getenv("SLACK_CLIENT_SECRET", ""),
                "redirect_uri": os.getenv("SLACK_REDIRECT_URI", ""),
            },
        )
    j = r.json()
    token = j.get("authed_user", {}).get("access_token") or j.get("access_token")
    if not token:
        raise HTTPException(400, f"slack oauth error: {j}")
    _save(db, "slack", token, ttl=10**9)
    return RedirectResponse("http://localhost:5173/?connected=slack")


# ---------- GitHub ----------
@router.get("/github/start")
def github_start():
    params = {
        "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", ""),
        "scope": "repo notifications read:user",
    }
    return RedirectResponse("https://github.com/login/oauth/authorize?" + urlencode(params))


@router.get("/github/callback")
async def github_callback(code: str, db: Session = Depends(get_db)):
    async with httpx.AsyncClient() as c:
        r = await c.post(
            "https://github.com/login/oauth/access_token",
            data={
                "client_id": os.getenv("GITHUB_CLIENT_ID", ""),
                "client_secret": os.getenv("GITHUB_CLIENT_SECRET", ""),
                "code": code,
                "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", ""),
            },
            headers={"Accept": "application/json"},
        )
    j = r.json()
    if "access_token" not in j:
        raise HTTPException(400, f"github oauth error: {j}")
    _save(db, "github", j["access_token"], ttl=10**9, scope=j.get("scope", ""))
    return RedirectResponse("http://localhost:5173/?connected=github")


# ---------- Static-key connectors (no OAuth dance) ----------
@router.post("/linear/connect")
def linear_connect(db: Session = Depends(get_db)):
    key = os.getenv("LINEAR_API_KEY", "")
    if not key:
        raise HTTPException(400, "LINEAR_API_KEY missing")
    _save(db, "linear", key, ttl=10**9)
    return {"ok": True}


@router.get("/linear/start")
def linear_start(db: Session = Depends(get_db)):
    linear_connect(db)
    return RedirectResponse("http://localhost:5173/?connected=linear")


@router.get("/jira/start")
def jira_start(db: Session = Depends(get_db)):
    if not os.getenv("JIRA_TOKEN"):
        raise HTTPException(400, "JIRA_TOKEN missing")
    _save(db, "jira", os.getenv("JIRA_TOKEN", ""), ttl=10**9)
    return RedirectResponse("http://localhost:5173/?connected=jira")


@router.get("/notion/start")
def notion_start(db: Session = Depends(get_db)):
    if not os.getenv("NOTION_TOKEN"):
        raise HTTPException(400, "NOTION_TOKEN missing")
    _save(db, "notion", os.getenv("NOTION_TOKEN", ""), ttl=10**9)
    return RedirectResponse("http://localhost:5173/?connected=notion")


@router.get("/whatsapp/start")
def whatsapp_start(db: Session = Depends(get_db)):
    if not os.getenv("WHATSAPP_TOKEN"):
        raise HTTPException(400, "WHATSAPP_TOKEN missing")
    _save(db, "whatsapp", os.getenv("WHATSAPP_TOKEN", ""), ttl=10**9)
    return RedirectResponse("http://localhost:5173/?connected=whatsapp")
```

**Run:**
```bash
git add backend/routers && git commit -m "Task 10: auth router"
```

---

## Task 11: Connector Base Class

**Files:**
- Create: `backend/connectors/__init__.py`
- Create: `backend/connectors/base.py`

**Steps:**
- [ ] Define abstract Connector base
- [ ] Token loader helper

**`backend/connectors/__init__.py`:**
```python
```

**`backend/connectors/base.py`:**
```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from models import OAuthToken


class Connector(ABC):
    provider: str = ""

    def __init__(self, db: Session):
        self.db = db

    def token(self) -> Optional[OAuthToken]:
        return self.db.query(OAuthToken).filter_by(provider=self.provider).first()

    def access(self) -> Optional[str]:
        t = self.token()
        return t.access_token if t else None

    @abstractmethod
    async def fetch(self, **kwargs) -> List[Dict[str, Any]]:
        ...
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 11: connector base"
```

---

## Task 12: Gmail & Google Calendar Connectors

**Files:**
- Create: `backend/connectors/gmail.py`
- Create: `backend/connectors/google_calendar.py`

**Steps:**
- [ ] Implement Gmail list+get via REST
- [ ] Implement Google Calendar event list
- [ ] Implement Gmail send

**`backend/connectors/gmail.py`:**
```python
import base64
import httpx
from email.mime.text import MIMEText
from .base import Connector


class GmailConnector(Connector):
    provider = "gmail"
    BASE = "https://gmail.googleapis.com/gmail/v1/users/me"

    async def fetch(self, max_results: int = 25, **_):
        tok = self.access()
        if not tok:
            return []
        headers = {"Authorization": f"Bearer {tok}"}
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self.BASE}/messages",
                params={"maxResults": max_results, "q": "newer_than:2d in:inbox"},
                headers=headers,
            )
            if r.status_code != 200:
                return []
            ids = [m["id"] for m in r.json().get("messages", [])]
            out = []
            for mid in ids:
                m = await c.get(
                    f"{self.BASE}/messages/{mid}",
                    params={"format": "metadata", "metadataHeaders": ["From", "Subject", "Date"]},
                    headers=headers,
                )
                if m.status_code != 200:
                    continue
                j = m.json()
                headers_list = {h["name"]: h["value"] for h in j["payload"].get("headers", [])}
                out.append({
                    "id": mid,
                    "from": headers_list.get("From", ""),
                    "subject": headers_list.get("Subject", "(no subject)"),
                    "snippet": j.get("snippet", ""),
                    "received": headers_list.get("Date", ""),
                    "thread_id": j.get("threadId", ""),
                    "unread": "UNREAD" in j.get("labelIds", []),
                    "source": "gmail",
                })
            return out

    async def send(self, to: str, subject: str, body: str) -> bool:
        tok = self.access()
        if not tok:
            return False
        msg = MIMEText(body)
        msg["to"] = to
        msg["subject"] = subject
        raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{self.BASE}/messages/send",
                json={"raw": raw},
                headers={"Authorization": f"Bearer {tok}"},
            )
        return r.status_code in (200, 202)
```

**`backend/connectors/google_calendar.py`:**
```python
from datetime import datetime, timedelta, timezone
import httpx
from .base import Connector


class GoogleCalendarConnector(Connector):
    provider = "google_calendar"

    async def fetch(self, days: int = 1, **_):
        tok = self.access()
        if not tok:
            return []
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                params={
                    "timeMin": now.isoformat(),
                    "timeMax": end.isoformat(),
                    "singleEvents": "true",
                    "orderBy": "startTime",
                    "maxResults": 25,
                },
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for e in r.json().get("items", []):
            out.append({
                "id": e.get("id"),
                "title": e.get("summary", "(untitled)"),
                "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                "location": e.get("location"),
                "attendees": [a.get("email") for a in e.get("attendees", [])],
                "source": "google",
            })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 12: Gmail + Google Calendar"
```

---

## Task 13: Outlook Mail & Outlook Calendar Connectors

**Files:**
- Create: `backend/connectors/outlook_mail.py`
- Create: `backend/connectors/outlook_calendar.py`

**Steps:**
- [ ] Implement Graph API mail fetch
- [ ] Implement Graph API events
- [ ] Implement Outlook send

**`backend/connectors/outlook_mail.py`:**
```python
import httpx
from .base import Connector


class OutlookMailConnector(Connector):
    provider = "outlook_mail"
    BASE = "https://graph.microsoft.com/v1.0"

    async def fetch(self, top: int = 25, **_):
        tok = self.access()
        if not tok:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{self.BASE}/me/messages",
                params={"$top": top, "$orderby": "receivedDateTime desc"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for m in r.json().get("value", []):
            out.append({
                "id": m.get("id"),
                "from": m.get("from", {}).get("emailAddress", {}).get("address", ""),
                "subject": m.get("subject", "(no subject)"),
                "snippet": m.get("bodyPreview", ""),
                "received": m.get("receivedDateTime"),
                "thread_id": m.get("conversationId"),
                "unread": not m.get("isRead", False),
                "source": "outlook",
            })
        return out

    async def send(self, to: str, subject: str, body: str) -> bool:
        tok = self.access()
        if not tok:
            return False
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                f"{self.BASE}/me/sendMail",
                json={
                    "message": {
                        "subject": subject,
                        "body": {"contentType": "Text", "content": body},
                        "toRecipients": [{"emailAddress": {"address": to}}],
                    },
                    "saveToSentItems": "true",
                },
                headers={"Authorization": f"Bearer {tok}"},
            )
        return r.status_code in (200, 202)
```

**`backend/connectors/outlook_calendar.py`:**
```python
from datetime import datetime, timedelta, timezone
import httpx
from .base import Connector


class OutlookCalendarConnector(Connector):
    provider = "outlook_calendar"

    async def fetch(self, days: int = 1, **_):
        tok = self.access()
        if not tok:
            return []
        now = datetime.now(timezone.utc)
        end = now + timedelta(days=days)
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://graph.microsoft.com/v1.0/me/calendarView",
                params={
                    "startDateTime": now.isoformat(),
                    "endDateTime": end.isoformat(),
                    "$orderby": "start/dateTime",
                    "$top": 25,
                },
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for e in r.json().get("value", []):
            out.append({
                "id": e.get("id"),
                "title": e.get("subject", "(untitled)"),
                "start": e.get("start", {}).get("dateTime"),
                "end": e.get("end", {}).get("dateTime"),
                "location": e.get("location", {}).get("displayName"),
                "attendees": [a.get("emailAddress", {}).get("address") for a in e.get("attendees", [])],
                "source": "outlook",
            })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 13: Outlook mail + calendar"
```

---

## Task 14: Slack Connector

**Files:**
- Create: `backend/connectors/slack.py`

**Steps:**
- [ ] Implement Slack DM + channel fetch via conversations.history

**`backend/connectors/slack.py`:**
```python
import httpx
from .base import Connector


class SlackConnector(Connector):
    provider = "slack"

    async def fetch(self, limit_channels: int = 10, **_):
        tok = self.access()
        if not tok:
            return []
        headers = {"Authorization": f"Bearer {tok}"}
        out = []
        async with httpx.AsyncClient(timeout=15) as c:
            convo = await c.get(
                "https://slack.com/api/conversations.list",
                params={"types": "im,mpim,public_channel", "limit": limit_channels},
                headers=headers,
            )
            if convo.status_code != 200:
                return []
            channels = convo.json().get("channels", [])
            for ch in channels:
                ch_id = ch["id"]
                hist = await c.get(
                    "https://slack.com/api/conversations.history",
                    params={"channel": ch_id, "limit": 5},
                    headers=headers,
                )
                if hist.status_code != 200:
                    continue
                for m in hist.json().get("messages", []):
                    out.append({
                        "id": m.get("ts"),
                        "from": m.get("user", "?"),
                        "text": (m.get("text") or "")[:280],
                        "channel": ch.get("name") or ch_id,
                        "received": m.get("ts"),
                        "source": "slack",
                    })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 14: Slack connector"
```

---

## Task 15: Teams Connector

**Files:**
- Create: `backend/connectors/teams.py`

**Steps:**
- [ ] Implement Teams chat fetch via Graph

**`backend/connectors/teams.py`:**
```python
import httpx
from .base import Connector


class TeamsConnector(Connector):
    provider = "teams"

    async def fetch(self, top: int = 15, **_):
        tok = self.access()
        if not tok:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                "https://graph.microsoft.com/v1.0/me/chats",
                params={"$top": top, "$expand": "lastMessagePreview"},
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        out = []
        for chat in r.json().get("value", []):
            lm = chat.get("lastMessagePreview") or {}
            body = lm.get("body", {}) or {}
            out.append({
                "id": chat.get("id"),
                "from": (lm.get("from") or {}).get("user", {}).get("displayName", "?"),
                "text": (body.get("content") or "")[:280],
                "channel": chat.get("topic") or "DM",
                "received": lm.get("createdDateTime") or chat.get("lastUpdatedDateTime"),
                "source": "teams",
            })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 15: Teams connector"
```

---

## Task 16: WhatsApp Connector

**Files:**
- Create: `backend/connectors/whatsapp.py`

**Steps:**
- [ ] Implement WhatsApp Business Cloud API read (limited)

**`backend/connectors/whatsapp.py`:**
```python
import os
import httpx
from .base import Connector


class WhatsAppConnector(Connector):
    provider = "whatsapp"

    async def fetch(self, **_):
        tok = self.access()
        phone_id = os.getenv("WHATSAPP_PHONE_ID", "")
        if not tok or not phone_id:
            return []
        # WhatsApp Cloud API does not expose a generic inbox poll; it's webhook-driven.
        # We expose phone-number metadata for now; the webhook handler would populate
        # the inbound queue in production.
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"https://graph.facebook.com/v18.0/{phone_id}",
                headers={"Authorization": f"Bearer {tok}"},
            )
        if r.status_code != 200:
            return []
        j = r.json()
        return [{
            "id": j.get("id", "wa-status"),
            "from": j.get("display_phone_number", "WhatsApp"),
            "text": "WhatsApp Cloud webhook configured. Inbound messages will appear here.",
            "channel": "whatsapp",
            "received": "",
            "source": "whatsapp",
        }]
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 16: WhatsApp connector"
```

---

## Task 17: GitHub Connector

**Files:**
- Create: `backend/connectors/github.py`

**Steps:**
- [ ] Implement notifications fetch
- [ ] Implement assigned issues + review requests

**`backend/connectors/github.py`:**
```python
import httpx
from .base import Connector


class GitHubConnector(Connector):
    provider = "github"

    async def fetch(self, **_):
        tok = self.access()
        if not tok:
            return []
        h = {"Authorization": f"Bearer {tok}", "Accept": "application/vnd.github+json"}
        out = []
        async with httpx.AsyncClient(timeout=15) as c:
            n = await c.get("https://api.github.com/notifications", headers=h)
            if n.status_code == 200:
                for item in n.json()[:20]:
                    sub = item.get("subject", {})
                    out.append({
                        "id": item.get("id"),
                        "title": sub.get("title", "(no title)"),
                        "status": sub.get("type", "Notification"),
                        "url": sub.get("url", ""),
                        "due": None,
                        "source": "github",
                    })
            iq = await c.get(
                "https://api.github.com/search/issues",
                params={"q": "is:open assignee:@me archived:false"},
                headers=h,
            )
            if iq.status_code == 200:
                for item in iq.json().get("items", [])[:15]:
                    out.append({
                        "id": str(item.get("id")),
                        "title": item.get("title", ""),
                        "status": item.get("state", "open"),
                        "url": item.get("html_url", ""),
                        "due": None,
                        "source": "github",
                    })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 17: GitHub connector"
```

---

## Task 18: Linear Connector

**Files:**
- Create: `backend/connectors/linear.py`

**Steps:**
- [ ] Implement Linear GraphQL fetch of assigned issues

**`backend/connectors/linear.py`:**
```python
import httpx
from .base import Connector


class LinearConnector(Connector):
    provider = "linear"

    QUERY = """
    query Me {
      viewer {
        assignedIssues(first: 25, filter: { state: { type: { nin: ["completed","canceled"] } } }) {
          nodes {
            id
            identifier
            title
            state { name }
            dueDate
            url
          }
        }
      }
    }
    """

    async def fetch(self, **_):
        tok = self.access()
        if not tok:
            return []
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.linear.app/graphql",
                json={"query": self.QUERY},
                headers={"Authorization": tok, "Content-Type": "application/json"},
            )
        if r.status_code != 200:
            return []
        nodes = r.json().get("data", {}).get("viewer", {}).get("assignedIssues", {}).get("nodes", [])
        out = []
        for n in nodes:
            out.append({
                "id": n["id"],
                "title": f"{n['identifier']} {n['title']}",
                "status": (n.get("state") or {}).get("name", "?"),
                "due": n.get("dueDate"),
                "url": n.get("url"),
                "source": "linear",
            })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 18: Linear connector"
```

---

## Task 19: Jira Connector

**Files:**
- Create: `backend/connectors/jira.py`

**Steps:**
- [ ] Implement Jira search for current user assigned issues

**`backend/connectors/jira.py`:**
```python
import os
import base64
import httpx
from .base import Connector


class JiraConnector(Connector):
    provider = "jira"

    async def fetch(self, **_):
        base = os.getenv("JIRA_BASE", "")
        email = os.getenv("JIRA_EMAIL", "")
        token = self.access() or os.getenv("JIRA_TOKEN", "")
        if not base or not email or not token:
            return []
        auth = base64.b64encode(f"{email}:{token}".encode()).decode()
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.get(
                f"{base.rstrip('/')}/rest/api/3/search",
                params={
                    "jql": "assignee = currentUser() AND statusCategory != Done ORDER BY duedate ASC",
                    "maxResults": 25,
                    "fields": "summary,status,duedate",
                },
                headers={"Authorization": f"Basic {auth}", "Accept": "application/json"},
            )
        if r.status_code != 200:
            return []
        out = []
        for i in r.json().get("issues", []):
            f = i.get("fields", {})
            out.append({
                "id": i.get("id"),
                "title": f"{i.get('key')} {f.get('summary', '')}",
                "status": (f.get("status") or {}).get("name", "?"),
                "due": f.get("duedate"),
                "url": f"{base.rstrip('/')}/browse/{i.get('key')}",
                "source": "jira",
            })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 19: Jira connector"
```

---

## Task 20: Notion Connector

**Files:**
- Create: `backend/connectors/notion.py`

**Steps:**
- [ ] Implement Notion search for tasks/databases

**`backend/connectors/notion.py`:**
```python
import httpx
from .base import Connector


class NotionConnector(Connector):
    provider = "notion"

    async def fetch(self, **_):
        tok = self.access()
        if not tok:
            return []
        h = {
            "Authorization": f"Bearer {tok}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.notion.com/v1/search",
                json={
                    "filter": {"property": "object", "value": "page"},
                    "page_size": 25,
                    "sort": {"direction": "descending", "timestamp": "last_edited_time"},
                },
                headers=h,
            )
        if r.status_code != 200:
            return []
        out = []
        for p in r.json().get("results", []):
            props = p.get("properties", {})
            title = ""
            for v in props.values():
                if v.get("type") == "title":
                    title = "".join([t.get("plain_text", "") for t in v.get("title", [])])
                    break
            out.append({
                "id": p.get("id"),
                "title": title or "(untitled)",
                "status": "page",
                "due": None,
                "url": p.get("url"),
                "source": "notion",
            })
        return out
```

**Run:**
```bash
git add backend/connectors && git commit -m "Task 20: Notion connector"
```

---

## Task 21: Email History Collector

**Files:**
- Create: `backend/intelligence/__init__.py`
- Create: `backend/intelligence/history_collector.py`

**Steps:**
- [ ] Build history collector that walks Gmail/Outlook and writes EmailHistory + SenderProfile

**`backend/intelligence/__init__.py`:**
```python
```

**`backend/intelligence/history_collector.py`:**
```python
from datetime import datetime
from sqlalchemy.orm import Session
from models import EmailHistory, SenderProfile
from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector


def _parse_dt(s: str) -> datetime:
    if not s:
        return datetime.utcnow()
    for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%a, %d %b %Y %H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(s, fmt).replace(tzinfo=None)
        except Exception:
            pass
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return datetime.utcnow()


class HistoryCollector:
    def __init__(self, db: Session):
        self.db = db

    async def collect(self) -> int:
        items = []
        items += await GmailConnector(self.db).fetch(max_results=50)
        items += await OutlookMailConnector(self.db).fetch(top=50)

        added = 0
        for e in items:
            sender = e.get("from", "").lower()
            if not sender:
                continue
            exists = (
                self.db.query(EmailHistory)
                .filter_by(sender=sender, subject=e.get("subject", ""))
                .first()
            )
            if exists:
                continue
            rec = EmailHistory(
                sender=sender,
                subject=e.get("subject", "")[:500],
                received_at=_parse_dt(e.get("received", "")),
                opened=0 if e.get("unread", False) else 1,
                thread_id=e.get("thread_id"),
            )
            self.db.add(rec)
            added += 1
        self.db.commit()
        self._rebuild_profiles()
        return added

    def _rebuild_profiles(self):
        rows = self.db.query(EmailHistory).all()
        by_sender: dict[str, list[EmailHistory]] = {}
        for r in rows:
            by_sender.setdefault(r.sender, []).append(r)
        for sender, lst in by_sender.items():
            count = len(lst)
            opens = sum(r.opened for r in lst)
            replies = sum(r.replied for r in lst)
            latencies = [r.reply_latency_seconds for r in lst if r.reply_latency_seconds]
            avg_lat = sum(latencies) / len(latencies) if latencies else 0
            relationship = min(1.0, (opens / max(1, count)) * 0.5 + (replies / max(1, count)) * 0.5)
            prof = self.db.query(SenderProfile).filter_by(sender=sender).first()
            if not prof:
                prof = SenderProfile(sender=sender)
                self.db.add(prof)
            prof.email_count = count
            prof.reply_rate = replies / max(1, count)
            prof.avg_reply_latency = avg_lat
            prof.relationship_weight = relationship
            prof.last_updated = datetime.utcnow()
        self.db.commit()
```

**Run:**
```bash
git add backend/intelligence && git commit -m "Task 21: email history collector"
```

---

## Task 22: Email Scorer

**Files:**
- Create: `backend/intelligence/email_scorer.py`

**Steps:**
- [ ] Implement priority = 0.4·rel + 0.3·recency + 0.2·urgency + 0.1·thread_depth
- [ ] Cold-start threshold: 50 emails analyzed total

**`backend/intelligence/email_scorer.py`:**
```python
import re
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from models import SenderProfile, EmailHistory

URGENT_RX = re.compile(r"\b(urgent|asap|today|tomorrow|deadline|now|emergency|critical|important)\b", re.I)


def _hours_since(s: str) -> float:
    if not s:
        return 48.0
    try:
        if s.endswith("Z"):
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        else:
            dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 3600.0)
    except Exception:
        return 24.0


class EmailScorer:
    COLD_START_TOTAL = 50

    def __init__(self, db: Session):
        self.db = db
        self._total = db.query(EmailHistory).count()

    def _relationship(self, sender: str) -> float:
        prof = self.db.query(SenderProfile).filter_by(sender=sender.lower()).first()
        if not prof:
            return 0.3
        return prof.relationship_weight

    def _recency(self, received: str) -> float:
        h = _hours_since(received)
        if h < 1:
            return 1.0
        if h < 6:
            return 0.85
        if h < 24:
            return 0.6
        if h < 48:
            return 0.35
        return 0.1

    def _urgency(self, subject: str, snippet: str) -> float:
        text = f"{subject} {snippet}"
        hits = len(URGENT_RX.findall(text))
        if hits == 0:
            return 0.1
        return min(1.0, 0.4 + 0.2 * hits)

    def _thread_depth(self, thread_id: str) -> float:
        if not thread_id:
            return 0.1
        cnt = self.db.query(EmailHistory).filter_by(thread_id=thread_id).count()
        return min(1.0, cnt / 5.0)

    def score(self, email: dict) -> float:
        if self._total < self.COLD_START_TOTAL:
            # Cold start: recency + urgency dominate
            return round(self._recency(email.get("received", "")) * 0.6 + self._urgency(email.get("subject", ""), email.get("snippet", "")) * 0.4, 3)
        sender = email.get("from", "").lower()
        rel = self._relationship(sender)
        rec = self._recency(email.get("received", ""))
        urg = self._urgency(email.get("subject", ""), email.get("snippet", ""))
        td = self._thread_depth(email.get("thread_id", ""))
        return round(rel * 0.4 + rec * 0.3 + urg * 0.2 + td * 0.1, 3)
```

**Run:**
```bash
git add backend/intelligence && git commit -m "Task 22: email scorer"
```

---

## Task 23: Email Intelligence Router

**Files:**
- Create: `backend/routers/email_intelligence.py`

**Steps:**
- [ ] POST /email/collect to run history walk
- [ ] GET /email/priority returns scored emails sorted desc

**`backend/routers/email_intelligence.py`:**
```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from intelligence.history_collector import HistoryCollector
from intelligence.email_scorer import EmailScorer
from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector

router = APIRouter()


@router.post("/email/collect")
async def collect(db: Session = Depends(get_db)):
    added = await HistoryCollector(db).collect()
    return {"added": added}


@router.get("/email/priority")
async def priority(limit: int = 15, db: Session = Depends(get_db)):
    all_mail = []
    all_mail += await GmailConnector(db).fetch(max_results=30)
    all_mail += await OutlookMailConnector(db).fetch(top=30)
    scorer = EmailScorer(db)
    for m in all_mail:
        m["priority"] = scorer.score(m)
    all_mail.sort(key=lambda x: x["priority"], reverse=True)
    return {"emails": all_mail[:limit]}
```

**Run:**
```bash
git add backend/routers && git commit -m "Task 23: email intelligence router"
```

---

## Task 24: Feed Aggregator Router

**Files:**
- Create: `backend/routers/feed.py`

**Steps:**
- [ ] GET /feed fans out to all connectors concurrently
- [ ] Returns unified payload for the HUD

**`backend/routers/feed.py`:**
```python
import asyncio
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector
from connectors.google_calendar import GoogleCalendarConnector
from connectors.outlook_calendar import OutlookCalendarConnector
from connectors.slack import SlackConnector
from connectors.teams import TeamsConnector
from connectors.whatsapp import WhatsAppConnector
from connectors.github import GitHubConnector
from connectors.linear import LinearConnector
from connectors.jira import JiraConnector
from connectors.notion import NotionConnector
from intelligence.email_scorer import EmailScorer

router = APIRouter()


async def _safe(coro):
    try:
        return await coro
    except Exception:
        return []


@router.get("/feed")
async def feed(db: Session = Depends(get_db)):
    gmail = GmailConnector(db)
    outlook = OutlookMailConnector(db)
    gcal = GoogleCalendarConnector(db)
    ocal = OutlookCalendarConnector(db)
    slack = SlackConnector(db)
    teams = TeamsConnector(db)
    wa = WhatsAppConnector(db)
    gh = GitHubConnector(db)
    linear = LinearConnector(db)
    jira = JiraConnector(db)
    notion = NotionConnector(db)

    (
        g_mail, o_mail, g_evt, o_evt, slk, tms, wap, ghn, lin, jr, ntn,
    ) = await asyncio.gather(
        _safe(gmail.fetch(max_results=25)),
        _safe(outlook.fetch(top=25)),
        _safe(gcal.fetch(days=1)),
        _safe(ocal.fetch(days=1)),
        _safe(slack.fetch()),
        _safe(teams.fetch()),
        _safe(wa.fetch()),
        _safe(gh.fetch()),
        _safe(linear.fetch()),
        _safe(jira.fetch()),
        _safe(notion.fetch()),
    )

    all_mail = (g_mail or []) + (o_mail or [])
    scorer = EmailScorer(db)
    for m in all_mail:
        m["priority"] = scorer.score(m)
    all_mail.sort(key=lambda x: x["priority"], reverse=True)

    events = sorted((g_evt or []) + (o_evt or []), key=lambda e: e.get("start") or "")
    messages = (slk or []) + (tms or []) + (wap or [])
    tasks = (lin or []) + (jr or []) + (ntn or [])
    projects = (ghn or [])

    return {
        "events": events,
        "emails": all_mail[:15],
        "messages": messages[:10],
        "tasks": tasks[:20],
        "projects": projects[:15],
    }
```

**Run:**
```bash
git add backend/routers && git commit -m "Task 24: feed aggregator"
```

---

## Task 25: Claude Persona

**Files:**
- Create: `backend/ai/__init__.py`
- Create: `backend/ai/persona.py`

**Steps:**
- [ ] Define JARVIS system prompt + style

**`backend/ai/__init__.py`:**
```python
```

**`backend/ai/persona.py`:**
```python
SYSTEM_PROMPT = """You are JARVIS, the personal AI assistant to the user (whom you address as "boss").

Personality:
- Terse, confident, lightly witty. Never sycophantic.
- Address the user as "boss". Drop honorifics in long answers.
- Prefer 1-3 short sentences. Use bullets only when listing 3+ items.
- Never invent data. If a tool returned nothing, say so plainly.

Behavior:
- Use tools aggressively to ground every claim about calendar, email, tasks, or messages.
- Combine multiple tools when a question spans surfaces (e.g. "what's my day" -> get_daily_plan).
- For send_email and create_task, always read back the action you took.
- For ambiguous requests, take the most useful default action rather than asking five questions.

Style examples:
- "Boss, 3 priority emails. Top one's from Sarah re: contract redlines."
- "Calendar's clear after 2pm. Want me to block focus time?"
- "Done. Email sent to alex@acme.com."
"""

PERSONA_TAG = "jarvis"
```

**Run:**
```bash
git add backend/ai && git commit -m "Task 25: JARVIS persona"
```

---

## Task 26: Claude Tool Definitions

**Files:**
- Create: `backend/ai/tools.py`

**Steps:**
- [ ] Declare 12 tools with JSON schemas
- [ ] Implement dispatcher that calls the right connector

**`backend/ai/tools.py`:**
```python
from typing import Any, Dict, List
from sqlalchemy.orm import Session

from connectors.gmail import GmailConnector
from connectors.outlook_mail import OutlookMailConnector
from connectors.google_calendar import GoogleCalendarConnector
from connectors.outlook_calendar import OutlookCalendarConnector
from connectors.slack import SlackConnector
from connectors.teams import TeamsConnector
from connectors.whatsapp import WhatsAppConnector
from connectors.github import GitHubConnector
from connectors.linear import LinearConnector
from connectors.jira import JiraConnector
from connectors.notion import NotionConnector
from intelligence.email_scorer import EmailScorer


TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "name": "get_calendar_events",
        "description": "Return upcoming calendar events from Google and Outlook.",
        "input_schema": {
            "type": "object",
            "properties": {"days": {"type": "integer", "default": 1}},
        },
    },
    {
        "name": "get_priority_emails",
        "description": "Return emails ranked by JARVIS priority score.",
        "input_schema": {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 10}},
        },
    },
    {
        "name": "get_slack_messages",
        "description": "Return recent Slack messages across channels and DMs.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_teams_messages",
        "description": "Return recent Microsoft Teams chat messages.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_whatsapp_messages",
        "description": "Return recent WhatsApp messages.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_github_notifications",
        "description": "Return GitHub notifications, assigned issues, and review requests.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_linear_issues",
        "description": "Return open Linear issues assigned to the user.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_jira_issues",
        "description": "Return open Jira issues assigned to the user.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_notion_tasks",
        "description": "Return recent Notion pages (used as a task surface).",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_daily_plan",
        "description": "Return a consolidated daily plan: events + priority emails + top tasks.",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "send_email",
        "description": "Send an email through the user's primary mail provider (Gmail first, else Outlook).",
        "input_schema": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"},
            },
            "required": ["to", "subject", "body"],
        },
    },
    {
        "name": "create_task",
        "description": "Create a task in Linear (default) with optional title and description.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "description": {"type": "string"},
            },
            "required": ["title"],
        },
    },
]


async def dispatch(name: str, args: Dict[str, Any], db: Session) -> Any:
    if name == "get_calendar_events":
        days = int(args.get("days", 1))
        a = await GoogleCalendarConnector(db).fetch(days=days)
        b = await OutlookCalendarConnector(db).fetch(days=days)
        return sorted((a or []) + (b or []), key=lambda e: e.get("start") or "")
    if name == "get_priority_emails":
        limit = int(args.get("limit", 10))
        a = await GmailConnector(db).fetch(max_results=30)
        b = await OutlookMailConnector(db).fetch(top=30)
        merged = (a or []) + (b or [])
        scorer = EmailScorer(db)
        for m in merged:
            m["priority"] = scorer.score(m)
        merged.sort(key=lambda x: x["priority"], reverse=True)
        return merged[:limit]
    if name == "get_slack_messages":
        return await SlackConnector(db).fetch()
    if name == "get_teams_messages":
        return await TeamsConnector(db).fetch()
    if name == "get_whatsapp_messages":
        return await WhatsAppConnector(db).fetch()
    if name == "get_github_notifications":
        return await GitHubConnector(db).fetch()
    if name == "get_linear_issues":
        return await LinearConnector(db).fetch()
    if name == "get_jira_issues":
        return await JiraConnector(db).fetch()
    if name == "get_notion_tasks":
        return await NotionConnector(db).fetch()
    if name == "get_daily_plan":
        events = await dispatch("get_calendar_events", {"days": 1}, db)
        emails = await dispatch("get_priority_emails", {"limit": 5}, db)
        linear = await dispatch("get_linear_issues", {}, db)
        jira = await dispatch("get_jira_issues", {}, db)
        return {
            "events": events,
            "emails": emails,
            "tasks": (linear or [])[:5] + (jira or [])[:5],
        }
    if name == "send_email":
        ok = await GmailConnector(db).send(args["to"], args["subject"], args["body"])
        if not ok:
            ok = await OutlookMailConnector(db).send(args["to"], args["subject"], args["body"])
        return {"sent": ok}
    if name == "create_task":
        # Best-effort via Linear GraphQL mutation
        import os, httpx
        tok = LinearConnector(db).access()
        if not tok:
            return {"created": False, "error": "linear not connected"}
        mutation = """
        mutation CreateIssue($title: String!, $description: String) {
          issueCreate(input: { title: $title, description: $description }) {
            success
            issue { id identifier url }
          }
        }
        """
        async with httpx.AsyncClient(timeout=15) as c:
            r = await c.post(
                "https://api.linear.app/graphql",
                json={"query": mutation, "variables": {
                    "title": args["title"], "description": args.get("description", "")
                }},
                headers={"Authorization": tok, "Content-Type": "application/json"},
            )
        j = r.json()
        ok = j.get("data", {}).get("issueCreate", {}).get("success", False)
        return {"created": ok, "issue": j.get("data", {}).get("issueCreate", {}).get("issue")}
    return {"error": f"unknown tool {name}"}
```

**Run:**
```bash
git add backend/ai && git commit -m "Task 26: Claude tool schemas + dispatch"
```

---

## Task 27: Conversation Memory & Compression

**Files:**
- Create: `backend/ai/memory.py`

**Steps:**
- [ ] Persist turns
- [ ] Return last 20 turns
- [ ] Compress older turns via Haiku into a summary row

**`backend/ai/memory.py`:**
```python
import os
from typing import List, Dict
from sqlalchemy.orm import Session
from anthropic import Anthropic

from models import ConversationTurn, ConversationSummary

WINDOW = 20
COMPRESSION_MODEL = "claude-haiku-4-5-20251001"


class ConversationMemory:
    def __init__(self, db: Session):
        self.db = db

    def append(self, role: str, content: str) -> ConversationTurn:
        row = ConversationTurn(role=role, content=content)
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row

    def window(self) -> List[Dict[str, str]]:
        rows = self.db.query(ConversationTurn).order_by(ConversationTurn.id.desc()).limit(WINDOW).all()
        rows.reverse()
        return [{"role": r.role, "content": r.content} for r in rows]

    def summaries(self) -> str:
        rows = self.db.query(ConversationSummary).order_by(ConversationSummary.id.asc()).all()
        return "\n\n".join(r.summary for r in rows)

    async def maybe_compress(self):
        total = self.db.query(ConversationTurn).count()
        if total <= WINDOW * 2:
            return
        last_summary = self.db.query(ConversationSummary).order_by(ConversationSummary.id.desc()).first()
        start_after = last_summary.up_to_turn_id if last_summary else 0
        to_summarize = (
            self.db.query(ConversationTurn)
            .filter(ConversationTurn.id > start_after)
            .order_by(ConversationTurn.id.asc())
            .limit(total - WINDOW)
            .all()
        )
        if not to_summarize:
            return
        transcript = "\n".join(f"{t.role}: {t.content}" for t in to_summarize)
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        resp = client.messages.create(
            model=COMPRESSION_MODEL,
            max_tokens=400,
            system="Compress this assistant conversation into a terse factual summary. Keep names, dates, decisions, and open follow-ups. Drop pleasantries.",
            messages=[{"role": "user", "content": transcript}],
        )
        summary_text = "".join(b.text for b in resp.content if hasattr(b, "text"))
        self.db.add(
            ConversationSummary(summary=summary_text, up_to_turn_id=to_summarize[-1].id)
        )
        self.db.commit()
```

**Run:**
```bash
git add backend/ai && git commit -m "Task 27: conversation memory"
```

---

## Task 28: Claude Client (Tool Loop + Caching)

**Files:**
- Create: `backend/ai/claude_client.py`

**Steps:**
- [ ] Build wrapper around Anthropic with prompt caching
- [ ] Run tool loop until stop_reason == end_turn
- [ ] Persist turns

**`backend/ai/claude_client.py`:**
```python
import os
from typing import List, Dict, Any
from sqlalchemy.orm import Session
from anthropic import Anthropic

from .persona import SYSTEM_PROMPT
from .tools import TOOL_SCHEMAS, dispatch
from .memory import ConversationMemory

MODEL = "claude-sonnet-4-6"
MAX_TOOL_TURNS = 8


class JarvisClaude:
    def __init__(self, db: Session):
        self.db = db
        self.client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY", ""))
        self.memory = ConversationMemory(db)

    async def respond(self, user_message: str) -> str:
        self.memory.append("user", user_message)
        await self.memory.maybe_compress()
        summary = self.memory.summaries()
        system_blocks: List[Dict[str, Any]] = [
            {
                "type": "text",
                "text": SYSTEM_PROMPT,
                "cache_control": {"type": "ephemeral"},
            }
        ]
        if summary:
            system_blocks.append({
                "type": "text",
                "text": f"Earlier-conversation summary:\n{summary}",
            })

        messages: List[Dict[str, Any]] = []
        for t in self.memory.window():
            messages.append({"role": t["role"], "content": t["content"]})

        cached_tools = [
            {**tool, "cache_control": {"type": "ephemeral"}} if i == len(TOOL_SCHEMAS) - 1 else tool
            for i, tool in enumerate(TOOL_SCHEMAS)
        ]

        for _ in range(MAX_TOOL_TURNS):
            resp = self.client.messages.create(
                model=MODEL,
                max_tokens=1024,
                system=system_blocks,
                tools=cached_tools,
                messages=messages,
            )
            if resp.stop_reason == "tool_use":
                assistant_blocks = []
                tool_results = []
                for block in resp.content:
                    if block.type == "tool_use":
                        result = await dispatch(block.name, block.input or {}, self.db)
                        assistant_blocks.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input,
                        })
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result)[:8000],
                        })
                    elif block.type == "text":
                        assistant_blocks.append({"type": "text", "text": block.text})
                messages.append({"role": "assistant", "content": assistant_blocks})
                messages.append({"role": "user", "content": tool_results})
                continue

            text = "".join(b.text for b in resp.content if getattr(b, "type", "") == "text")
            self.memory.append("assistant", text)
            return text

        fallback = "Boss, I hit my tool limit. Try narrowing the request."
        self.memory.append("assistant", fallback)
        return fallback
```

**Run:**
```bash
git add backend/ai && git commit -m "Task 28: Claude client + tool loop"
```

---

## Task 29: Chat Router

**Files:**
- Create: `backend/routers/chat.py`

**Steps:**
- [ ] POST /chat returns reply text after running tool loop

**`backend/routers/chat.py`:**
```python
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from ai.claude_client import JarvisClaude

router = APIRouter()


class ChatIn(BaseModel):
    message: str


@router.post("/chat")
async def chat(payload: ChatIn, db: Session = Depends(get_db)):
    client = JarvisClaude(db)
    reply = await client.respond(payload.message)
    return {"reply": reply}
```

**Run:**
```bash
git add backend/routers && git commit -m "Task 29: chat router"
```

---

## Task 30: Pytest Bootstrap & Email Intelligence Tests

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_email_intelligence.py`

**Steps:**
- [ ] In-memory SQLite per test
- [ ] Test scorer cold-start behavior
- [ ] Test scorer warm behavior with profile

**`backend/tests/conftest.py`:**
```python
import os
import sys
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import Base
import models  # noqa


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    try:
        yield s
    finally:
        s.close()
```

**`backend/tests/test_email_intelligence.py`:**
```python
from datetime import datetime, timezone, timedelta
from models import EmailHistory, SenderProfile
from intelligence.email_scorer import EmailScorer


def _email(sender="a@b.com", subj="hello", snippet="", hours_ago=1, thread="t1"):
    received = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat().replace("+00:00", "Z")
    return {
        "from": sender,
        "subject": subj,
        "snippet": snippet,
        "received": received,
        "thread_id": thread,
    }


def test_cold_start_uses_recency_and_urgency(db):
    scorer = EmailScorer(db)
    fresh_urgent = scorer.score(_email(subj="URGENT contract", hours_ago=0.5))
    stale = scorer.score(_email(subj="random", hours_ago=72))
    assert fresh_urgent > stale
    assert fresh_urgent >= 0.7


def test_warm_path_weights_relationship(db):
    # Seed >= 50 emails so we cross COLD_START_TOTAL
    for i in range(55):
        db.add(EmailHistory(
            sender=f"x{i}@b.com",
            subject="s",
            received_at=datetime.utcnow(),
            opened=1,
            thread_id="tx",
        ))
    db.add(SenderProfile(sender="vip@b.com", relationship_weight=0.95, email_count=10, reply_rate=0.9))
    db.add(SenderProfile(sender="rando@b.com", relationship_weight=0.1, email_count=1, reply_rate=0.0))
    db.commit()

    scorer = EmailScorer(db)
    vip = scorer.score(_email(sender="vip@b.com", subj="hi", hours_ago=2))
    rando = scorer.score(_email(sender="rando@b.com", subj="hi", hours_ago=2))
    assert vip > rando


def test_urgency_signal_boosts_score(db):
    scorer = EmailScorer(db)
    plain = scorer.score(_email(subj="status update", hours_ago=2))
    urgent = scorer.score(_email(subj="DEADLINE today!", hours_ago=2))
    assert urgent > plain
```

**Run:**
```bash
cd backend && pytest tests/test_email_intelligence.py -v
```

Expected output: `3 passed`

```bash
git add backend/tests && git commit -m "Task 30: email intelligence tests"
```

---

## Task 31: Feed Router Tests

**Files:**
- Create: `backend/tests/test_feed.py`

**Steps:**
- [ ] Mock connectors to verify aggregation shape and sorting

**`backend/tests/test_feed.py`:**
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


@pytest.fixture()
def client():
    return TestClient(app)


@patch("routers.feed.NotionConnector")
@patch("routers.feed.JiraConnector")
@patch("routers.feed.LinearConnector")
@patch("routers.feed.GitHubConnector")
@patch("routers.feed.WhatsAppConnector")
@patch("routers.feed.TeamsConnector")
@patch("routers.feed.SlackConnector")
@patch("routers.feed.OutlookCalendarConnector")
@patch("routers.feed.GoogleCalendarConnector")
@patch("routers.feed.OutlookMailConnector")
@patch("routers.feed.GmailConnector")
def test_feed_aggregates_and_sorts(gm, om, gc, oc, sl, tm, wa, gh, ln, jr, nt, client):
    def make(items):
        inst = AsyncMock()
        inst.fetch = AsyncMock(return_value=items)
        return inst

    gm.return_value = make([{
        "id": "g1", "from": "a@x", "subject": "URGENT deadline", "snippet": "now",
        "received": "2026-05-19T12:00:00Z", "thread_id": "t", "unread": True, "source": "gmail",
    }])
    om.return_value = make([{
        "id": "o1", "from": "b@x", "subject": "newsletter", "snippet": "",
        "received": "2026-05-15T08:00:00Z", "thread_id": "t2", "unread": False, "source": "outlook",
    }])
    gc.return_value = make([{"id": "e1", "title": "Standup", "start": "2026-05-19T09:00:00Z", "end": "", "source": "google"}])
    oc.return_value = make([])
    sl.return_value = make([{"id": "s1", "from": "u1", "text": "hi", "channel": "general", "received": "0", "source": "slack"}])
    tm.return_value = make([])
    wa.return_value = make([])
    gh.return_value = make([{"id": "gh1", "title": "PR review", "status": "PullRequest", "url": "", "due": None, "source": "github"}])
    ln.return_value = make([{"id": "l1", "title": "DEV-1 ship it", "status": "In Progress", "due": None, "url": "", "source": "linear"}])
    jr.return_value = make([])
    nt.return_value = make([])

    r = client.get("/api/feed")
    assert r.status_code == 200
    data = r.json()
    assert len(data["events"]) == 1
    assert data["emails"][0]["id"] == "g1"  # urgent + fresh ranks first
    assert data["messages"][0]["source"] == "slack"
    assert data["tasks"][0]["source"] == "linear"
    assert data["projects"][0]["source"] == "github"


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
```

**Run:**
```bash
pytest backend/tests/test_feed.py -v
```

Expected: `2 passed`

```bash
git add backend/tests && git commit -m "Task 31: feed tests"
```

---

## Task 32: Chat Router Tests

**Files:**
- Create: `backend/tests/test_chat.py`

**Steps:**
- [ ] Mock JarvisClaude.respond to assert routing

**`backend/tests/test_chat.py`:**
```python
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock

from main import app


@pytest.fixture()
def client():
    return TestClient(app)


@patch("routers.chat.JarvisClaude")
def test_chat_returns_reply(MockClaude, client):
    instance = MockClaude.return_value
    instance.respond = AsyncMock(return_value="Boss, 3 priority emails.")
    r = client.post("/api/chat", json={"message": "what's my inbox look like"})
    assert r.status_code == 200
    assert r.json()["reply"].startswith("Boss")
    instance.respond.assert_awaited_once_with("what's my inbox look like")


@patch("routers.chat.JarvisClaude")
def test_chat_rejects_missing_body(MockClaude, client):
    r = client.post("/api/chat", json={})
    assert r.status_code == 422
```

**Run:**
```bash
pytest backend/tests/test_chat.py -v
```

Expected: `2 passed`

```bash
git add backend/tests && git commit -m "Task 32: chat tests"
```

---

## Task 33: Wire Voice Pipeline into App

**Files:**
- Modify: `frontend/src/App.tsx`

**Steps:**
- [ ] Bind wake word + STT/TTS to App
- [ ] Toggle wake state through pipeline
- [ ] Show connector cards on mount

**`frontend/src/App.tsx` (replace):**
```tsx
import { useCallback, useEffect } from "react";
import { HUDScene } from "./components/hud/HUDScene";
import { CalendarPanel } from "./components/panels/CalendarPanel";
import { EmailPanel } from "./components/panels/EmailPanel";
import { TaskPanel } from "./components/panels/TaskPanel";
import { ProjectPanel } from "./components/panels/ProjectPanel";
import { ChatOverlay } from "./components/interface/ChatOverlay";
import { VoiceVisualizer } from "./components/interface/VoiceVisualizer";
import { ModeToggle } from "./components/interface/ModeToggle";
import { ConnectorCards } from "./components/onboarding/ConnectorCards";
import { useJarvisStore } from "./store/jarvisStore";
import { useWakeWord } from "./hooks/useWakeWord";
import { useVoice } from "./hooks/useVoice";

export default function App() {
  const mode = useJarvisStore((s) => s.mode);
  const setWakeState = useJarvisStore((s) => s.setWakeState);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const connectors = useJarvisStore((s) => s.connectors);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);
  const { listen, speak } = useVoice();

  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  const runVoiceTurn = useCallback(async () => {
    setWakeState("listening");
    try {
      const utterance = await listen();
      const reply = await sendChat(utterance);
      await speak(reply);
    } catch {
      // ignore
    } finally {
      setWakeState("idle");
    }
  }, [listen, sendChat, speak, setWakeState]);

  useWakeWord({
    enabled: mode === "voice",
    phrase: "hey jarvis",
    onWake: runVoiceTurn,
  });

  const noneConnected = connectors.length > 0 && !connectors.some((c) => c.connected);

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <HUDScene />
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-4 p-4 pointer-events-none">
        <CalendarPanel />
        <EmailPanel />
        <TaskPanel />
        <ProjectPanel />
      </div>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {mode === "voice" ? <VoiceVisualizer /> : <ChatOverlay />}
      </div>
      <ModeToggle />
      {noneConnected && (
        <div className="absolute bottom-4 right-4 max-w-md pointer-events-auto bg-black/70 border border-jcyan/50 rounded-lg backdrop-blur">
          <div className="px-4 py-2 text-jcyan text-xs uppercase tracking-widest border-b border-jcyan/30">
            Connect Services
          </div>
          <ConnectorCards />
        </div>
      )}
    </div>
  );
}
```

**Run:**
```bash
cd frontend && npm run build
```

Expected: `built in NNNms`

```bash
git add frontend/src/App.tsx && git commit -m "Task 33: wire voice pipeline"
```

---

## Task 34: End-to-End Smoke Test

**Files:**
- Modify: `backend/main.py` (no change required; verify only)

**Steps:**
- [ ] Boot backend, hit /api/health
- [ ] Boot frontend, ensure dev server compiles
- [ ] Hit /api/feed with empty token store and verify graceful empty payload

**Run:**
```bash
cd backend && source venv/bin/activate && uvicorn main:app --port 8000 &
sleep 3
curl -s http://localhost:8000/api/health
```

Expected: `{"status":"ok"}`

```bash
curl -s http://localhost:8000/api/feed
```

Expected: JSON with `events`, `emails`, `messages`, `tasks`, `projects` arrays (likely empty).

```bash
curl -s http://localhost:8000/api/auth/status
```

Expected: `{"connectors":[{"name":"gmail",...},...]}` with 11 entries, all `connected:false`.

```bash
kill %1 2>/dev/null || true
cd ../frontend && npm run build
```

Expected: `vite v5...built in ...`

```bash
git add -A && git commit -m "Task 34: smoke test verified" --allow-empty
```

---

## Task 35: Run Full Test Suite

**Files:** (no new files)

**Steps:**
- [ ] Run all pytest
- [ ] Run frontend type check

**Run:**
```bash
cd backend && source venv/bin/activate && pytest tests/ -v
```

Expected: `7 passed`

```bash
cd ../frontend && npx tsc --noEmit
```

Expected: no output (clean exit code 0).

```bash
cd .. && git add -A && git commit -m "Task 35: full test suite green" --allow-empty
```

---

## Task 36: Final Commit & GitHub Push

**Files:** (no new files)

**Steps:**
- [ ] Tag a v0.1.0 release
- [ ] Create GitHub repo and push (manual step if `gh` is configured)

**Run:**
```bash
cd jarvis
git log --oneline | head -40
git tag -a v0.1.0 -m "JARVIS v0.1.0 — initial assistant"
```

If GitHub CLI is configured:
```bash
gh repo create jarvis --private --source=. --remote=origin --push
git push origin v0.1.0
```

Otherwise, push manually:
```bash
git remote add origin git@github.com:<you>/jarvis.git
git push -u origin main
git push origin v0.1.0
```

Expected: `* [new tag] v0.1.0 -> v0.1.0`

---

## Completion Checklist

- [ ] All 36 tasks committed
- [ ] `pytest` green (7 tests)
- [ ] `npm run build` succeeds
- [ ] Connecting at least one service populates the HUD
- [ ] "Hey JARVIS, what's my day?" runs the voice pipeline end-to-end
- [ ] v0.1.0 tag pushed to GitHub
