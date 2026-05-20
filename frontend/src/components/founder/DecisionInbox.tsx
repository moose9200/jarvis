/**
 * Decision Inbox — slide-in panel listing items that need user action.
 *
 * Sources are populated by Celery jobs (deferred): GitHub PRs, Shopify large
 * orders, Freshdesk urgent tickets, Linear/Jira blocked issues. Each row
 * shows the AI's suggested action and 4 buttons: ✓ Approve / ✗ Reject /
 * → Delegate / 💤 Snooze.
 *
 * Approve/Reject/Delegate transition the row to that status. Snooze hides
 * the row for N hours (default 24). Snoozed items resurface automatically
 * once their timer passes — backend GET /api/decisions?status=pending
 * already folds expired snoozes back into the pending list.
 */
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { DecisionsAPI, type DecisionRow } from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";

interface Props {
  open: boolean;
  onClose: () => void;
}

const SOURCE_LABELS: Record<string, { icon: string; label: string }> = {
  github_pr:        { icon: "🐙", label: "GitHub PR" },
  github_issue:     { icon: "🐙", label: "GitHub issue" },
  shopify_order:    { icon: "🛒", label: "Shopify order" },
  freshdesk_ticket: { icon: "🎫", label: "Freshdesk ticket" },
  linear_issue:     { icon: "📐", label: "Linear" },
  jira_issue:       { icon: "🔵", label: "Jira" },
  manual:           { icon: "✏",  label: "Manual" },
};

export function DecisionInbox({ open, onClose }: Props) {
  const [rows, setRows] = useState<DecisionRow[]>([]);
  const [loading, setLoading] = useState(false);
  const addToast = useJarvisStore((s) => s.addToast);

  const load = async () => {
    setLoading(true);
    try {
      const r = await DecisionsAPI.list("pending");
      setRows(r.decisions);
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed to load decisions." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) load();
  }, [open]);

  const act = async (id: number, status: string, snoozeHours?: number) => {
    try {
      await DecisionsAPI.patch(id, { status, snooze_hours: snoozeHours });
      setRows((rs) => rs.filter((r) => r.id !== id));
      addToast({ type: "success", message: `Decision ${status}.` });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed." });
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 360, damping: 32 }}
            className="fixed right-0 top-0 h-full w-[26rem] z-[110] bg-[#0a0e1a] border-l border-jcyan/30 shadow-2xl flex flex-col"
          >
            <div className="px-5 py-4 border-b border-jcyan/20 flex items-center justify-between">
              <div>
                <h3 className="text-jcyan text-sm font-bold uppercase tracking-widest">
                  Decisions
                </h3>
                <p className="text-white/30 text-xs">
                  {rows.length} pending — awaiting your call
                </p>
              </div>
              <button
                onClick={onClose}
                className="text-white/30 hover:text-white text-lg leading-none"
              >✕</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {loading && <div className="text-white/40 text-sm">Loading…</div>}
              {!loading && rows.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
                  <span className="text-3xl opacity-30">✓</span>
                  <span className="text-white/40 text-sm">Inbox zero. Nothing waiting.</span>
                  <span className="text-white/20 text-xs">
                    Decisions surface here from GitHub, Shopify, Freshdesk, etc.
                  </span>
                </div>
              )}
              {rows.map((d) => (
                <DecisionCard key={d.id} d={d} onAct={act} />
              ))}
            </div>

            <div className="px-5 py-3 border-t border-jcyan/20 text-white/20 text-[10px]">
              Snoozed items reappear after their timer.
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function DecisionCard({
  d, onAct,
}: { d: DecisionRow; onAct: (id: number, status: string, hours?: number) => void }) {
  const meta = SOURCE_LABELS[d.source] || { icon: "•", label: d.source };
  return (
    <div className="p-3 rounded-lg border border-white/10 bg-white/3 hover:border-jcyan/30 transition-colors">
      <div className="flex items-center gap-2 mb-1">
        <span className="text-sm">{meta.icon}</span>
        <span className="text-jcyan/70 text-[10px] uppercase tracking-wider">{meta.label}</span>
        {d.source_id && (
          <span className="text-white/30 text-[10px]">#{d.source_id}</span>
        )}
      </div>
      <div className="text-white text-sm font-medium leading-snug">{d.title}</div>
      {d.ai_suggestion && (
        <div className="mt-2 p-2 rounded bg-jcyan/5 border border-jcyan/20">
          <div className="text-jcyan/60 text-[10px] uppercase tracking-wider mb-0.5">
            JARVIS suggests
          </div>
          <div className="text-white/80 text-xs leading-relaxed">{d.ai_suggestion}</div>
        </div>
      )}
      <div className="flex gap-1 mt-3">
        <ActionBtn label="✓ Approve"  color="green"  onClick={() => onAct(d.id, "approved")} />
        <ActionBtn label="✗ Reject"   color="red"    onClick={() => onAct(d.id, "rejected")} />
        <ActionBtn label="→ Delegate" color="purple" onClick={() => onAct(d.id, "delegated")} />
        <ActionBtn label="💤 Snooze"  color="yellow" onClick={() => onAct(d.id, "snoozed", 24)} />
      </div>
    </div>
  );
}

function ActionBtn({
  label, color, onClick,
}: { label: string; color: "green" | "red" | "purple" | "yellow"; onClick: () => void }) {
  const cls = {
    green:  "text-green-300 border-green-400/30 hover:bg-green-400/10",
    red:    "text-red-300 border-red-400/30 hover:bg-red-400/10",
    purple: "text-purple-300 border-purple-400/30 hover:bg-purple-400/10",
    yellow: "text-yellow-300 border-yellow-400/30 hover:bg-yellow-400/10",
  }[color];
  return (
    <button
      onClick={onClick}
      className={`flex-1 px-1.5 py-1 rounded border text-[10px] font-bold uppercase tracking-wider transition-colors ${cls}`}
    >
      {label}
    </button>
  );
}
