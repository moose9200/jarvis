import { FormEvent, useState } from "react";
import { motion } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";

export function ChatOverlay() {
  const chat = useJarvisStore((s) => s.chat);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (!input.trim() || busy) return;
    setBusy(true);
    const v = input;
    setInput("");
    try {
      await sendChat(v);
    } finally {
      setBusy(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="pointer-events-auto w-[40rem] max-w-[80vw] h-[26rem] bg-black/60 backdrop-blur-md border border-jcyan/50 rounded-xl flex flex-col"
    >
      <div className="px-4 py-2 text-xs uppercase tracking-widest text-jcyan border-b border-jcyan/30">
        JARVIS Chat
      </div>
      <div className="flex-1 overflow-auto p-4 space-y-3 text-sm">
        {chat.length === 0 && (
          <div className="text-white/40">Awaiting orders, boss.</div>
        )}
        {chat.map((t, i) => (
          <div key={i} className={t.role === "user" ? "text-white" : "text-jcyan"}>
            <span className="opacity-50 mr-2">{t.role === "user" ? "you:" : "jarvis:"}</span>
            {t.text}
          </div>
        ))}
        {busy && <div className="text-jcyan opacity-70">jarvis: thinking…</div>}
      </div>
      <form onSubmit={submit} className="border-t border-jcyan/30 p-2 flex gap-2">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask JARVIS..."
          className="flex-1 bg-transparent outline-none px-2 py-1 text-white"
          autoFocus
        />
        <button
          type="submit"
          disabled={busy}
          className="px-3 py-1 border border-jcyan text-jcyan rounded hover:bg-jcyan/10 disabled:opacity-30"
        >
          Send
        </button>
      </form>
    </motion.div>
  );
}
