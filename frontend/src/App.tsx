import { useCallback, useEffect } from "react";
import { HUDScene } from "./components/hud/HUDScene";
import { CalendarPanel } from "./components/panels/CalendarPanel";
import { EmailPanel } from "./components/panels/EmailPanel";
import { TaskPanel } from "./components/panels/TaskPanel";
import { ProjectPanel } from "./components/panels/ProjectPanel";
import { ChatOverlay } from "./components/interface/ChatOverlay";
import { VoiceVisualizer } from "./components/interface/VoiceVisualizer";
import { ModeToggle } from "./components/interface/ModeToggle";
import { ConnectorCards } from "./components/onboarding/ConnectorCards";
import { useJarvisStore } from "./store/jarvisStore";
import { useWakeWord } from "./hooks/useWakeWord";
import { useVoice } from "./hooks/useVoice";

export default function App() {
  const mode = useJarvisStore((s) => s.mode);
  const setWakeState = useJarvisStore((s) => s.setWakeState);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const connectors = useJarvisStore((s) => s.connectors);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);
  const { listen, speak } = useVoice();

  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

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
    enabled: mode === "voice",
    phrase: "hey jarvis",
    onWake: runVoiceTurn,
  });

  const noneConnected = connectors.length > 0 && !connectors.some((c) => c.connected);

  return (
    <div className="relative w-screen h-screen overflow-hidden">
      <HUDScene />
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2 gap-4 p-4 pointer-events-none">
        <CalendarPanel />
        <EmailPanel />
        <TaskPanel />
        <ProjectPanel />
      </div>
      <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
        {mode === "voice" ? <VoiceVisualizer /> : <ChatOverlay />}
      </div>
      <ModeToggle />
      {noneConnected && (
        <div className="absolute bottom-4 right-4 max-w-md pointer-events-auto bg-black/70 border border-jcyan/50 rounded-lg backdrop-blur">
          <div className="px-4 py-2 text-jcyan text-xs uppercase tracking-widest border-b border-jcyan/30">
            Connect Services
          </div>
          <ConnectorCards />
        </div>
      )}
    </div>
  );
}
