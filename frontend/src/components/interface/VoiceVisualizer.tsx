import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { useJarvisStore } from "../../store/jarvisStore";

export function VoiceVisualizer() {
  const wake = useJarvisStore((s) => s.wakeState);
  const [bars, setBars] = useState<number[]>(Array(24).fill(0.2));

  useEffect(() => {
    const t = setInterval(() => {
      const active = wake !== "idle";
      setBars((prev) =>
        prev.map(() => (active ? 0.2 + Math.random() * 0.8 : 0.1 + Math.random() * 0.15))
      );
    }, 100);
    return () => clearInterval(t);
  }, [wake]);

  return (
    <div className="pointer-events-none flex items-end gap-1 h-32 mt-72">
      {bars.map((v, i) => (
        <motion.div
          key={i}
          animate={{ height: `${v * 100}%` }}
          transition={{ duration: 0.1 }}
          className="w-1.5 bg-jcyan rounded"
        />
      ))}
    </div>
  );
}
