import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

const SOURCE_COLOR: Record<string, string> = {
  linear: "text-purple-400",
  jira:   "text-blue-400",
  notion: "text-white/50",
  github: "text-orange-400",
};

const STATUS_DOT: Record<string, string> = {
  "in_progress": "bg-jcyan",
  "todo": "bg-white/30",
  "done": "bg-green-400",
  "blocked": "bg-jurgent",
};

export function TaskPanel() {
  const tasks = useJarvisStore((s) => s.tasks);
  const fetchFeed = useJarvisStore((s) => s.fetchFeed);

  return (
    <PanelWrapper
      title="Tasks"
      icon="✓"
      corner="bl"
      onRefresh={fetchFeed}
      badge={tasks.length || undefined}
    >
      {tasks.length === 0 && (
        <div className="flex flex-col items-center justify-center py-6 gap-2">
          <span className="text-2xl opacity-20">✓</span>
          <span className="text-white/30 text-xs">All clear</span>
        </div>
      )}
      {tasks.map((t) => (
        <div key={t.id} className="flex items-start gap-2 py-0.5 border-b border-white/5 last:border-0">
          <span
            className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${STATUS_DOT[t.status] || "bg-white/30"}`}
          />
          <div className="flex-1 min-w-0">
            {t.url ? (
              <a
                href={t.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-white/80 hover:text-jcyan transition-colors truncate block text-xs leading-relaxed"
              >
                {t.title}
              </a>
            ) : (
              <div className="text-white/80 truncate text-xs leading-relaxed">{t.title}</div>
            )}
            <div className="flex items-center gap-2 mt-0.5">
              <span className={`text-[10px] uppercase tracking-wider ${SOURCE_COLOR[t.source] || "text-white/40"}`}>
                {t.source}
              </span>
              {t.due && (
                <span className="text-[10px] text-white/25">{new Date(t.due).toLocaleDateString()}</span>
              )}
            </div>
          </div>
        </div>
      ))}
    </PanelWrapper>
  );
}
