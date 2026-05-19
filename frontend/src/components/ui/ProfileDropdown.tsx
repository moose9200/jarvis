import { useEffect, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useJarvisStore } from "../../store/jarvisStore";

interface Props {
  onOpenIntegrations: () => void;
  onOpenCustomizer: () => void;
}

export function ProfileDropdown({ onOpenIntegrations, onOpenCustomizer }: Props) {
  const user = useJarvisStore((s) => s.user);
  const token = useJarvisStore((s) => s.token);
  const logout = useJarvisStore((s) => s.logout);
  const [open, setOpen] = useState(false);
  const [userEmail, setUserEmail] = useState(user?.email || "");
  const ref = useRef<HTMLDivElement>(null);

  // Fetch /me if we have a token but no user email
  useEffect(() => {
    if (token && !userEmail) {
      fetch(`${import.meta.env.VITE_API_BASE || ""}/api/users/me`, {
        headers: { Authorization: `Bearer ${token}` },
      })
        .then((r) => r.json())
        .then((d) => d.email && setUserEmail(d.email))
        .catch(() => {});
    }
  }, [token, userEmail]);

  // Close on outside click
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const initial = userEmail ? userEmail[0].toUpperCase() : "J";
  const displayEmail = userEmail || "Loading...";

  return (
    <div ref={ref} className="relative">
      {/* Avatar button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative w-9 h-9 rounded-full border-2 border-jcyan/60 bg-jcyan/10 flex items-center justify-center text-jcyan font-bold text-sm hover:border-jcyan hover:bg-jcyan/20 transition-all shadow-lg shadow-jcyan/20"
        title="Profile"
      >
        {initial}
        <span className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full bg-green-400 border-2 border-[#020510]" />
      </button>

      <AnimatePresence>
        {open && (
          <motion.div
            initial={{ opacity: 0, y: -8, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -8, scale: 0.95 }}
            transition={{ type: "spring", stiffness: 500, damping: 35 }}
            className="absolute top-12 right-0 w-64 bg-[#0a0e1a]/95 backdrop-blur-md border border-jcyan/30 rounded-xl shadow-2xl shadow-black/60 overflow-hidden z-[100]"
          >
            {/* User info */}
            <div className="px-4 py-4 border-b border-white/10">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full border-2 border-jcyan/60 bg-jcyan/10 flex items-center justify-center text-jcyan font-bold shrink-0">
                  {initial}
                </div>
                <div className="min-w-0">
                  <div className="text-white text-sm font-semibold truncate">
                    {displayEmail.split("@")[0]}
                  </div>
                  <div className="text-white/40 text-xs truncate">{displayEmail}</div>
                </div>
              </div>
            </div>

            {/* Menu items */}
            <div className="py-1">
              <MenuBtn
                icon="⚙"
                label="Integrations"
                desc="Connect services"
                onClick={() => { setOpen(false); onOpenIntegrations(); }}
              />
              <MenuBtn
                icon="▦"
                label="Customize Dashboard"
                desc="Show/hide panels"
                onClick={() => { setOpen(false); onOpenCustomizer(); }}
              />
              <MenuBtn
                icon="🔑"
                label="Keyboard Shortcuts"
                desc="⌘K chat · Esc close"
                onClick={() => setOpen(false)}
                disabled
              />
            </div>

            {/* Divider + logout */}
            <div className="border-t border-white/10 py-1">
              <button
                onClick={() => { setOpen(false); logout(); }}
                className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-red-500/10 transition-colors group"
              >
                <span className="text-red-400/70 group-hover:text-red-400 transition-colors">⏻</span>
                <span className="text-white/50 group-hover:text-red-300 text-sm transition-colors">Sign Out</span>
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function MenuBtn({
  icon, label, desc, onClick, disabled,
}: {
  icon: string; label: string; desc: string; onClick: () => void; disabled?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-white/5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed group"
    >
      <span className="text-jcyan/60 group-hover:text-jcyan transition-colors text-base w-5 text-center shrink-0">
        {icon}
      </span>
      <div className="min-w-0">
        <div className="text-white/80 text-sm font-medium group-hover:text-white transition-colors">
          {label}
        </div>
        <div className="text-white/30 text-xs">{desc}</div>
      </div>
    </button>
  );
}
