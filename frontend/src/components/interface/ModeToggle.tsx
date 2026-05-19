import { useJarvisStore } from "../../store/jarvisStore";

export function ModeToggle() {
  const mode = useJarvisStore((s) => s.mode);
  const setMode = useJarvisStore((s) => s.setMode);
  return (
    <div className="flex items-center gap-0 bg-black/40 border border-white/15 rounded-full p-0.5 backdrop-blur">
      <button
        onClick={() => setMode("voice")}
        className={`px-4 py-1.5 text-xs uppercase tracking-widest rounded-full transition-all font-bold ${
          mode === "voice"
            ? "bg-jcyan/20 text-jcyan border border-jcyan/40 shadow-lg shadow-jcyan/20"
            : "text-white/30 hover:text-white/60"
        }`}
      >
        🎙 Voice
      </button>
      <button
        onClick={() => setMode("text")}
        className={`px-4 py-1.5 text-xs uppercase tracking-widest rounded-full transition-all font-bold ${
          mode === "text"
            ? "bg-jcyan/20 text-jcyan border border-jcyan/40 shadow-lg shadow-jcyan/20"
            : "text-white/30 hover:text-white/60"
        }`}
      >
        ⌨ Text
      </button>
    </div>
  );
}
