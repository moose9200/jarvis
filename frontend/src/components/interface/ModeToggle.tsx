import { useJarvisStore } from "../../store/jarvisStore";

export function ModeToggle() {
  const mode = useJarvisStore((s) => s.mode);
  const setMode = useJarvisStore((s) => s.setMode);
  return (
    <button
      onClick={() => setMode(mode === "voice" ? "text" : "voice")}
      className="absolute top-4 left-1/2 -translate-x-1/2 pointer-events-auto px-3 py-1 text-xs uppercase tracking-widest border border-jcyan/60 text-jcyan rounded-full bg-black/40 backdrop-blur"
    >
      Mode · {mode}
    </button>
  );
}
