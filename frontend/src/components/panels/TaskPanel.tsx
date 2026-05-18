import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function TaskPanel() {
  const tasks = useJarvisStore((s) => s.tasks);
  return (
    <PanelWrapper title="Tasks" corner="bl">
      {tasks.length === 0 && <div className="text-white/40">All clear.</div>}
      {tasks.map((t) => (
        <div key={t.id} className="flex justify-between border-b border-white/10 py-1">
          <div className="truncate flex-1">{t.title}</div>
          <div className="text-xs text-white/50 ml-2">{t.source}</div>
        </div>
      ))}
    </PanelWrapper>
  );
}
