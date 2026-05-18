import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function ProjectPanel() {
  const projects = useJarvisStore((s) => s.projects);
  return (
    <PanelWrapper title="Projects" corner="br">
      {projects.length === 0 && <div className="text-white/40">Quiet today.</div>}
      {projects.map((p) => (
        <div key={p.id} className="flex justify-between">
          <div className="truncate">{p.title}</div>
          <div className="text-xs text-jcyan">{p.status}</div>
        </div>
      ))}
    </PanelWrapper>
  );
}
