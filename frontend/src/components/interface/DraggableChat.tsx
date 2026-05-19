import { FormEvent, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";

const MIN_W = 320;
const MIN_H = 220;
const DEFAULT_W = 560;
const DEFAULT_H = 380;

export function DraggableChat() {
  const chat = useJarvisStore((s) => s.chat);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [size, setSize] = useState({ w: DEFAULT_W, h: DEFAULT_H });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const constraintRef = useRef<HTMLDivElement>(null);
  const resizing = useRef(false);
  const resizeStart = useRef({ x: 0, y: 0, w: DEFAULT_W, h: DEFAULT_H });

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, busy]);

  // Keyboard shortcut: Cmd+K / Ctrl+K focuses input
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setMinimized(false);
        setTimeout(() => document.getElementById("jarvis-input")?.focus(), 50);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    const v = input;
    setInput("");
    try { await sendChat(v); } finally { setBusy(false); }
  };

  // Resize pointer handlers
  const onResizeStart = (e: React.PointerEvent) => {
    e.stopPropagation();
    e.preventDefault();
    resizing.current = true;
    resizeStart.current = { x: e.clientX, y: e.clientY, w: size.w, h: size.h };

    const onMove = (ev: PointerEvent) => {
      if (!resizing.current) return;
      const dw = ev.clientX - resizeStart.current.x;
      const dh = ev.clientY - resizeStart.current.y;
      setSize({
        w: Math.max(MIN_W, resizeStart.current.w + dw),
        h: Math.max(MIN_H, resizeStart.current.h + dh),
      });
    };
    const onUp = () => {
      resizing.current = false;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onUp);
    };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };

  return (
    // Full-screen constraint layer (invisible, pointer-events-none for backdrop)
    <div ref={constraintRef} className="absolute inset-0 pointer-events-none">
      <motion.div
        drag
        dragConstraints={constraintRef}
        dragMomentum={false}
        dragElastic={0}
        dragListener={!resizing.current}
        // Start roughly centered
        initial={{ x: 0, y: 0 }}
        style={{ width: size.w, height: minimized ? "auto" : size.h }}
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto bg-black/70 backdrop-blur-md border border-jcyan/50 rounded-xl flex flex-col shadow-2xl shadow-black/60"
      >
        {/* ── Header / drag handle ── */}
        <div className="flex items-center gap-2 px-4 py-2.5 border-b border-jcyan/30 cursor-grab active:cursor-grabbing select-none shrink-0 rounded-t-xl">
          {/* Traffic lights */}
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setMinimized((v) => !v)}
              className="w-3 h-3 rounded-full bg-yellow-400/80 hover:bg-yellow-400 transition-colors"
              title={minimized ? "Expand" : "Minimize"}
            />
            <button
              onClick={() => setSize({ w: DEFAULT_W, h: DEFAULT_H })}
              className="w-3 h-3 rounded-full bg-green-400/80 hover:bg-green-400 transition-colors"
              title="Reset size"
            />
          </div>

          <span className="flex-1 text-center text-xs uppercase tracking-widest text-jcyan font-bold">
            J·A·R·V·I·S
          </span>

          {/* Wake state indicator */}
          <WakeIndicator />
        </div>

        {/* ── Messages ── */}
        {!minimized && (
          <>
            <div className="flex-1 overflow-auto p-4 space-y-3 text-sm min-h-0">
              {chat.length === 0 && (
                <div className="flex flex-col items-center justify-center h-full gap-3 text-center">
                  <div className="text-4xl opacity-20">⚡</div>
                  <div className="text-white/30 text-xs tracking-wide">
                    Awaiting orders, boss.<br />
                    <span className="text-jcyan/40">⌘K</span> to focus anytime.
                  </div>
                </div>
              )}
              {chat.map((t, i) => (
                <div key={i} className={`flex gap-2 ${t.role === "user" ? "justify-end" : "justify-start"}`}>
                  {t.role === "assistant" && (
                    <div className="w-5 h-5 rounded-full bg-jcyan/20 border border-jcyan/40 flex items-center justify-center text-jcyan text-[10px] shrink-0 mt-0.5">
                      J
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] px-3 py-2 rounded-xl text-sm leading-relaxed ${
                      t.role === "user"
                        ? "bg-jcyan/15 border border-jcyan/30 text-white rounded-tr-sm"
                        : "bg-white/5 border border-white/10 text-white/90 rounded-tl-sm"
                    }`}
                  >
                    {t.text}
                  </div>
                  {t.role === "user" && (
                    <div className="w-5 h-5 rounded-full bg-white/10 border border-white/20 flex items-center justify-center text-white/60 text-[10px] shrink-0 mt-0.5">
                      U
                    </div>
                  )}
                </div>
              ))}
              {busy && (
                <div className="flex gap-2 justify-start">
                  <div className="w-5 h-5 rounded-full bg-jcyan/20 border border-jcyan/40 flex items-center justify-center text-jcyan text-[10px] shrink-0">
                    J
                  </div>
                  <div className="px-3 py-2 rounded-xl rounded-tl-sm bg-white/5 border border-white/10">
                    <ThinkingDots />
                  </div>
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* ── Input ── */}
            <form
              onSubmit={submit}
              className="border-t border-jcyan/30 p-3 flex gap-2 shrink-0 rounded-b-xl"
            >
              <input
                id="jarvis-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask JARVIS anything…"
                disabled={busy}
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-jcyan/50 focus:bg-jcyan/5 transition-all disabled:opacity-40"
              />
              <button
                type="submit"
                disabled={busy || !input.trim()}
                className="px-4 py-2 border border-jcyan/60 text-jcyan rounded-lg text-sm font-bold hover:bg-jcyan/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                ↑
              </button>
            </form>
          </>
        )}

        {/* ── Resize handle (bottom-right corner) ── */}
        {!minimized && (
          <div
            onPointerDown={onResizeStart}
            className="absolute bottom-0 right-0 w-5 h-5 cursor-nwse-resize flex items-center justify-center opacity-30 hover:opacity-70 transition-opacity"
            title="Drag to resize"
          >
            <svg width="10" height="10" viewBox="0 0 10 10" fill="currentColor" className="text-jcyan">
              <path d="M0 10 L10 0 L10 10 Z" opacity="0.5" />
              <path d="M4 10 L10 4 L10 10 Z" />
            </svg>
          </div>
        )}
      </motion.div>
    </div>
  );
}

function WakeIndicator() {
  const wakeState = useJarvisStore((s) => s.wakeState);
  const COLOR = {
    idle: "bg-white/20",
    listening: "bg-green-400",
    processing: "bg-yellow-400",
    responding: "bg-jcyan",
  }[wakeState];
  const LABEL = {
    idle: "Idle",
    listening: "Listening",
    processing: "Thinking",
    responding: "Speaking",
  }[wakeState];
  return (
    <div className="flex items-center gap-1.5">
      <span className={`w-2 h-2 rounded-full ${COLOR} ${wakeState !== "idle" ? "animate-pulse" : ""}`} />
      <span className="text-white/30 text-[10px] uppercase tracking-wider">{LABEL}</span>
    </div>
  );
}

function ThinkingDots() {
  return (
    <div className="flex items-center gap-1 py-0.5">
      {[0, 1, 2].map((i) => (
        <motion.div
          key={i}
          className="w-1.5 h-1.5 rounded-full bg-jcyan/60"
          animate={{ y: [0, -4, 0] }}
          transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </div>
  );
}
