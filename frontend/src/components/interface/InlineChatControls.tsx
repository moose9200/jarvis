/**
 * Compact inline controls shown above the chat input:
 *   - Tier pills (Eco / Intelligent / Scientist) — driven by Settings.preferences
 *   - Skill dropdown — All Purpose default + 10 popular skills (Coder,
 *     Designer, Writer, Marketer, Founder, Researcher, Analyst, Coach,
 *     Devil's Advocate, Creative). Choice persists to UserSettings.
 *   - Horizontally-scrollable QuickActions chip row (from /api/chat/quick-actions)
 *
 * All controls hit PUT /api/settings/preferences with optimistic local state.
 */
import { useEffect, useRef, useState } from "react";
import { ChatMetaAPI, SettingsAPI } from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";
import type { Tier } from "../../types";

const TIERS: { id: Tier; label: string; desc: string }[] = [
  { id: "eco",         label: "Eco",   desc: "fast + cheap" },
  { id: "intelligent", label: "Intel", desc: "balanced" },
  { id: "scientist",   label: "Sci",   desc: "deepest" },
];

// Local fallback if the /personalities fetch fails. Order matters — first
// entry renders as the default placeholder.
const FALLBACK_SKILLS = [
  { id: "all_purpose",     label: "All Purpose",     tag: "balanced default" },
  { id: "coder",           label: "Coder",           tag: "senior software engineer" },
  { id: "designer",        label: "Designer",        tag: "UI/UX + design systems" },
  { id: "writer",          label: "Writer",          tag: "long-form content" },
  { id: "marketer",        label: "Marketer",        tag: "growth + GTM" },
  { id: "founder",         label: "Founder",         tag: "strategy + decisions" },
  { id: "researcher",      label: "Researcher",      tag: "analysis + citations" },
  { id: "analyst",         label: "Analyst",         tag: "data + metrics" },
  { id: "coach",           label: "Coach",           tag: "Socratic Q&A" },
  { id: "devils_advocate", label: "Devil's Advocate", tag: "challenges assumptions" },
  { id: "creative",        label: "Creative",        tag: "lateral thinking" },
];

interface Skill { id: string; label: string; tag: string }

export function InlineChatControls({ onPick }: { onPick: (prompt: string) => void }) {
  const [tier, setTier] = useState<Tier>("intelligent");
  const [skill, setSkill] = useState<string>("all_purpose");
  const [skills, setSkills] = useState<Skill[]>(FALLBACK_SKILLS);
  const [actions, setActions] = useState<{ id: string; label: string; prompt: string }[]>([]);
  const addToast = useJarvisStore((s) => s.addToast);
  const loadedRef = useRef(false);

  useEffect(() => {
    if (loadedRef.current) return;
    loadedRef.current = true;
    Promise.all([SettingsAPI.get(), ChatMetaAPI.personalities(), ChatMetaAPI.quickActions()])
      .then(([s, p, qa]) => {
        if (s.default_model === "eco" || s.default_model === "intelligent" || s.default_model === "scientist") {
          setTier(s.default_model);
        }
        setSkill(s.personality_mode || "all_purpose");
        if (Array.isArray(p.modes) && p.modes.length) {
          // p.modes already has {id, label, tag, style}
          setSkills(p.modes as Skill[]);
        }
        setActions(qa.actions);
      })
      .catch(() => {/* keep fallback */});
  }, []);

  const pickTier = async (t: Tier) => {
    setTier(t);
    try {
      await SettingsAPI.putPreferences({ default_model: t });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed to save tier." });
    }
  };

  const pickSkill = async (s: string) => {
    setSkill(s);
    try {
      await SettingsAPI.putPreferences({ personality_mode: s });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed to save skill." });
    }
  };

  return (
    <div className="border-t border-jcyan/15 px-2 pt-2 pb-1 shrink-0 space-y-1.5">
      {/* Row 1: tier pills + skill dropdown */}
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

        <SkillDropdown skills={skills} value={skill} onChange={pickSkill} />
      </div>

      {/* Row 2: quick action chips */}
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


function SkillDropdown({
  skills, value, onChange,
}: { skills: Skill[]; value: string; onChange: (id: string) => void }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const current = skills.find((s) => s.id === value) || skills[0];

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        title={current?.tag}
        className="flex items-center gap-1.5 px-2.5 py-1 text-[10px] uppercase tracking-wider rounded-full font-bold border border-white/15 bg-black/40 text-white/70 hover:text-jcyan hover:border-jcyan/40 transition-colors"
      >
        <span className="text-jcyan/80">▾</span>
        <span>{current?.label || "All Purpose"}</span>
      </button>

      {open && (
        <div className="absolute bottom-full left-0 mb-1 min-w-[14rem] bg-[#0a0e1a]/95 backdrop-blur-md border border-jcyan/30 rounded-lg shadow-2xl z-50 max-h-[60vh] overflow-y-auto">
          {skills.map((s) => {
            const active = s.id === value;
            return (
              <button
                key={s.id}
                type="button"
                onClick={() => { onChange(s.id); setOpen(false); }}
                className={`w-full text-left px-3 py-2 transition-colors border-l-2 ${
                  active
                    ? "border-jcyan bg-jcyan/10 text-white"
                    : "border-transparent text-white/70 hover:bg-white/5 hover:text-white"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium">{s.label}</span>
                  {active && <span className="text-jcyan text-xs">✓</span>}
                </div>
                <div className="text-[10px] text-white/40 mt-0.5">{s.tag}</div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}
