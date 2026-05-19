import { useCallback, useEffect, useState } from "react";
import { HUDScene } from "./components/hud/HUDScene";
import { CalendarPanel } from "./components/panels/CalendarPanel";
import { EmailPanel } from "./components/panels/EmailPanel";
import { TaskPanel } from "./components/panels/TaskPanel";
import { ProjectPanel } from "./components/panels/ProjectPanel";
import { DraggableChat } from "./components/interface/DraggableChat";
import { VoiceVisualizer } from "./components/interface/VoiceVisualizer";
import { ModeToggle } from "./components/interface/ModeToggle";
import { IntegrationsModal } from "./components/onboarding/IntegrationsModal";
import { AuthPage } from "./components/auth/AuthPage";
import { ToastStack } from "./components/ui/Toast";
import { ProfileDropdown } from "./components/ui/ProfileDropdown";
import { DashboardCustomizer } from "./components/ui/DashboardCustomizer";
import { useJarvisStore } from "./store/jarvisStore";
import { useWakeWord } from "./hooks/useWakeWord";
import { useVoice } from "./hooks/useVoice";

// ── Clock ──────────────────────────────────────────────────────────────────────
function Clock() {
  const [time, setTime] = useState(new Date());
  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);
  const day = time.toLocaleDateString([], { weekday: "short", month: "short", day: "numeric" });
  const hhmm = time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return (
    <div className="flex flex-col items-start leading-tight select-none">
      <span className="text-white font-bold text-sm tracking-wide">{hhmm}</span>
      <span className="text-white/30 text-[10px] uppercase tracking-widest">{day}</span>
    </div>
  );
}

// ── Main App ──────────────────────────────────────────────────────────────────
export default function App() {
  const isAuthenticated = useJarvisStore((s) => s.isAuthenticated);
  const mode = useJarvisStore((s) => s.mode);
  const setWakeState = useJarvisStore((s) => s.setWakeState);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);
  const panelVisibility = useJarvisStore((s) => s.panelVisibility);
  const addToast = useJarvisStore((s) => s.addToast);
  const { listen, speak } = useVoice();

  const [showIntegrations, setShowIntegrations] = useState(false);
  const [showCustomizer, setShowCustomizer] = useState(false);

  // All hooks before conditional return
  useEffect(() => {
    if (isAuthenticated) fetchConnectors();
  }, [fetchConnectors, isAuthenticated]);

  // Handle OAuth return params (?connected=X or ?error=not_configured&provider=X)
  useEffect(() => {
    if (!isAuthenticated) return;
    const params = new URLSearchParams(window.location.search);
    const connected = params.get("connected");
    const error = params.get("error");
    const provider = params.get("provider");

    if (connected) {
      addToast({ type: "success", message: `✓ ${connected.charAt(0).toUpperCase() + connected.slice(1)} connected successfully!` });
      fetchConnectors();
      window.history.replaceState({}, "", "/");
    }
    if (error === "not_configured" && provider) {
      addToast({ type: "error", message: `${provider} is not configured. Add credentials to backend/.env to enable.` });
      window.history.replaceState({}, "", "/");
    }
  }, [isAuthenticated, addToast, fetchConnectors]);

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

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      {/* 3D background */}
      <HUDScene />

      {/* ── Top bar ──────────────────────────────────────────────────────────── */}
      <div className="absolute top-0 left-0 right-0 z-40 flex items-center gap-3 px-4 py-3 pointer-events-auto">
        {/* Left: Logo + clock */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2">
            <div className="w-7 h-7 rounded-full border border-jcyan/60 bg-jcyan/10 flex items-center justify-center text-jcyan text-xs font-bold">
              J
            </div>
            <span className="text-jcyan text-xs font-bold uppercase tracking-[0.25em] hidden sm:block">
              JARVIS
            </span>
          </div>
          <div className="w-px h-6 bg-white/10" />
          <Clock />
        </div>

        {/* Center: Mode toggle */}
        <div className="flex-1 flex justify-center">
          <ModeToggle />
        </div>

        {/* Right: Profile dropdown */}
        <ProfileDropdown
          onOpenIntegrations={() => setShowIntegrations(true)}
          onOpenCustomizer={() => setShowCustomizer(true)}
        />
      </div>

      {/* ── Panels grid ──────────────────────────────────────────────────────── */}
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-3 p-3 pt-16 pointer-events-none">
        {panelVisibility.calendar && <CalendarPanel />}
        {panelVisibility.email    && <EmailPanel />}
        {panelVisibility.tasks    && <TaskPanel />}
        {panelVisibility.projects && <ProjectPanel />}
      </div>

      {/* ── Chat / Voice center ──────────────────────────────────────────────── */}
      {mode === "voice" ? (
        <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
          <VoiceVisualizer />
        </div>
      ) : (
        <DraggableChat />
      )}

      {/* ── Modals ───────────────────────────────────────────────────────────── */}
      {showIntegrations && (
        <IntegrationsModal
          onClose={() => { setShowIntegrations(false); fetchConnectors(); }}
        />
      )}
      <DashboardCustomizer
        open={showCustomizer}
        onClose={() => setShowCustomizer(false)}
      />

      {/* ── Toast notifications ──────────────────────────────────────────────── */}
      <ToastStack />
    </div>
  );
}
