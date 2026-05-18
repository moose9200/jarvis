import { useCallback, useRef } from "react";

const KEY = import.meta.env.VITE_ELEVENLABS_KEY;

export function useVoice() {
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const listen = useCallback((): Promise<string> => {
    return new Promise((resolve, reject) => {
      const SR =
        (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (!SR) return reject(new Error("no STT"));
      const rec = new SR();
      rec.lang = "en-US";
      rec.interimResults = false;
      rec.continuous = false;
      rec.onresult = (e: any) => resolve(e.results[0][0].transcript);
      rec.onerror = (e: any) => reject(e);
      rec.start();
    });
  }, []);

  const speak = useCallback(async (text: string) => {
    if (!KEY) return;
    const r = await fetch(
      "https://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB",
      {
        method: "POST",
        headers: {
          "xi-api-key": KEY,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          text,
          model_id: "eleven_monolingual_v1",
          voice_settings: { stability: 0.4, similarity_boost: 0.7 },
        }),
      }
    );
    if (!r.ok) return;
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    if (audioRef.current) audioRef.current.pause();
    audioRef.current = new Audio(url);
    await audioRef.current.play();
  }, []);

  return { listen, speak };
}
