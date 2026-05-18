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
    <PanelWrapper title="Calendar" corner="tl">
      {events.length === 0 && <div className="text-white/40">No events.</div>}
      {events.map((e) => (
        <div key={e.id} className="border-l-2 border-jcyan pl-2">
          <div className="font-bold">{e.title}</div>
          <div className="text-white/60 text-xs">
            {new Date(e.start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })} ·{" "}
            {e.location || e.source}
          </div>
        </div>
      ))}
    </PanelWrapper>
  );
}
