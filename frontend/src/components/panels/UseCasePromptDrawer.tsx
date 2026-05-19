/**
 * Per-panel suggestion drawer. Opens when the user clicks the ❓ button in
 * a PanelWrapper. Renders 5 polished prompts; clicking one sends it to chat.
 *
 * Prompts come from GET /api/chat/suggestions/{panel}. We cache them on
 * mount so re-opens are instant.
 */
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";

const API = import.meta.env.VITE_API_BASE || "";

interface Props {
  panel: string;       // "email" | "calendar" | "tasks" | "projects" | ...
  title: string;       // human label for the header
  open: boolean;
  onClose: () => void;
}

const CACHE: Record<string, string[]> = {};

export function UseCasePromptDrawer({ panel, title, open, onClose }: Props) {
  const [prompts, setPrompts] = useState<string[]>(CACHE[panel] || []);
  const [loading, setLoading] = useState(false);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const setMode = useJarvisStore((s) => s.setMode);
  const token = useJarvisStore((s) => s.token);

  useEffect(() => {
    if (!open || prompts.length || !token) return;
    setLoading(true);
    fetch(`${API}/api/chat/suggestions/${panel}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (d?.prompts) {
          CACHE[panel] = d.prompts;
          setPrompts(d.prompts);
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open, panel, prompts.length, token]);

  const send = async (prompt: string) => {
    setMode("text");
    onClose();
    await sendChat(prompt);
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: -6 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -6 }}
          transition={{ duration: 0.15 }}
          className="absolute top-9 left-0 right-0 z-30 bg-[#0a0e1a]/95 backdrop-blur border border-jcyan/30 rounded-lg shadow-2xl p-2 mx-2"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-center justify-between px-2 py-1 mb-1">
            <span className="text-jcyan text-[10px] uppercase tracking-widest font-bold">
              Ask about {title}
            </span>
            <button onClick={onClose} className="text-white/30 hover:text-white text-xs">✕</button>
          </div>
          {loading ? (
            <div className="text-white/40 text-xs px-2 py-1">Loading…</div>
          ) : prompts.length === 0 ? (
            <div className="text-white/40 text-xs px-2 py-1">No suggestions.</div>
          ) : (
            <div className="space-y-1">
              {prompts.map((p, i) => (
                <button
                  key={i}
                  onClick={() => send(p)}
                  className="w-full text-left text-xs text-white/70 hover:text-white hover:bg-jcyan/10 rounded px-2 py-1.5 transition-colors"
                >
                  {p}
                </button>
              ))}
            </div>
          )}
        </motion.div>
      )}
    </AnimatePresence>
  );
}
