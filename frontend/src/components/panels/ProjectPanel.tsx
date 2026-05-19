import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

const STATUS_STYLE: Record<string, string> = {
  "active":      "text-jcyan bg-jcyan/10 border-jcyan/30",
  "in_progress": "text-jcyan bg-jcyan/10 border-jcyan/30",
  "paused":      "text-yellow-400 bg-yellow-400/10 border-yellow-400/30",
  "blocked":     "text-jurgent bg-jurgent/10 border-jurgent/30",
  "done":        "text-green-400 bg-green-400/10 border-green-400/30",
  "backlog":     "text-white/40 bg-white/5 border-white/10",
};

export function ProjectPanel() {
  const projects = useJarvisStore((s) => s.projects);
  const fetchFeed = useJarvisStore((s) => s.fetchFeed);

  return (
    <PanelWrapper
      title="Projects"
      icon="⬡"
      corner="br"
      onRefresh={fetchFeed}
      badge={projects.length || undefined}
      panelKey="projects"
    >
      {projects.length === 0 && (
        <div className="flex flex-col items-center justify-center py-6 gap-2">
          <span className="text-2xl opacity-20">⬡</span>
          <span className="text-white/30 text-xs">No active projects</span>
        </div>
      )}
      {projects.map((p) => {
        const style = STATUS_STYLE[p.status?.toLowerCase()] || STATUS_STYLE.backlog;
        return (
          <div key={p.id} className="flex items-center gap-2 py-0.5 border-b border-white/5 last:border-0">
            <div className="flex-1 min-w-0">
              {p.url ? (
                <a
                  href={p.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-white/80 hover:text-jcyan transition-colors truncate block text-xs"
                >
                  {p.title}
                </a>
              ) : (
                <div className="text-white/80 truncate text-xs">{p.title}</div>
              )}
              <div className="text-[10px] text-white/30 uppercase">{p.source}</div>
            </div>
            <span className={`shrink-0 text-[10px] px-1.5 py-0.5 rounded border font-bold uppercase tracking-wider ${style}`}>
              {p.status}
            </span>
          </div>
        );
      })}
    </PanelWrapper>
  );
}
