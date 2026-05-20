import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ContextAPI, SettingsAPI } from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";
import type {
  AIProvider,
  Personality,
  Tier,
  UserContextSnapshot,
  UserSettingsSnapshot,
} from "../../types";

interface Props {
  open: boolean;
  onClose: () => void;
}

type TabId = "ai" | "keys" | "context" | "integrations" | "github" | "account";

const TABS: { id: TabId; label: string; icon: string; desc: string }[] = [
  { id: "ai",           label: "AI & Intelligence", icon: "🧠", desc: "Tier, personality, budget" },
  { id: "keys",         label: "API Keys",          icon: "🔑", desc: "Bring your own keys" },
  { id: "context",      label: "About Me",          icon: "👤", desc: "Persona + RAG context" },
  { id: "integrations", label: "Integrations",      icon: "🔌", desc: "Gmail, Calendar, Slack …" },
  { id: "github",       label: "GitHub",            icon: "🐙", desc: "Repo + access token" },
  { id: "account",      label: "Account",           icon: "🛡", desc: "Password, danger zone" },
];

const PROVIDERS: { id: AIProvider; label: string; recommended?: boolean; cheap?: string }[] = [
  { id: "anthropic", label: "Anthropic", recommended: true, cheap: "Cache hits up to 90% off" },
  { id: "openai",    label: "OpenAI",    cheap: "Cheapest for Eco tier ($0.15/M)" },
  { id: "groq",      label: "Groq",      cheap: "20× faster, Llama models" },
  { id: "mistral",   label: "Mistral",   cheap: "EU-hosted option" },
  { id: "google",    label: "Google",    cheap: "Gemini 2.5 Pro" },
];

const TIERS: { id: Tier; label: string; desc: string; cost: string }[] = [
  { id: "eco",         label: "Eco",         desc: "Fast & cheap. Day-to-day questions.", cost: "$1/M in" },
  { id: "intelligent", label: "Intelligent", desc: "Default. Balanced quality.",            cost: "$3/M in" },
  { id: "scientist",   label: "Scientist",   desc: "Deep thinking on hard problems.",       cost: "$15/M in" },
];

// Skill catalogue — matches backend ai/persona.py SKILLS dict.
// 1 default (All Purpose) + 10 popular Anthropic Claude use cases.
const PERSONALITIES: { id: Personality; label: string; tag: string }[] = [
  { id: "all_purpose",     label: "All Purpose",      tag: "Balanced default" },
  { id: "coder",           label: "Coder",            tag: "Senior software engineer" },
  { id: "designer",        label: "Designer",         tag: "UI/UX + design systems" },
  { id: "writer",          label: "Writer",           tag: "Long-form content" },
  { id: "marketer",        label: "Marketer",         tag: "Growth + GTM" },
  { id: "founder",         label: "Founder",          tag: "Strategy + decisions" },
  { id: "researcher",      label: "Researcher",       tag: "Analysis + citations" },
  { id: "analyst",         label: "Analyst",          tag: "Data + metrics" },
  { id: "coach",           label: "Coach",            tag: "Socratic Q&A" },
  { id: "devils_advocate", label: "Devil's Advocate", tag: "Challenges assumptions" },
  { id: "creative",        label: "Creative",         tag: "Lateral thinking" },
];

export function SettingsPage({ open, onClose }: Props) {
  const [tab, setTab] = useState<TabId>("ai");
  const [settings, setSettings] = useState<UserSettingsSnapshot | null>(null);
  const [context, setContext] = useState<UserContextSnapshot | null>(null);
  const addToast = useJarvisStore((s) => s.addToast);

  // Load on open
  useEffect(() => {
    if (!open) return;
    SettingsAPI.get().then(setSettings).catch(() => addToast({ type: "error", message: "Failed to load settings." }));
    ContextAPI.get().then(setContext).catch(() => {});
  }, [open, addToast]);

  if (!open) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[120] flex items-center justify-center bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      >
        <motion.div
          initial={{ y: 20, scale: 0.97 }}
          animate={{ y: 0, scale: 1 }}
          exit={{ y: 20, scale: 0.97 }}
          transition={{ type: "spring", stiffness: 360, damping: 32 }}
          onClick={(e) => e.stopPropagation()}
          className="w-full max-w-5xl h-[88vh] mx-4 bg-[#0a0e1a] border border-jcyan/30 rounded-2xl shadow-2xl shadow-jcyan/10 flex overflow-hidden"
        >
          {/* Sidebar */}
          <div className="w-60 shrink-0 border-r border-white/10 bg-black/30 flex flex-col">
            <div className="px-5 py-4 border-b border-white/10">
              <h2 className="text-jcyan text-sm font-bold uppercase tracking-widest">Settings</h2>
              <p className="text-white/30 text-xs mt-0.5">Configure JARVIS</p>
            </div>
            <nav className="flex-1 overflow-y-auto py-2">
              {TABS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => setTab(t.id)}
                  className={`w-full flex items-start gap-3 px-5 py-2.5 text-left transition-colors ${
                    tab === t.id
                      ? "bg-jcyan/10 border-l-2 border-jcyan text-white"
                      : "border-l-2 border-transparent text-white/50 hover:bg-white/5 hover:text-white/80"
                  }`}
                >
                  <span className="text-base mt-0.5">{t.icon}</span>
                  <span>
                    <span className="block text-sm font-medium">{t.label}</span>
                    <span className="block text-[10px] text-white/30">{t.desc}</span>
                  </span>
                </button>
              ))}
            </nav>
            <div className="px-5 py-3 border-t border-white/10 text-white/20 text-[10px]">
              JARVIS V2 · Settings persist per account.
            </div>
          </div>

          {/* Content */}
          <div className="flex-1 flex flex-col min-w-0">
            <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
              <div className="flex items-center gap-2">
                <span className="text-lg">{TABS.find((t) => t.id === tab)?.icon}</span>
                <h3 className="text-white font-semibold tracking-wide">{TABS.find((t) => t.id === tab)?.label}</h3>
              </div>
              <button
                onClick={onClose}
                className="text-white/30 hover:text-white text-xl leading-none transition-colors"
              >✕</button>
            </div>
            <div className="flex-1 overflow-y-auto p-6">
              {tab === "ai"           && <AITab settings={settings} setSettings={setSettings} />}
              {tab === "keys"         && <KeysTab settings={settings} setSettings={setSettings} />}
              {tab === "context"      && <ContextTab context={context} setContext={setContext} />}
              {tab === "integrations" && <IntegrationsTab />}
              {tab === "github"       && <GitHubTab settings={settings} setSettings={setSettings} />}
              {tab === "account"      && <AccountTab />}
            </div>
          </div>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}

// ── AI tab ──────────────────────────────────────────────────────────────────

function AITab({
  settings, setSettings,
}: { settings: UserSettingsSnapshot | null; setSettings: (s: UserSettingsSnapshot) => void }) {
  const addToast = useJarvisStore((s) => s.addToast);
  if (!settings) return <Loading />;

  const update = async (patch: Parameters<typeof SettingsAPI.putPreferences>[0]) => {
    try {
      const next = await SettingsAPI.putPreferences(patch);
      setSettings(next);
      addToast({ type: "success", message: "Preferences saved." });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Save failed." });
    }
  };

  const setProvider = async (p: AIProvider) => {
    try {
      const next = await SettingsAPI.putActiveProvider(p);
      setSettings(next);
      addToast({ type: "success", message: `Active provider: ${p}.` });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Failed." });
    }
  };

  return (
    <div className="space-y-8">
      {/* Active provider */}
      <Section title="Active provider" desc="Which AI brain runs your chat.">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {PROVIDERS.map((p) => {
            const active = settings.ai_provider === p.id;
            const hasKey = settings.keys_set[p.id];
            return (
              <button
                key={p.id}
                onClick={() => setProvider(p.id)}
                disabled={!hasKey}
                className={`flex items-center justify-between p-3 rounded-lg border transition-all text-left ${
                  active
                    ? "border-jcyan/60 bg-jcyan/10"
                    : hasKey
                    ? "border-white/15 hover:border-white/40"
                    : "border-white/5 opacity-40 cursor-not-allowed"
                }`}
              >
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-white font-medium text-sm">{p.label}</span>
                    {p.recommended && (
                      <span className="text-[9px] uppercase tracking-wider text-jcyan bg-jcyan/10 px-1.5 py-0.5 rounded border border-jcyan/30">
                        Recommended
                      </span>
                    )}
                  </div>
                  <div className="text-white/30 text-xs">{p.cheap}</div>
                </div>
                {active ? (
                  <span className="text-jcyan text-xs font-bold">✓</span>
                ) : !hasKey ? (
                  <span className="text-white/20 text-[10px]">Add key</span>
                ) : null}
              </button>
            );
          })}
        </div>
      </Section>

      {/* Tier */}
      <Section title="Intelligence tier" desc="Higher tiers think harder, cost more.">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
          {TIERS.map((t) => {
            const active = settings.default_model === t.id;
            return (
              <button
                key={t.id}
                onClick={() => update({ default_model: t.id })}
                className={`p-3 rounded-lg border text-left transition-all ${
                  active ? "border-jcyan/60 bg-jcyan/10" : "border-white/15 hover:border-white/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-white font-semibold text-sm">{t.label}</span>
                  <span className="text-[10px] text-jcyan/60">{t.cost}</span>
                </div>
                <p className="text-white/40 text-xs mt-1">{t.desc}</p>
              </button>
            );
          })}
        </div>
      </Section>

      {/* Personality */}
      <Section title="Personality" desc="How JARVIS phrases responses.">
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
          {PERSONALITIES.map((p) => {
            const active = settings.personality_mode === p.id;
            return (
              <button
                key={p.id}
                onClick={() => update({ personality_mode: p.id })}
                className={`p-3 rounded-lg border text-center transition-all ${
                  active ? "border-jcyan/60 bg-jcyan/10" : "border-white/15 hover:border-white/40"
                }`}
              >
                <div className="text-white text-sm font-medium">{p.label}</div>
                <div className="text-white/30 text-[10px] mt-0.5">{p.tag}</div>
              </button>
            );
          })}
        </div>
      </Section>

      {/* Response length */}
      <Section title="Response length" desc="Default verbosity. Personality wins ties.">
        <div className="flex gap-2">
          {(["brief", "detailed", "deep"] as const).map((r) => (
            <button
              key={r}
              onClick={() => update({ response_length: r })}
              className={`flex-1 py-2 rounded-lg border capitalize text-sm transition-all ${
                settings.response_length === r
                  ? "border-jcyan/60 bg-jcyan/10 text-jcyan"
                  : "border-white/15 text-white/60 hover:text-white"
              }`}
            >
              {r}
            </button>
          ))}
        </div>
      </Section>

      {/* Budget */}
      <Section title="Daily token budget" desc="Soft cap; you'll get an alert before the hard limit.">
        <div className="flex items-center gap-3">
          <input
            type="number"
            min={1000}
            max={100_000_000}
            step={10_000}
            defaultValue={settings.daily_token_budget}
            onBlur={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v) && v !== settings.daily_token_budget) update({ daily_token_budget: v });
            }}
            className="flex-1 bg-white/5 border border-white/15 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-jcyan/60"
          />
          <span className="text-white/40 text-xs">tokens / day</span>
        </div>
        <div className="mt-3 flex items-center gap-2">
          <span className="text-white/40 text-xs">Alert at</span>
          <input
            type="number"
            min={1}
            max={100}
            defaultValue={settings.budget_alert_pct}
            onBlur={(e) => {
              const v = parseInt(e.target.value, 10);
              if (!isNaN(v) && v !== settings.budget_alert_pct) update({ budget_alert_pct: v });
            }}
            className="w-20 bg-white/5 border border-white/15 rounded px-2 py-1 text-white text-sm focus:outline-none focus:border-jcyan/60"
          />
          <span className="text-white/40 text-xs">%</span>
        </div>
      </Section>
    </div>
  );
}

// ── Keys tab ────────────────────────────────────────────────────────────────

function KeysTab({
  settings, setSettings,
}: { settings: UserSettingsSnapshot | null; setSettings: (s: UserSettingsSnapshot) => void }) {
  const addToast = useJarvisStore((s) => s.addToast);
  if (!settings) return <Loading />;

  return (
    <div className="space-y-4">
      <p className="text-white/50 text-sm">
        Bring your own key. JARVIS encrypts at rest with Fernet. Keys never appear in chat,
        logs, or URLs. Get keys from your provider's dashboard.
      </p>
      {PROVIDERS.map((p) => (
        <KeyRow
          key={p.id}
          provider={p.id}
          label={p.label}
          masked={settings.keys_masked[p.id]}
          hasKey={settings.keys_set[p.id]}
          onSave={async (raw) => {
            try {
              const next = await SettingsAPI.putKeys({ [`${p.id}_api_key`]: raw } as any);
              setSettings(next);
              addToast({ type: "success", message: `${p.label} key saved.` });
            } catch (e) {
              addToast({ type: "error", message: (e as Error).message || "Save failed." });
            }
          }}
          onClear={async () => {
            try {
              const next = await SettingsAPI.putKeys({ [`${p.id}_api_key`]: "" } as any);
              setSettings(next);
              addToast({ type: "info", message: `${p.label} key removed.` });
            } catch (e) {
              addToast({ type: "error", message: (e as Error).message || "Failed." });
            }
          }}
          onTest={async (raw) => {
            try {
              const r = await SettingsAPI.testKey(p.id, raw);
              return r;
            } catch (e) {
              return { ok: false, error: (e as Error).message };
            }
          }}
        />
      ))}
      <KeyRow
        provider="elevenlabs"
        label="ElevenLabs (voice)"
        masked={settings.keys_masked["elevenlabs"]}
        hasKey={settings.keys_set["elevenlabs"]}
        onSave={async (raw) => {
          try {
            const next = await SettingsAPI.putKeys({ elevenlabs_api_key: raw });
            setSettings(next);
            addToast({ type: "success", message: "ElevenLabs key saved." });
          } catch (e) { addToast({ type: "error", message: (e as Error).message }); }
        }}
        onClear={async () => {
          const next = await SettingsAPI.putKeys({ elevenlabs_api_key: "" });
          setSettings(next);
          addToast({ type: "info", message: "ElevenLabs key removed." });
        }}
      />
    </div>
  );
}

function KeyRow({
  provider, label, masked, hasKey, onSave, onClear, onTest,
}: {
  provider: string;
  label: string;
  masked: string | null;
  hasKey: boolean;
  onSave: (raw: string) => Promise<void>;
  onClear: () => Promise<void>;
  onTest?: (raw: string) => Promise<{ ok: boolean; error?: string }>;
}) {
  const [editing, setEditing] = useState(false);
  const [val, setVal] = useState("");
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<null | { ok: boolean; error?: string }>(null);

  return (
    <div className="p-4 rounded-lg border border-white/10 bg-white/3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-white font-medium text-sm">{label}</span>
          {hasKey ? (
            <span className="text-[10px] uppercase tracking-wider text-green-400 bg-green-400/10 px-1.5 py-0.5 rounded border border-green-400/30">
              Set
            </span>
          ) : (
            <span className="text-[10px] uppercase tracking-wider text-white/30 bg-white/5 px-1.5 py-0.5 rounded border border-white/10">
              Not set
            </span>
          )}
        </div>
        {hasKey && !editing && (
          <button onClick={onClear} className="text-red-400/70 hover:text-red-400 text-xs">Remove</button>
        )}
      </div>
      {!editing ? (
        <div className="flex items-center justify-between mt-2">
          <span className="font-mono text-white/40 text-xs">{masked || "—"}</span>
          <button
            onClick={() => { setEditing(true); setVal(""); }}
            className="text-jcyan text-xs hover:underline"
          >
            {hasKey ? "Replace" : "Add key"}
          </button>
        </div>
      ) : (
        <div className="mt-2 space-y-2">
          <input
            type="password"
            autoFocus
            value={val}
            onChange={(e) => { setVal(e.target.value); setTestResult(null); }}
            placeholder={`Paste your ${label} key…`}
            className="w-full bg-black/40 border border-white/15 rounded px-3 py-2 text-white text-sm font-mono focus:outline-none focus:border-jcyan/60"
          />
          <div className="flex gap-2">
            <button
              onClick={async () => { await onSave(val); setEditing(false); setVal(""); setTestResult(null); }}
              disabled={val.length < 4}
              className="px-3 py-1.5 rounded bg-jcyan/15 border border-jcyan/40 text-jcyan text-xs font-bold uppercase tracking-wider hover:bg-jcyan/25 disabled:opacity-30"
            >
              Save
            </button>
            {onTest && (
              <button
                onClick={async () => {
                  setTesting(true);
                  setTestResult(null);
                  const r = await onTest(val);
                  setTestResult(r);
                  setTesting(false);
                }}
                disabled={val.length < 4 || testing}
                className="px-3 py-1.5 rounded border border-white/20 text-white/60 text-xs uppercase tracking-wider hover:text-white disabled:opacity-30"
              >
                {testing ? "Testing…" : "Test"}
              </button>
            )}
            <button
              onClick={() => { setEditing(false); setVal(""); setTestResult(null); }}
              className="px-3 py-1.5 rounded text-white/40 text-xs hover:text-white"
            >
              Cancel
            </button>
            {testResult && (
              <span className={`text-xs ml-auto self-center ${testResult.ok ? "text-green-400" : "text-red-400"}`}>
                {testResult.ok ? "✓ Key valid" : `✕ ${testResult.error || "Invalid"}`}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Context tab ─────────────────────────────────────────────────────────────

function ContextTab({
  context, setContext,
}: { context: UserContextSnapshot | null; setContext: (c: UserContextSnapshot) => void }) {
  const addToast = useJarvisStore((s) => s.addToast);
  if (!context) return <Loading />;

  const save = async (patch: Partial<UserContextSnapshot>) => {
    try {
      const next = await ContextAPI.put(patch);
      setContext(next);
      addToast({ type: "success", message: "Context saved." });
    } catch (e) {
      addToast({ type: "error", message: (e as Error).message || "Save failed." });
    }
  };

  return (
    <div className="space-y-5">
      <p className="text-white/50 text-sm">
        JARVIS injects this into every prompt. Be specific — the more it knows about you,
        the less generic its answers.
      </p>
      <TextField
        label="About me"
        placeholder="Who you are, your company, your role…"
        value={context.about_me || ""}
        onSave={(v) => save({ about_me: v })}
        rows={3}
      />
      <TextField
        label="Communication style"
        placeholder="How JARVIS should phrase things (direct, structured, friendly…)"
        value={context.communication_style || ""}
        onSave={(v) => save({ communication_style: v })}
        rows={2}
      />
      <TextField
        label="Top priorities"
        placeholder="The 2–4 things that actually matter to you right now"
        value={context.priorities || ""}
        onSave={(v) => save({ priorities: v })}
        rows={2}
      />
      <TextField
        label="Business context"
        placeholder="Industry, stage, customer base, key constraints"
        value={context.business_context || ""}
        onSave={(v) => save({ business_context: v })}
        rows={3}
      />
      <Section
        title="Team members"
        desc={`${context.team_members?.length || 0} people. JARVIS knows who to defer to.`}
      >
        <div className="space-y-2">
          {(context.team_members || []).map((m, i) => (
            <div key={i} className="flex items-center gap-2 p-2 border border-white/10 rounded">
              <span className="text-white text-sm font-medium">{m.name}</span>
              <span className="text-white/40 text-xs">{m.role || "—"}</span>
              <span className="ml-auto text-white/30 text-xs italic">{m.relationship || ""}</span>
            </div>
          ))}
          <p className="text-white/30 text-xs">Team CRUD UI coming in a follow-up. Edit via /api/context for now.</p>
        </div>
      </Section>
    </div>
  );
}

// ── Integrations tab ────────────────────────────────────────────────────────

function IntegrationsTab() {
  return (
    <div className="space-y-4">
      <p className="text-white/50 text-sm">
        Manage external service connections (Gmail, Outlook, Slack, Linear, Jira, etc.)
        from the JARVIS HUD by clicking the ⚙ Integrations chip — those flows already
        handle the OAuth handshake. This tab links there for convenience.
      </p>
      <div className="p-4 rounded-lg border border-jcyan/30 bg-jcyan/5 text-jcyan text-sm">
        Tip: close Settings, open Profile → Integrations.
      </div>
    </div>
  );
}

// ── GitHub tab ──────────────────────────────────────────────────────────────

function GitHubTab({
  settings, setSettings,
}: { settings: UserSettingsSnapshot | null; setSettings: (s: UserSettingsSnapshot) => void }) {
  const addToast = useJarvisStore((s) => s.addToast);
  const [url, setUrl] = useState("");
  useEffect(() => { setUrl(settings?.github_repo_url || ""); }, [settings]);
  if (!settings) return <Loading />;

  const saveRepo = async () => {
    try {
      const next = await SettingsAPI.putKeys({ github_repo_url: url });
      setSettings(next);
      addToast({ type: "success", message: "Repo URL saved." });
    } catch (e) { addToast({ type: "error", message: (e as Error).message }); }
  };

  return (
    <div className="space-y-5">
      <p className="text-white/50 text-sm">
        Let JARVIS push commits, open PRs, and read repo state on your behalf.
        Create a PAT with <code className="text-jcyan/80">repo</code> scope at
        <a href="https://github.com/settings/tokens" target="_blank" rel="noopener noreferrer"
           className="text-jcyan hover:underline ml-1">github.com/settings/tokens</a>.
      </p>
      <div>
        <label className="block text-white/40 text-xs uppercase tracking-wider mb-1.5">
          Repository URL
        </label>
        <div className="flex gap-2">
          <input
            type="text"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            placeholder="https://github.com/you/yourrepo"
            className="flex-1 bg-white/5 border border-white/15 rounded px-3 py-2 text-white text-sm focus:outline-none focus:border-jcyan/60"
          />
          <button
            onClick={saveRepo}
            className="px-4 py-2 rounded bg-jcyan/15 border border-jcyan/40 text-jcyan text-xs font-bold uppercase"
          >Save</button>
        </div>
      </div>
      <KeyRow
        provider="github_pat"
        label="GitHub PAT"
        masked={settings.keys_masked["github_pat"]}
        hasKey={!!settings.keys_set["github_pat"]}
        onSave={async (raw) => {
          try {
            const next = await SettingsAPI.putKeys({ github_pat: raw });
            setSettings(next);
            addToast({ type: "success", message: "GitHub PAT saved." });
          } catch (e) { addToast({ type: "error", message: (e as Error).message }); }
        }}
        onClear={async () => {
          const next = await SettingsAPI.putKeys({ github_pat: "" });
          setSettings(next);
          addToast({ type: "info", message: "GitHub PAT removed." });
        }}
      />
    </div>
  );
}

// ── Account tab ─────────────────────────────────────────────────────────────

function AccountTab() {
  const logout = useJarvisStore((s) => s.logout);
  return (
    <div className="space-y-6">
      <Section title="Sign out" desc="End the current session on this device.">
        <button
          onClick={logout}
          className="px-4 py-2 rounded border border-white/20 text-white/70 text-sm hover:border-white/40 hover:text-white"
        >Sign out</button>
      </Section>
      <Section title="Password" desc="Change your account password (coming soon).">
        <button disabled className="px-4 py-2 rounded border border-white/10 text-white/30 text-sm cursor-not-allowed">
          Change password — pending
        </button>
      </Section>
      <Section title="Export data" desc="Download all your data as JSON (coming soon).">
        <button disabled className="px-4 py-2 rounded border border-white/10 text-white/30 text-sm cursor-not-allowed">
          Export — pending
        </button>
      </Section>
      <Section title="Danger zone" desc="Delete your account and all data. Cannot be undone.">
        <button disabled className="px-4 py-2 rounded border border-red-500/20 text-red-400/40 text-sm cursor-not-allowed">
          Delete account — pending
        </button>
      </Section>
    </div>
  );
}

// ── Shared bits ─────────────────────────────────────────────────────────────

function Section({ title, desc, children }: { title: string; desc?: string; children: React.ReactNode }) {
  return (
    <div>
      <h4 className="text-white text-sm font-semibold tracking-wide">{title}</h4>
      {desc && <p className="text-white/40 text-xs mb-3">{desc}</p>}
      {children}
    </div>
  );
}

function TextField({
  label, value, placeholder, onSave, rows = 2,
}: { label: string; value: string; placeholder: string; onSave: (v: string) => void; rows?: number }) {
  const [val, setVal] = useState(value);
  useEffect(() => setVal(value), [value]);
  return (
    <div>
      <label className="block text-white/40 text-xs uppercase tracking-wider mb-1.5">{label}</label>
      <textarea
        value={val}
        rows={rows}
        onChange={(e) => setVal(e.target.value)}
        onBlur={() => { if (val !== value) onSave(val); }}
        placeholder={placeholder}
        className="w-full bg-white/5 border border-white/15 rounded px-3 py-2 text-white text-sm resize-y focus:outline-none focus:border-jcyan/60"
      />
    </div>
  );
}

function Loading() {
  return <div className="text-white/40 text-sm">Loading…</div>;
}
