import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { TokensAPI } from "../../lib/api";
import type { TokenUsageDay, TokenUsageToday } from "../../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

/**
 * Floating slide-out panel showing today's usage + a 7-day sparkline.
 * Refreshes every 30s while open. Color-codes the budget bar
 * (green < 60%, yellow < 90%, red ≥ 90%).
 */
export function TokenMonitor({ open, onClose }: Props) {
  const [today, setToday] = useState<TokenUsageToday | null>(null);
  const [history, setHistory] = useState<TokenUsageDay[]>([]);

  useEffect(() => {
    if (!open) return;
    const load = async () => {
      try {
        const [t, h] = await Promise.all([TokensAPI.today(), TokensAPI.history(7)]);
        setToday(t);
        setHistory(h.series);
      } catch {
        // ignore — toast handled at caller
      }
    };
    load();
    const id = setInterval(load, 30_000);
    return () => clearInterval(id);
  }, [open]);

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
            className="fixed right-0 top-0 h-full w-80 z-[110] bg-[#0a0e1a] border-l border-jcyan/30 shadow-2xl flex flex-col"
          >
            <div className="px-5 py-4 border-b border-jcyan/20 flex items-center justify-between">
              <div>
                <h3 className="text-jcyan text-sm font-bold uppercase tracking-widest">Tokens</h3>
                <p className="text-white/30 text-xs">Usage + cost</p>
              </div>
              <button
                onClick={onClose}
                className="text-white/30 hover:text-white text-lg leading-none"
              >✕</button>
            </div>

            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Today */}
              {today ? <TodayCard today={today} /> : <Loading />}

              {/* Sparkline */}
              <Section title="Last 7 days">
                {history.length === 0 ? (
                  <div className="text-white/30 text-xs">No usage yet.</div>
                ) : (
                  <Sparkline series={history} />
                )}
              </Section>

              <Section title="This session">
                <p className="text-white/40 text-xs">
                  Detailed per-call breakdown is at <code className="text-jcyan/80">/api/tokens/session</code>.
                </p>
              </Section>
            </div>

            <div className="px-5 py-3 border-t border-jcyan/20 text-white/20 text-[10px]">
              Refreshes every 30s. Budget set in Settings → AI.
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function TodayCard({ today }: { today: TokenUsageToday }) {
  const pct = Math.min(100, today.used_pct);
  const barColor =
    pct < 60 ? "bg-green-400" : pct < 90 ? "bg-yellow-400" : "bg-jurgent";

  return (
    <Section title="Today" desc={today.date}>
      <div className="space-y-3">
        {/* Budget bar */}
        <div>
          <div className="flex items-center justify-between text-xs mb-1">
            <span className="text-white/60">
              {today.used_total_tokens.toLocaleString()} / {today.budget.toLocaleString()} tokens
            </span>
            <span className="text-white/40">{pct.toFixed(1)}%</span>
          </div>
          <div className="h-2 rounded-full bg-white/5 overflow-hidden">
            <div
              className={`h-full ${barColor} transition-all`}
              style={{ width: `${pct}%` }}
            />
          </div>
        </div>

        {/* Stat grid */}
        <div className="grid grid-cols-2 gap-2">
          <Stat label="Input"  value={today.input.toLocaleString()} />
          <Stat label="Output" value={today.output.toLocaleString()} />
          <Stat label="Cache hit" value={today.cache_read.toLocaleString()} />
          <Stat label="Calls" value={today.calls.toString()} />
        </div>

        {/* Cost */}
        <div className="p-3 rounded-lg border border-jcyan/30 bg-jcyan/5 flex items-center justify-between">
          <span className="text-white/60 text-xs uppercase tracking-wider">Today's cost</span>
          <span className="text-jcyan text-lg font-bold">${today.cost_usd.toFixed(4)}</span>
        </div>
      </div>
    </Section>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="p-2 rounded border border-white/10 bg-white/3">
      <div className="text-white/40 text-[10px] uppercase tracking-wider">{label}</div>
      <div className="text-white font-mono text-sm mt-0.5">{value}</div>
    </div>
  );
}

function Sparkline({ series }: { series: TokenUsageDay[] }) {
  const max = Math.max(...series.map((d) => d.input + d.output), 1);
  const W = 280;
  const H = 60;
  const stepX = W / Math.max(1, series.length - 1);
  const points = series.map((d, i) => {
    const total = d.input + d.output;
    const y = H - (total / max) * (H - 4) - 2;
    const x = i * stepX;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");

  const totalCost = series.reduce((s, d) => s + (d.cost_usd || 0), 0);
  const totalCalls = series.reduce((s, d) => s + (d.calls || 0), 0);

  return (
    <div>
      <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-16">
        <defs>
          <linearGradient id="spark" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"  stopColor="#00d4ff" stopOpacity="0.5"/>
            <stop offset="100%" stopColor="#00d4ff" stopOpacity="0"/>
          </linearGradient>
        </defs>
        <polyline
          fill="url(#spark)"
          stroke="none"
          points={`0,${H} ${points} ${W},${H}`}
        />
        <polyline
          fill="none"
          stroke="#00d4ff"
          strokeWidth="1.5"
          points={points}
        />
      </svg>
      <div className="flex justify-between text-[10px] text-white/30 mt-1">
        <span>{series[0]?.date}</span>
        <span>{series[series.length - 1]?.date}</span>
      </div>
      <div className="mt-3 flex justify-between text-xs">
        <span className="text-white/40">Total: <span className="text-white/70">{totalCalls} calls</span></span>
        <span className="text-jcyan font-bold">${totalCost.toFixed(4)}</span>
      </div>
    </div>
  );
}

function Section({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-white text-sm font-semibold tracking-wide">{title}</h4>
      {desc && <p className="text-white/30 text-xs mb-2">{desc}</p>}
      {children}
    </div>
  );
}

function Loading() {
  return <div className="text-white/40 text-sm">Loading…</div>;
}
