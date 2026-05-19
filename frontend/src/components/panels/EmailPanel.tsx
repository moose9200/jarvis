import { useJarvisStore } from "../../store/jarvisStore";
import { PanelWrapper } from "./PanelWrapper";

const SOURCE_ICON: Record<string, string> = {
  gmail: "G", outlook: "O", slack: "S", teams: "T", whatsapp: "W",
};

export function EmailPanel() {
  const emails = useJarvisStore((s) => s.emails);
  const messages = useJarvisStore((s) => s.messages);
  const fetchFeed = useJarvisStore((s) => s.fetchFeed);
  const total = emails.length + messages.length;

  return (
    <PanelWrapper
      title="Inbox & Messages"
      icon="📧"
      corner="tr"
      onRefresh={fetchFeed}
      badge={total || undefined}
      panelKey="email"
    >
      {emails.length === 0 && messages.length === 0 && (
        <div className="flex flex-col items-center justify-center py-6 gap-2">
          <span className="text-2xl opacity-20">📬</span>
          <span className="text-white/30 text-xs">Inbox empty</span>
        </div>
      )}

      {emails.slice(0, 5).map((e) => {
        const urgency = e.priority > 0.7 ? "bg-jurgent" : e.priority > 0.4 ? "bg-jcyan" : "bg-white/20";
        return (
          <div key={e.id} className="flex gap-2 items-start py-0.5">
            <div className={`w-0.5 self-stretch rounded-full mt-1 ${urgency}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-1.5">
                <span className="font-medium truncate text-white/90 text-xs">{e.from}</span>
                {e.unread && <span className="w-1.5 h-1.5 rounded-full bg-jcyan shrink-0" />}
                <span className="ml-auto text-[10px] text-white/20 shrink-0">{SOURCE_ICON[e.source]}</span>
              </div>
              <div className="text-white/50 text-xs truncate">{e.subject}</div>
            </div>
          </div>
        );
      })}

      {messages.length > 0 && emails.length > 0 && (
        <div className="border-t border-white/10 pt-1 mt-1" />
      )}

      {messages.slice(0, 3).map((m) => (
        <div key={m.id} className="flex gap-2 items-start py-0.5">
          <div className="w-0.5 self-stretch rounded-full mt-1 bg-jblue" />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="font-medium truncate text-white/90 text-xs">{m.from}</span>
              {m.channel && <span className="text-[10px] text-white/30">#{m.channel}</span>}
              <span className="ml-auto text-[10px] text-white/20 shrink-0">{SOURCE_ICON[m.source]}</span>
            </div>
            <div className="text-white/50 text-xs truncate">{m.text}</div>
          </div>
        </div>
      ))}
    </PanelWrapper>
  );
}
