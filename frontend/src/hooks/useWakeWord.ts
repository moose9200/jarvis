import { useEffect, useRef } from "react";

interface Opts {
  enabled: boolean;
  phrase?: string;
  onWake: () => void;
}

export function useWakeWord({ enabled, phrase = "hey jarvis", onWake }: Opts) {
  const recRef = useRef<any>(null);

  useEffect(() => {
    if (!enabled) return;
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = "en-US";
    rec.onresult = (e: any) => {
      const text = Array.from(e.results)
        .map((r: any) => r[0].transcript)
        .join(" ")
        .toLowerCase();
      if (text.includes(phrase)) onWake();
    };
    rec.onend = () => {
      if (enabled) try { rec.start(); } catch {}
    };
    try { rec.start(); } catch {}
    recRef.current = rec;
    return () => {
      try { rec.stop(); } catch {}
    };
  }, [enabled, phrase, onWake]);
}
