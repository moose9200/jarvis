import { FormEvent, useEffect, useRef, useState } from "react";
import { motion, useDragControls } from "framer-motion";
import { FilesAPI, type FileRow } from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";
import type { ToolEvent } from "../../types";
import { InlineChatControls } from "./InlineChatControls";

const MIN_W = 320;
const MIN_H = 220;
const DEFAULT_W = 560;
const DEFAULT_H = 380;

export function DraggableChat() {
  const chat = useJarvisStore((s) => s.chat);
  const streamChat = useJarvisStore((s) => s.streamChat);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [streamingText, setStreamingText] = useState("");
  const [streamingTools, setStreamingTools] = useState<ToolEvent[]>([]);
  const [lastUsage, setLastUsage] = useState<any>(null);
  const [attachments, setAttachments] = useState<FileRow[]>([]);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const addToast = useJarvisStore((s) => s.addToast);
  const [minimized, setMinimized] = useState(false);
  const [size, setSize] = useState({ w: DEFAULT_W, h: DEFAULT_H });
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const constraintRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  // framer-motion drag controls — drag only starts from the header handle
  const dragControls = useDragControls();

  // Resize tracking (completely isolated from drag)
  const resizeStartRef = useRef({ x: 0, y: 0, w: DEFAULT_W, h: DEFAULT_H });

  // Auto-scroll on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chat, busy]);

  // ⌘K / Ctrl+K: focus input
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
    setStreamingText("");
    setStreamingTools([]);
    setLastUsage(null);
    const v = input;
    setInput("");

    const controller = new AbortController();
    abortRef.current = controller;

    const fileIds = attachments.map((a) => a.id);

    try {
      await streamChat(
        v,
        {
          onToken: (delta) => setStreamingText((s) => s + delta),
          onToolStart: (name) =>
            setStreamingTools((ts) => [...ts, { name, status: "running" }]),
          onToolEnd: (name, ok) =>
            setStreamingTools((ts) => {
              const next = [...ts];
              for (let i = next.length - 1; i >= 0; i--) {
                if (next[i].name === name && next[i].status === "running") {
                  next[i] = { name, status: ok ? "ok" : "fail" };
                  break;
                }
              }
              return next;
            }),
          onCorrection: (corrected, violations) => {
            // Backend guardrail caught an action claim with no matching
            // tool call. Replace the streamed (lying) text with the
            // honesty-corrected version and surface a toast so the user
            // knows JARVIS auto-flagged the issue.
            setStreamingText(corrected);
            const phrases = violations.map((v) => `"${v.phrase}"`).join("; ");
            addToast({
              type: "error",
              message: `JARVIS caught a false claim: ${phrases}. Action was NOT executed.`,
              duration: 8000,
            });
          },
          onDone:  (usage) => setLastUsage(usage),
          onError: (err)   => setStreamingText((s) => s + `\n\n[stream error: ${err}]`),
        },
        controller.signal,
        fileIds,
      );
    } finally {
      abortRef.current = null;
      setStreamingText("");   // assistant message now in chat history
      setStreamingTools([]);
      setAttachments([]);     // attachments consumed by this turn
      setBusy(false);
    }
  };

  const cancelStream = () => {
    abortRef.current?.abort();
    abortRef.current = null;
  };

  const uploadFiles = async (fileList: FileList | File[] | null) => {
    if (!fileList) return;
    setUploading(true);
    try {
      for (const f of Array.from(fileList)) {
        try {
          const row = await FilesAPI.upload(f);
          setAttachments((a) => [...a, row]);
          addToast({ type: "success", message: `Attached ${row.filename}` });
        } catch (e) {
          addToast({ type: "error", message: `Upload failed: ${(e as Error).message}` });
        }
      }
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    if (e.dataTransfer?.files?.length) uploadFiles(e.dataTransfer.files);
  };

  const removeAttachment = (id: number) => {
    setAttachments((a) => a.filter((f) => f.id !== id));
    FilesAPI.remove(id).catch(() => {/* best-effort */});
  };

  // Resize: starts from the corner handle, entirely independent of drag
  const onResizePointerDown = (e: React.PointerEvent) => {
    e.stopPropagation(); // do NOT let this bubble to the motion.div
    e.currentTarget.setPointerCapture(e.pointerId); // capture on the handle element itself

    resizeStartRef.current = {
      x: e.clientX,
      y: e.clientY,
      w: size.w,
      h: size.h,
    };
  };

  const onResizePointerMove = (e: React.PointerEvent) => {
    if (!(e.buttons & 1)) return; // only while primary button held
    const { x, y, w, h } = resizeStartRef.current;
    setSize({
      w: Math.max(MIN_W, w + e.clientX - x),
      h: Math.max(MIN_H, h + e.clientY - y),
    });
  };

  const onResizePointerUp = (e: React.PointerEvent) => {
    e.currentTarget.releasePointerCapture(e.pointerId);
  };

  return (
    // Full-screen constraint layer
    <div ref={constraintRef} className="absolute inset-0 pointer-events-none">
      <motion.div
        drag
        dragControls={dragControls}
        dragListener={false}       // CRITICAL: only start drag via dragControls.start()
        dragConstraints={constraintRef}
        dragMomentum={false}
        dragElastic={0}
        initial={{ x: 0, y: 0 }}
        style={{ width: size.w, height: minimized ? "auto" : size.h }}
        className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 pointer-events-auto bg-black/70 backdrop-blur-md border border-jcyan/50 rounded-xl flex flex-col shadow-2xl shadow-black/60"
      >
        {/* ── Header / drag handle ── */}
        <div
          onPointerDown={(e) => {
            // Only start drag from the header bar (not buttons inside it)
            if ((e.target as HTMLElement).closest("button")) return;
            dragControls.start(e);
          }}
          className="flex items-center gap-2 px-4 py-2.5 border-b border-jcyan/30 cursor-grab active:cursor-grabbing select-none shrink-0 rounded-t-xl bg-black/20"
        >
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
                  <div className="max-w-[80%] flex flex-col gap-1">
                    {t.role === "assistant" && t.tools && t.tools.length > 0 && (
                      <ToolPills tools={t.tools} />
                    )}
                    {t.role === "assistant" && t.corrections && t.corrections.length > 0 && (
                      <GuardrailBanner corrections={t.corrections} />
                    )}
                    {(t.text || t.role === "user") && (
                      <div
                        className={`px-3 py-2 rounded-xl text-sm leading-relaxed whitespace-pre-wrap break-words ${
                          t.role === "user"
                            ? "bg-jcyan/15 border border-jcyan/30 text-white rounded-tr-sm"
                            : "bg-white/5 border border-white/10 text-white/90 rounded-tl-sm"
                        }`}
                      >
                        {t.text}
                      </div>
                    )}
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
                  <div className="w-5 h-5 rounded-full bg-jcyan/20 border border-jcyan/40 flex items-center justify-center text-jcyan text-[10px] shrink-0 mt-0.5">
                    J
                  </div>
                  <div className="max-w-[80%] flex flex-col gap-1">
                    {streamingTools.length > 0 && <ToolPills tools={streamingTools} />}
                    <div className="px-3 py-2 rounded-xl rounded-tl-sm bg-white/5 border border-white/10 text-white/90 text-sm leading-relaxed whitespace-pre-wrap break-words">
                      {streamingText || <ThinkingDots />}
                      <span className="inline-block w-1.5 h-3 bg-jcyan/60 animate-pulse ml-0.5 align-middle" />
                    </div>
                  </div>
                </div>
              )}
              {!busy && lastUsage && (
                <div className="text-[10px] text-white/30 text-right pr-1 -mt-1">
                  {lastUsage.provider}/{lastUsage.model} · {lastUsage.input}+{lastUsage.output} tok · ${(lastUsage.cost_usd ?? 0).toFixed(4)}
                </div>
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* ── Inline controls (tier pills + personality + quick actions) ── */}
            <InlineChatControls onPick={(prompt) => setInput(prompt)} />

            {/* ── Attachment chips (shown above input when files queued) ── */}
            {attachments.length > 0 && (
              <div className="px-3 pt-2 flex flex-wrap gap-1 shrink-0">
                {attachments.map((a) => (
                  <span
                    key={a.id}
                    className="flex items-center gap-1.5 text-[10px] text-jcyan bg-jcyan/10 border border-jcyan/30 px-2 py-1 rounded-full"
                  >
                    📎 {a.filename}
                    <button
                      type="button"
                      onClick={() => removeAttachment(a.id)}
                      className="text-jcyan/60 hover:text-jurgent ml-0.5"
                    >✕</button>
                  </span>
                ))}
              </div>
            )}

            {/* ── Input + drop zone ── */}
            <form
              onSubmit={submit}
              onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              className={`border-t p-3 flex gap-2 shrink-0 rounded-b-xl items-center transition-colors ${
                dragOver ? "border-jcyan bg-jcyan/10" : "border-jcyan/30"
              }`}
            >
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => uploadFiles(e.target.files)}
                multiple
                className="hidden"
                accept=".jpg,.jpeg,.png,.gif,.webp,.pdf,.txt,.csv,.md"
              />
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={busy || uploading}
                title="Attach files"
                className="px-2.5 py-2 text-white/40 hover:text-jcyan transition-colors text-base disabled:opacity-30"
              >
                {uploading ? "…" : "📎"}
              </button>
              <input
                id="jarvis-input"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask JARVIS anything…"
                disabled={busy}
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm placeholder-white/20 focus:outline-none focus:border-jcyan/50 focus:bg-jcyan/5 transition-all disabled:opacity-40"
              />
              {busy ? (
                <button
                  type="button"
                  onClick={cancelStream}
                  className="px-4 py-2 border border-jurgent/60 text-jurgent rounded-lg text-sm font-bold hover:bg-jurgent/10 transition-colors"
                  title="Cancel stream"
                >
                  ■
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={!input.trim()}
                  className="px-4 py-2 border border-jcyan/60 text-jcyan rounded-lg text-sm font-bold hover:bg-jcyan/10 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  ↑
                </button>
              )}
            </form>
          </>
        )}

        {/* ── Resize handle — uses pointer capture, completely isolated from drag ── */}
        {!minimized && (
          <div
            onPointerDown={onResizePointerDown}
            onPointerMove={onResizePointerMove}
            onPointerUp={onResizePointerUp}
            className="absolute bottom-0 right-0 w-6 h-6 cursor-nwse-resize flex items-center justify-center"
            title="Drag to resize"
          >
            <svg
              width="10"
              height="10"
              viewBox="0 0 10 10"
              className="text-jcyan/40 hover:text-jcyan/80 transition-colors"
              fill="currentColor"
            >
              <path d="M2 10 L10 2 L10 10 Z" opacity="0.4" />
              <path d="M6 10 L10 6 L10 10 Z" />
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
    idle:       "bg-white/20",
    listening:  "bg-green-400",
    processing: "bg-yellow-400",
    responding: "bg-jcyan",
  }[wakeState];
  const LABEL = {
    idle:       "Idle",
    listening:  "Listening",
    processing: "Thinking",
    responding: "Speaking",
  }[wakeState];
  return (
    <div className="flex items-center gap-1.5">
      <span
        className={`w-2 h-2 rounded-full ${COLOR} ${wakeState !== "idle" ? "animate-pulse" : ""}`}
      />
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

const TOOL_LABELS: Record<string, string> = {
  send_email: "send email",
  get_priority_emails: "fetch emails",
  get_calendar_events: "fetch calendar",
  get_slack_messages: "fetch slack",
  get_teams_messages: "fetch teams",
  get_whatsapp_messages: "fetch whatsapp",
  get_github_issues: "fetch github",
  get_linear_issues: "fetch linear",
  get_jira_issues: "fetch jira",
  get_notion_pages: "fetch notion",
  get_daily_brief: "daily brief",
  push_to_github: "push to github",
};

/**
 * Persistent inline banner rendered when the backend hallucination
 * guardrail flagged an action-claim phrase that wasn't backed by a
 * matching tool dispatch. Sits between the ToolPills row and the text
 * bubble so the catch is always visible — including after a page reload
 * (since corrections are persisted on the ChatTurn).
 */
function GuardrailBanner({
  corrections,
}: {
  corrections: Array<{ phrase: string; required_tools: string[] }>;
}) {
  return (
    <div className="rounded-lg border border-red-400/50 bg-red-400/10 px-3 py-2 text-xs text-red-300 leading-snug">
      <div className="flex items-start gap-1.5">
        <span aria-hidden className="text-red-400 leading-none">⚠</span>
        <div className="flex-1 space-y-1">
          <div className="font-semibold uppercase tracking-wide text-[10px] text-red-200">
            Guardrail caught a false action claim
          </div>
          {corrections.map((c, i) => (
            <div key={i} className="text-red-300/90">
              <span className="italic">"{c.phrase.slice(0, 120)}"</span>
              {c.required_tools.length > 0 && (
                <span className="block text-red-300/70 text-[10px]">
                  required tool: {c.required_tools.join(", ")}
                </span>
              )}
            </div>
          ))}
          <div className="text-red-200/80 text-[10px] italic">
            Action was NOT executed.
          </div>
        </div>
      </div>
    </div>
  );
}

function ToolPills({ tools }: { tools: ToolEvent[] }) {
  return (
    <div className="flex flex-wrap gap-1">
      {tools.map((t, i) => {
        const label = TOOL_LABELS[t.name] || t.name.replace(/_/g, " ");
        const style =
          t.status === "running"
            ? "bg-jcyan/10 border-jcyan/40 text-jcyan"
            : t.status === "ok"
            ? "bg-green-400/10 border-green-400/40 text-green-300"
            : "bg-jurgent/10 border-jurgent/40 text-jurgent";
        const icon =
          t.status === "running" ? (
            <motion.span
              className="inline-block w-1.5 h-1.5 rounded-full bg-current"
              animate={{ opacity: [0.3, 1, 0.3] }}
              transition={{ duration: 1, repeat: Infinity }}
            />
          ) : t.status === "ok" ? (
            <span className="text-[10px] leading-none">✓</span>
          ) : (
            <span className="text-[10px] leading-none">✕</span>
          );
        return (
          <span
            key={i}
            className={`inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full border ${style}`}
          >
            {icon}
            <span>{label}</span>
          </span>
        );
      })}
    </div>
  );
}
