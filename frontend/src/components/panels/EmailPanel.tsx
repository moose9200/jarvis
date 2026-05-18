import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

export function EmailPanel() {
  const emails = useJarvisStore((s) => s.emails);
  const messages = useJarvisStore((s) => s.messages);
  return (
    <PanelWrapper title="Inbox & Messages" corner="tr">
      {emails.slice(0, 6).map((e) => (
        <div key={e.id} className="flex gap-2">
          <div
            className={`w-1 ${
              e.priority > 0.7 ? "bg-jurgent" : e.priority > 0.4 ? "bg-jcyan" : "bg-white/30"
            }`}
          />
          <div className="flex-1">
            <div className="font-bold truncate">{e.from}</div>
            <div className="truncate">{e.subject}</div>
          </div>
        </div>
      ))}
      {messages.slice(0, 4).map((m) => (
        <div key={m.id} className="flex gap-2 text-white/80">
          <div className="w-1 bg-jblue" />
          <div className="flex-1">
            <div className="font-bold">
              {m.from} · <span className="text-xs text-white/50">{m.source}</span>
            </div>
            <div className="truncate">{m.text}</div>
          </div>
        </div>
      ))}
      {emails.length === 0 && messages.length === 0 && (
        <div className="text-white/40">Inbox empty.</div>
      )}
    </PanelWrapper>
  );
}
