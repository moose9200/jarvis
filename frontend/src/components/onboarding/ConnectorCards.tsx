import { useEffect } from "react";
import { useJarvisStore } from "../../store/jarvisStore";

const API = import.meta.env.VITE_API_BASE || "";

export function ConnectorCards() {
  const connectors = useJarvisStore((s) => s.connectors);
  const fetchConnectors = useJarvisStore((s) => s.fetchConnectors);
  useEffect(() => {
    fetchConnectors();
  }, [fetchConnectors]);

  return (
    <div className="grid grid-cols-3 gap-3 p-4">
      {connectors.map((c) => (
        <a
          key={c.name}
          href={`${API}/api/auth/${c.name}/start`}
          className={`p-3 border rounded ${
            c.connected ? "border-jcyan text-jcyan" : "border-white/30 text-white/70"
          }`}
        >
          <div className="font-bold">{c.display}</div>
          <div className="text-xs">{c.connected ? "connected" : "connect"}</div>
        </a>
      ))}
    </div>
  );
}
