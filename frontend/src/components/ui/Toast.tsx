import { AnimatePresence, motion } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";

const ICONS = {
  success: "✓",
  error: "✕",
  info: "ℹ",
  warning: "⚠",
};

const COLORS = {
  success: "border-green-400/50 bg-green-400/10 text-green-300",
  error: "border-red-400/50 bg-red-400/10 text-red-300",
  info: "border-jcyan/50 bg-jcyan/10 text-jcyan",
  warning: "border-yellow-400/50 bg-yellow-400/10 text-yellow-300",
};

export function ToastStack() {
  const toasts = useJarvisStore((s) => s.toasts);
  const removeToast = useJarvisStore((s) => s.removeToast);

  return (
    <div className="fixed top-16 right-4 z-[200] flex flex-col gap-2 pointer-events-none">
      <AnimatePresence>
        {toasts.map((t) => (
          <motion.div
            key={t.id}
            initial={{ opacity: 0, x: 60, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 60, scale: 0.9 }}
            transition={{ type: "spring", stiffness: 400, damping: 30 }}
            className={`pointer-events-auto flex items-start gap-3 px-4 py-3 rounded-lg border backdrop-blur-md shadow-lg text-sm max-w-xs ${COLORS[t.type]}`}
          >
            <span className="font-bold mt-0.5 shrink-0">{ICONS[t.type]}</span>
            <span className="flex-1 leading-relaxed">{t.message}</span>
            <button
              onClick={() => removeToast(t.id)}
              className="shrink-0 opacity-50 hover:opacity-100 transition-opacity text-xs mt-0.5"
            >
              ✕
            </button>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}
