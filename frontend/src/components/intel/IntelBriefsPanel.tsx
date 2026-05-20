/**
 * Intel Briefs — slide-in panel listing the user's saved monitors.
 *
 * For each brief: name, topic, last-run time, "Run now" button. Clicking
 * a brief expands its latest output (Markdown rendered as plain text;
 * preserves whitespace).
 *
 * Triggered by 🌐 button in the top bar.
 */
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { IntelAPI, type IntelBrief, type IntelBriefRun } from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";

interface Props {
  open: boolean;
  onClose: () => void;
}

export function IntelBriefsPanel({ open, onClose }: Props) {
  const [briefs, setBriefs] = useState<IntelBrief[]>([]);
  const [loading, setLoading] = useState(false);
  const [runningId, setRunningId] = useState<number | null>(null);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [runs, setRuns] = useState<Record<number, IntelBriefRun[]>>({});
  const addToast = useJarvisStore((s) => s.addToast);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    IntelAPI.list()
      .then((r) => setBriefs(r.briefs))
      .catch(() => addToast({ type: "error", message: "Failed to load briefs." }))
      .finally(() => setLoading(false));
  }, [open, addToast]);

  const runNow = async (id: number) => {
    setRunningId(id);
    addToast({ type: "info", message: "Fetching public web data + synthesizing…" });
    try {
      const run = await IntelAPI.run(id);
      setRuns((r) => ({ ...r, [id]: [run, ...(r[id] || [])] }));
      setExpandedId(id);
      if (run.status === "done") {
        addToast({ type: "success", message: `Brief refreshed. Cost $${run.cost_usd.toFixed(4)}.` });
      } else if (run.status === "failed") {
        addToast({ type: "error", message: run.error || "Brief failed." });
      }
      // refresh last_run_at
      const fresh = await IntelAPI.list();
      setBriefs(fresh.briefs);
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Run failed." });
    } finally {
      setRunningId(null);
    }
  };

  const expand = async (id: number) => {
    if (expandedId === id) {
      setExpandedId(null);
      return;
    }
    setExpandedId(id);
    if (!runs[id]) {
      try {
        const r = await IntelAPI.runs(id, 10);
        setRuns((rs) => ({ ...rs, [id]: r.runs }));
      } catch {
        addToast({ type: "error", message: "Couldn't load run history." });
      }
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
            className="fixed right-0 top-0 h-full w-[28rem] z-[110] bg-[#0a0e1a] border-l border-jcyan/30 shadow-2xl flex flex-col"
          >
            <div className="px-5 py-4 border-b border-jcyan/20 flex items-center justify-between">
              <div>
                <h3 className="text-jcyan text-sm font-bold uppercase tracking-widest">
                  Intel Briefs
                </h3>
                <p className="text-white/30 text-xs">
                  Industry chatter + public-web monitors
                </p>
              </div>
              <button onClick={onClose} className="text-white/30 hover:text-white text-lg leading-none">✕</button>
            </div>

            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {loading && <div className="text-white/40 text-sm">Loading…</div>}
              {!loading && briefs.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
                  <span className="text-3xl opacity-30">🌐</span>
                  <span className="text-white/40 text-sm">No briefs yet.</span>
                  <span className="text-white/20 text-xs">
                    Set your industry in Profile → Settings → Account.
                  </span>
                </div>
              )}
              {briefs.map((b) => (
                <BriefCard
                  key={b.id}
                  b={b}
                  running={runningId === b.id}
                  expanded={expandedId === b.id}
                  runs={runs[b.id] || []}
                  onRun={() => runNow(b.id)}
                  onToggle={() => expand(b.id)}
                />
              ))}
            </div>

            <div className="px-5 py-3 border-t border-jcyan/20 text-white/20 text-[10px]">
              Daily auto-run scheduled (Celery beat) — manual "Run now" works today.
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function BriefCard({
  b, running, expanded, runs, onRun, onToggle,
}: {
  b: IntelBrief;
  running: boolean;
  expanded: boolean;
  runs: IntelBriefRun[];
  onRun: () => void;
  onToggle: () => void;
}) {
  const sources = b.sources_json || {};
  const reddit = (sources.reddit || []) as string[];
  return (
    <div className={`rounded-lg border transition-colors ${expanded ? "border-jcyan/50 bg-jcyan/5" : "border-white/10 bg-white/3 hover:border-white/30"}`}>
      <div className="p-3">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2">
              <span className="text-white font-medium text-sm">{b.name}</span>
              {!b.is_active && (
                <span className="text-[9px] text-white/40 bg-white/5 px-1.5 py-0.5 rounded border border-white/10">PAUSED</span>
              )}
            </div>
            <div className="text-white/50 text-xs mt-0.5">📌 {b.topic}</div>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {reddit.map((s) => (
                <span key={s} className="text-[10px] text-orange-300/80 bg-orange-400/10 border border-orange-400/20 px-1.5 py-0.5 rounded">
                  r/{s}
                </span>
              ))}
              {sources.hn && (
                <span className="text-[10px] text-orange-200/80 bg-orange-500/10 border border-orange-500/20 px-1.5 py-0.5 rounded">
                  HN
                </span>
              )}
            </div>
            <div className="text-white/30 text-[10px] mt-1">
              {b.last_run_at ? `Last run: ${new Date(b.last_run_at).toLocaleString()}` : "Never run yet"}
            </div>
          </div>
          <div className="flex flex-col items-end gap-1 shrink-0">
            <button
              onClick={onRun}
              disabled={running}
              className="px-2.5 py-1 rounded border border-jcyan/40 text-jcyan text-[10px] font-bold uppercase tracking-wider hover:bg-jcyan/10 disabled:opacity-40"
            >
              {running ? "…" : "Run now"}
            </button>
            <button
              onClick={onToggle}
              className="text-white/30 hover:text-white text-[10px] uppercase tracking-wider"
            >
              {expanded ? "Hide" : "History"}
            </button>
          </div>
        </div>
      </div>
      {expanded && (
        <div className="border-t border-white/10 p-3 space-y-2">
          {runs.length === 0 && <div className="text-white/30 text-xs">No runs yet. Click "Run now".</div>}
          {runs.map((r) => (
            <details key={r.id} className="text-xs" open={runs[0]?.id === r.id}>
              <summary className="cursor-pointer text-white/60 hover:text-white">
                {r.status === "done"
                  ? `✓ ${r.started_at ? new Date(r.started_at).toLocaleString() : ""} · $${r.cost_usd.toFixed(4)}`
                  : r.status === "failed"
                  ? `✕ ${r.error?.slice(0, 60) || "Failed"}`
                  : `⏳ ${r.status}`}
              </summary>
              {r.output_text && (
                <pre className="text-white/80 text-xs whitespace-pre-wrap font-mono mt-2 p-2 bg-black/30 rounded border border-white/5 leading-relaxed max-h-[24rem] overflow-y-auto">
                  {r.output_text}
                </pre>
              )}
              {r.sources_summary && (
                <div className="text-white/30 text-[10px] mt-1">
                  Sources: {Object.entries(r.sources_summary).map(([k, v]) => `${k}=${v}`).join(", ")}
                </div>
              )}
            </details>
          ))}
        </div>
      )}
    </div>
  );
}
