import { useEffect, useState } from "react";
import { useJarvisStore } from "../../store/jarvisStore";

const API = import.meta.env.VITE_API_BASE || "";

const CONNECTOR_META: Record<string, { label: string; icon: string; desc: string }> = {
  gmail:            { label: "Gmail",            icon: "📧", desc: "Read & send emails" },
  google_calendar:  { label: "Google Calendar",  icon: "📅", desc: "Today's events" },
  outlook_mail:     { label: "Outlook Mail",     icon: "📨", desc: "Read & send emails" },
  outlook_calendar: { label: "Outlook Calendar", icon: "🗓️", desc: "Today's events" },
  slack:            { label: "Slack",            icon: "💬", desc: "Channels & DMs" },
  teams:            { label: "Microsoft Teams",  icon: "🫂", desc: "Chats & @mentions" },
  whatsapp:         { label: "WhatsApp",         icon: "📱", desc: "Unread messages" },
  github:           { label: "GitHub",           icon: "🐙", desc: "PRs & notifications" },
  linear:           { label: "Linear",           icon: "📐", desc: "Assigned issues" },
  jira:             { label: "Jira",             icon: "🔵", desc: "Assigned tickets" },
  notion:           { label: "Notion",           icon: "📓", desc: "Task database" },
};

interface Props {
  onClose: () => void;
}

export function IntegrationsModal({ onClose }: Props) {
  const connectors = useJarvisStore((s) => s.connectors);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);

  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  const connected = connectors.filter((c) => c.connected).length;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="w-full max-w-2xl mx-4 bg-[#0a0e1a] border border-[#00d4ff]/40 rounded-xl shadow-2xl shadow-[#00d4ff]/10">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-[#00d4ff]/20">
          <div>
            <h2 className="text-[#00d4ff] font-bold text-lg tracking-widest uppercase">
              Integrations
            </h2>
            <p className="text-white/50 text-xs mt-0.5">
              {connected}/{connectors.length} connected — JARVIS pulls data from connected services only
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-white/40 hover:text-white text-xl leading-none"
          >
            ✕
          </button>
        </div>

        {/* Grid */}
        <div className="grid grid-cols-2 gap-3 p-6 max-h-[70vh] overflow-y-auto">
          {connectors.map((c) => {
            const meta = CONNECTOR_META[c.name] || { label: c.display, icon: "🔌", desc: "" };
            return (
              <div
                key={c.name}
                className={`flex items-center gap-4 p-4 rounded-lg border transition-all ${
                  c.connected
                    ? "border-[#00d4ff]/60 bg-[#00d4ff]/5"
                    : "border-white/10 bg-white/3 hover:border-white/30"
                }`}
              >
                <span className="text-2xl">{meta.icon}</span>
                <div className="flex-1 min-w-0">
                  <div className="text-white font-medium text-sm">{meta.label}</div>
                  <div className="text-white/40 text-xs truncate">{meta.desc}</div>
                </div>
                {c.connected ? (
                  <span className="text-[#00d4ff] text-xs font-bold uppercase tracking-wider shrink-0">
                    ✓ On
                  </span>
                ) : c.configured ? (
                  <a
                    href={`${API}/api/auth/${c.name}/start`}
                    className="shrink-0 px-3 py-1.5 text-xs font-bold uppercase tracking-wider border border-[#00d4ff]/50 text-[#00d4ff] rounded hover:bg-[#00d4ff]/10 transition-colors"
                  >
                    Connect
                  </a>
                ) : (
                  <span
                    title="Add credentials to backend/.env to enable this integration"
                    className="shrink-0 text-white/25 text-xs cursor-help select-none"
                  >
                    ⚙ Setup Required
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Footer */}
        <div className="px-6 py-3 border-t border-[#00d4ff]/20 text-white/30 text-xs">
          OAuth flows open in this tab. After connecting, return here and refresh status.
        </div>
      </div>
    </div>
  );
}
