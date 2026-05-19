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
    <PanelWrapper
      title="Calendar"
      icon="📅"
      corner="tl"
      onRefresh={fetchFeed}
      badge={events.length || undefined}
    >
      {events.length === 0 && (
        <div className="flex flex-col items-center justify-center py-6 gap-2">
          <span className="text-2xl opacity-20">📅</span>
          <span className="text-white/30 text-xs">No events today</span>
        </div>
      )}
      {events.map((e) => {
        const start = new Date(e.start);
        const now = new Date();
        const isPast = start < now;
        return (
          <div key={e.id} className={`border-l-2 pl-2 py-0.5 ${isPast ? "border-white/20 opacity-50" : "border-jcyan"}`}>
            <div className={`font-medium truncate ${isPast ? "text-white/50" : "text-white"}`}>
              {e.title}
            </div>
            <div className="text-white/40 text-xs flex items-center gap-1.5">
              <span>
                {start.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </span>
              {e.location && (
                <>
                  <span>·</span>
                  <span className="truncate">{e.location}</span>
                </>
              )}
              <span className="ml-auto shrink-0 uppercase text-[10px] text-jcyan/50">{e.source}</span>
            </div>
          </div>
        );
      })}
    </PanelWrapper>
  );
}
