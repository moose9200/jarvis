import { useCallback, useEffect, useState } from "react";
import { HUDScene } from "./components/hud/HUDScene";
import { CalendarPanel } from "./components/panels/CalendarPanel";
import { EmailPanel } from "./components/panels/EmailPanel";
import { TaskPanel } from "./components/panels/TaskPanel";
import { ProjectPanel } from "./components/panels/ProjectPanel";
import { ChatOverlay } from "./components/interface/ChatOverlay";
import { VoiceVisualizer } from "./components/interface/VoiceVisualizer";
import { ModeToggle } from "./components/interface/ModeToggle";
import { IntegrationsModal } from "./components/onboarding/IntegrationsModal";
import { AuthPage } from "./components/auth/AuthPage";
import { useJarvisStore } from "./store/jarvisStore";
import { useWakeWord } from "./hooks/useWakeWord";
import { useVoice } from "./hooks/useVoice";

export default function App() {
  const isAuthenticated = useJarvisStore((s) => s.isAuthenticated);
  const logout = useJarvisStore((s) => s.logout);
  const mode = useJarvisStore((s) => s.mode);
  const setWakeState = useJarvisStore((s) => s.setWakeState);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const connectors = useJarvisStore((s) => s.connectors);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);
  const { listen, speak } = useVoice();
  const [showIntegrations, setShowIntegrations] = useState(false);

  // All hooks must run unconditionally before any conditional return
  useEffect(() => {
    if (isAuthenticated) fetchConnectors();
  }, [fetchConnectors, isAuthenticated]);

  const runVoiceTurn = useCallback(async () => {
    setWakeState("listening");
    try {
      const utterance = await listen();
      const reply = await sendChat(utterance);
      await speak(reply);
    } catch {
      // ignore
    } finally {
      setWakeState("idle");
    }
  }, [listen, sendChat, speak, setWakeState]);

  useWakeWord({
    enabled: isAuthenticated && mode === "voice",
    phrase: "hey jarvis",
    onWake: runVoiceTurn,
  });

  // Auth gate — after all hooks
  if (!isAuthenticated) return <AuthPage />;

  const connectedCount = connectors.filter((c) => c.connected).length;

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <HUDScene />

      {/* Panels */}
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-4 p-4 pointer-events-none">
        <CalendarPanel />
        <EmailPanel />
        <TaskPanel />
        <ProjectPanel />
      </div>

      {/* Chat / Voice center */}
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {mode === "voice" ? <VoiceVisualizer /> : <ChatOverlay />}
      </div>

      {/* Mode toggle top-center */}
      <ModeToggle />

      {/* Top-right controls */}
      <div className="absolute top-4 right-4 z-40 flex items-center gap-2 pointer-events-auto">
        {/* Integrations button */}
        <button
          onClick={() => setShowIntegrations(true)}
          className="flex items-center gap-2 px-3 py-2 rounded-lg border border-[#00d4ff]/40 bg-black/60 backdrop-blur text-[#00d4ff] text-xs font-bold uppercase tracking-widest hover:bg-[#00d4ff]/10 transition-colors"
        >
          <span>⚙</span>
          <span>Integrations</span>
          <span className={`ml-1 px-1.5 py-0.5 rounded text-[10px] ${connectedCount > 0 ? "bg-[#00d4ff]/20 text-[#00d4ff]" : "bg-white/10 text-white/50"}`}>
            {connectedCount}/{connectors.length}
          </span>
        </button>

        {/* Logout button */}
        <button
          onClick={logout}
          className="px-3 py-2 rounded-lg border border-white/10 bg-black/60 backdrop-blur text-white/40 text-xs font-bold uppercase tracking-widest hover:text-white/70 hover:border-white/30 transition-colors"
          title="Sign out"
        >
          ⏻
        </button>
      </div>

      {/* Integrations modal */}
      {showIntegrations && (
        <IntegrationsModal onClose={() => { setShowIntegrations(false); fetchConnectors(); }} />
      )}
    </div>
  );
}
