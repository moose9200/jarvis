/**
 * Compact inline controls shown above the chat input:
 *   - Tier pills (Eco / Intelligent / Scientist) — driven by /api/settings preferences
 *   - Personality pill quick-switcher (current mode shown, click to cycle)
 *   - Horizontally-scrollable QuickActions chip row (from /api/chat/quick-actions)
 *
 * All persist to UserSettings via SettingsAPI.putPreferences. Local-state shadow
 * keeps the UI responsive while the PUT is in-flight.
 */
import { useEffect, useRef, useState } from "react";
import { ChatMetaAPI, SettingsAPI } from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";
import type { Personality, Tier } from "../../types";

const TIERS: { id: Tier; label: string; desc: string }[] = [
  { id: "eco",         label: "Eco",         desc: "fast + cheap" },
  { id: "intelligent", label: "Intel",       desc: "balanced" },
  { id: "scientist",   label: "Sci",         desc: "deepest" },
];

// Order matters — click cycles in this sequence
const PERSONALITY_CYCLE: Personality[] = [
  "caveman", "executive", "expert", "creative", "devils_advocate", "coach",
];

const PERSONALITY_GLYPH: Record<Personality, string> = {
  caveman: "🪨",
  expert: "🎓",
  creative: "🎨",
  executive: "📊",
  devils_advocate: "⚔",
  coach: "🧭",
};

export function InlineChatControls({ onPick }: { onPick: (prompt: string) => void }) {
  const [tier, setTier] = useState<Tier>("intelligent");
  const [personality, setPersonality] = useState<Personality>("caveman");
  const [actions, setActions] = useState<{ id: string; label: string; prompt: string }[]>([]);
  const addToast = useJarvisStore((s) => s.addToast);
  const loadedRef = useRef(false);

  // Load current settings + quick actions on mount
  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    Promise.all([SettingsAPI.get(), ChatMetaAPI.quickActions()])
      .then(([s, qa]) => {
        if (s.default_model === "eco" || s.default_model === "intelligent" || s.default_model === "scientist") {
          setTier(s.default_model);
        }
        setPersonality((s.personality_mode || "caveman") as Personality);
        setActions(qa.actions);
      })
      .catch(() => {});
  }, []);

  const pickTier = async (t: Tier) => {
    setTier(t);
    try {
      await SettingsAPI.putPreferences({ default_model: t });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed to save tier." });
    }
  };

  const cyclePersonality = async () => {
    const next = PERSONALITY_CYCLE[(PERSONALITY_CYCLE.indexOf(personality) + 1) % PERSONALITY_CYCLE.length];
    setPersonality(next);
    try {
      await SettingsAPI.putPreferences({ personality_mode: next });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed." });
    }
  };

  return (
    <div className="border-t border-jcyan/15 px-2 pt-2 pb-1 shrink-0 space-y-1.5">
      {/* Row 1: tier pills + personality switcher */}
      <div className="flex items-center gap-2">
        <div className="flex items-center gap-0.5 bg-black/40 rounded-full p-0.5 border border-white/10">
          {TIERS.map((t) => (
            <button
              key={t.id}
              type="button"
              onClick={() => pickTier(t.id)}
              title={t.desc}
              className={`px-2.5 py-1 text-[10px] uppercase tracking-wider rounded-full font-bold transition-colors ${
                tier === t.id
                  ? "bg-jcyan/25 text-jcyan border border-jcyan/40"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <button
          type="button"
          onClick={cyclePersonality}
          title={`Personality: ${personality}. Click to cycle.`}
          className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-wider rounded-full font-bold border border-white/15 bg-black/40 text-white/60 hover:text-jcyan hover:border-jcyan/40 transition-colors"
        >
          <span>{PERSONALITY_GLYPH[personality]}</span>
          <span>{personality.replace("_", " ")}</span>
        </button>
      </div>

      {/* Row 2: quick action chips (horizontally scrollable) */}
      {actions.length > 0 && (
        <div className="flex gap-1 overflow-x-auto scrollbar-thin pb-1 -mx-0.5 px-0.5">
          {actions.map((a) => (
            <button
              key={a.id}
              type="button"
              onClick={() => onPick(a.prompt)}
              title={a.prompt}
              className="shrink-0 px-2.5 py-1 text-[10px] text-white/60 hover:text-white bg-white/3 hover:bg-jcyan/10 border border-white/10 hover:border-jcyan/30 rounded-full transition-colors whitespace-nowrap"
            >
              {a.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
