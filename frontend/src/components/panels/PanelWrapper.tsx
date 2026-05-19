import { motion } from "framer-motion";
import { ReactNode, useState } from "react";

interface Props {
  title: string;
  icon?: string;
  children: ReactNode;
  corner: "tl" | "tr" | "bl" | "br";
  onRefresh?: () => void;
  badge?: string | number;
}

export function PanelWrapper({ title, icon, children, corner, onRefresh, badge }: Props) {
  const [collapsed, setCollapsed] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const align =
    corner === "tl" ? "col-start-1 row-start-1"
    : corner === "tr" ? "col-start-2 row-start-1"
    : corner === "bl" ? "col-start-1 row-start-2"
    : "col-start-2 row-start-2";

  const handleRefresh = async () => {
    if (!onRefresh || refreshing) return;
    setRefreshing(true);
    try { await onRefresh(); } finally {
      setTimeout(() => setRefreshing(false), 600);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`${align} pointer-events-auto bg-black/50 backdrop-blur-sm border border-jcyan/30 rounded-xl overflow-hidden flex flex-col transition-all`}
    >
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-jcyan/15 bg-jcyan/3 shrink-0">
        {icon && <span className="text-sm">{icon}</span>}
        <span className="flex-1 text-xs uppercase tracking-widest text-jcyan font-bold truncate">
          {title}
        </span>

        {/* Badge (item count) */}
        {badge !== undefined && (
          <span className="text-[10px] text-jcyan/60 bg-jcyan/10 rounded px-1.5 py-0.5 font-mono">
            {badge}
          </span>
        )}

        {/* Refresh */}
        {onRefresh && (
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            title="Refresh"
            className="text-white/20 hover:text-jcyan transition-colors text-xs disabled:opacity-30"
          >
            <motion.span
              animate={refreshing ? { rotate: 360 } : { rotate: 0 }}
              transition={refreshing ? { duration: 0.6, repeat: Infinity, ease: "linear" } : {}}
              className="inline-block"
            >
              ↻
            </motion.span>
          </button>
        )}

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed((v) => !v)}
          title={collapsed ? "Expand" : "Collapse"}
          className="text-white/20 hover:text-white/50 transition-colors text-xs ml-0.5"
        >
          {collapsed ? "▲" : "▼"}
        </button>
      </div>

      {/* Body */}
      <motion.div
        initial={false}
        animate={{ height: collapsed ? 0 : "auto", opacity: collapsed ? 0 : 1 }}
        transition={{ type: "spring", stiffness: 400, damping: 35 }}
        className="flex-1 overflow-hidden"
      >
        <div className="h-full overflow-auto p-3 text-sm space-y-2 pr-2">
          {children}
        </div>
      </motion.div>
    </motion.div>
  );
}
