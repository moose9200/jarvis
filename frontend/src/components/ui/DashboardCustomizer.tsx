import { motion, AnimatePresence } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";
import type { PanelKey } from "../../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

const PANEL_META: { key: PanelKey; label: string; icon: string; desc: string; corner: string }[] = [
  { key: "calendar", label: "Calendar", icon: "📅", desc: "Today's events", corner: "Top Left" },
  { key: "email",    label: "Email & Messages", icon: "📧", desc: "Priority inbox + DMs", corner: "Top Right" },
  { key: "tasks",    label: "Tasks", icon: "✓", desc: "Assigned issues & tickets", corner: "Bottom Left" },
  { key: "projects", label: "Projects", icon: "⬡", desc: "Active project status", corner: "Bottom Right" },
];

export function DashboardCustomizer({ open, onClose }: Props) {
  const panelVisibility = useJarvisStore((s) => s.panelVisibility);
  const setPanelVisibility = useJarvisStore((s) => s.setPanelVisibility);
  const mode = useJarvisStore((s) => s.mode);
  const setMode = useJarvisStore((s) => s.setMode);

  return (
    <AnimatePresence>
      {open && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[80] bg-black/40 backdrop-blur-sm"
          />

          {/* Slide-in panel */}
          <motion.div
            initial={{ x: "100%", opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: "100%", opacity: 0 }}
            transition={{ type: "spring", stiffness: 350, damping: 35 }}
            className="fixed right-0 top-0 h-full w-80 z-[90] bg-[#0a0e1a] border-l border-jcyan/30 shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-jcyan/20">
              <div>
                <h2 className="text-jcyan font-bold text-sm tracking-widest uppercase">
                  Customize
                </h2>
                <p className="text-white/30 text-xs mt-0.5">Dashboard layout</p>
              </div>
              <button
                onClick={onClose}
                className="text-white/30 hover:text-white text-lg leading-none transition-colors"
              >
                ✕
              </button>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-5 space-y-6">
              {/* Panels section */}
              <section>
                <h3 className="text-white/40 text-xs uppercase tracking-widest mb-3">
                  Data Panels
                </h3>
                <div className="space-y-2">
                  {PANEL_META.map((p) => {
                    const visible = panelVisibility[p.key];
                    return (
                      <div
                        key={p.key}
                        className={`flex items-center gap-3 p-3 rounded-lg border transition-all ${
                          visible
                            ? "border-jcyan/30 bg-jcyan/5"
                            : "border-white/10 bg-white/3"
                        }`}
                      >
                        <span className="text-lg shrink-0">{p.icon}</span>
                        <div className="flex-1 min-w-0">
                          <div className="text-white text-sm font-medium">{p.label}</div>
                          <div className="text-white/30 text-xs">{p.corner} · {p.desc}</div>
                        </div>
                        <Toggle
                          on={visible}
                          onChange={(v) => setPanelVisibility(p.key, v)}
                        />
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* Interface mode */}
              <section>
                <h3 className="text-white/40 text-xs uppercase tracking-widest mb-3">
                  Interface Mode
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  <ModeCard
                    icon="🎙"
                    label="Voice"
                    desc="Wake word + speech"
                    active={mode === "voice"}
                    onClick={() => setMode("voice")}
                  />
                  <ModeCard
                    icon="⌨"
                    label="Text"
                    desc="Type to JARVIS"
                    active={mode === "text"}
                    onClick={() => setMode("text")}
                  />
                </div>
              </section>

              {/* Coming soon */}
              <section>
                <h3 className="text-white/40 text-xs uppercase tracking-widest mb-3">
                  Coming Soon
                </h3>
                <div className="space-y-2 opacity-40 pointer-events-none">
                  <FeatureRow icon="🎨" label="Theme" desc="Cyan / Purple / Amber" />
                  <FeatureRow icon="🔔" label="Notifications" desc="Desktop alerts" />
                  <FeatureRow icon="⏱" label="Refresh Rate" desc="Panel update interval" />
                </div>
              </section>
            </div>

            {/* Footer */}
            <div className="px-5 py-3 border-t border-jcyan/20 text-white/20 text-xs">
              Settings persist across sessions.
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function Toggle({ on, onChange }: { on: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!on)}
      className={`relative w-10 h-5 rounded-full transition-colors shrink-0 ${
        on ? "bg-jcyan/40 border border-jcyan/60" : "bg-white/10 border border-white/20"
      }`}
    >
      <span
        className={`absolute top-0.5 w-4 h-4 rounded-full transition-all ${
          on ? "left-5 bg-jcyan shadow-lg shadow-jcyan/40" : "left-0.5 bg-white/40"
        }`}
      />
    </button>
  );
}

function ModeCard({
  icon, label, desc, active, onClick,
}: {
  icon: string; label: string; desc: string; active: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex flex-col items-center gap-1.5 p-3 rounded-lg border transition-all text-center ${
        active
          ? "border-jcyan/60 bg-jcyan/10 text-jcyan"
          : "border-white/10 bg-white/3 text-white/50 hover:border-white/30"
      }`}
    >
      <span className="text-xl">{icon}</span>
      <span className="text-xs font-bold uppercase tracking-wider">{label}</span>
      <span className="text-[10px] text-white/30">{desc}</span>
    </button>
  );
}

function FeatureRow({ icon, label, desc }: { icon: string; label: string; desc: string }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg border border-white/10">
      <span className="text-base">{icon}</span>
      <div>
        <div className="text-white text-sm">{label}</div>
        <div className="text-white/30 text-xs">{desc}</div>
      </div>
    </div>
  );
}
