import { HUDScene } from "./components/hud/HUDScene";
import { CalendarPanel } from "./components/panels/CalendarPanel";
import { EmailPanel } from "./components/panels/EmailPanel";
import { TaskPanel } from "./components/panels/TaskPanel";
import { ProjectPanel } from "./components/panels/ProjectPanel";
import { ChatOverlay } from "./components/interface/ChatOverlay";
import { VoiceVisualizer } from "./components/interface/VoiceVisualizer";
import { ModeToggle } from "./components/interface/ModeToggle";
import { useJarvisStore } from "./store/jarvisStore";

export default function App() {
  const mode = useJarvisStore((s) => s.mode);
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
    </div>
  );
}
