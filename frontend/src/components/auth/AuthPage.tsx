import { useState, FormEvent } from "react";
import { useJarvisStore } from "../../store/jarvisStore";

export function AuthPage() {
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const login = useJarvisStore((s) => s.login);
  const register = useJarvisStore((s) => s.register);
  const authError = useJarvisStore((s) => s.authError);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setLoading(true);
    if (mode === "login") {
      await login(email, password);
    } else {
      await register(email, password);
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen w-screen bg-[#020510] flex items-center justify-center overflow-hidden relative">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-10"
        style={{
          backgroundImage:
            "linear-gradient(rgba(0,212,255,0.3) 1px, transparent 1px), linear-gradient(90deg, rgba(0,212,255,0.3) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
        }}
      />

      {/* Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] rounded-full bg-[#00d4ff]/5 blur-3xl pointer-events-none" />

      {/* Card */}
      <div className="relative z-10 w-full max-w-sm mx-4">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full border-2 border-[#00d4ff]/60 bg-[#00d4ff]/10 mb-4 shadow-lg shadow-[#00d4ff]/20">
            <span className="text-2xl">⚡</span>
          </div>
          <h1 className="text-[#00d4ff] text-3xl font-bold tracking-[0.3em] uppercase">JARVIS</h1>
          <p className="text-white/30 text-xs tracking-widest uppercase mt-1">
            Just A Rather Very Intelligent System
          </p>
        </div>

        {/* Form card */}
        <div className="bg-[#0a0e1a]/90 backdrop-blur border border-[#00d4ff]/30 rounded-xl p-6 shadow-2xl shadow-[#00d4ff]/10">
          <h2 className="text-white font-semibold text-sm uppercase tracking-widest mb-5 text-center">
            {mode === "login" ? "Sign In" : "Create Account"}
          </h2>

          {authError && (
            <div className="mb-4 px-3 py-2 rounded bg-red-500/10 border border-red-500/30 text-red-400 text-xs">
              {authError}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-white/40 text-xs uppercase tracking-wider mb-1.5">
                Email
              </label>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="boss@example.com"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder-white/20 focus:outline-none focus:border-[#00d4ff]/60 focus:bg-[#00d4ff]/5 transition-colors"
              />
            </div>

            <div>
              <label className="block text-white/40 text-xs uppercase tracking-wider mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2.5 text-white text-sm placeholder-white/20 focus:outline-none focus:border-[#00d4ff]/60 focus:bg-[#00d4ff]/5 transition-colors"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-2.5 rounded-lg bg-[#00d4ff]/15 border border-[#00d4ff]/50 text-[#00d4ff] text-sm font-bold uppercase tracking-widest hover:bg-[#00d4ff]/25 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-[#00d4ff]/10"
            >
              {loading ? "..." : mode === "login" ? "Sign In" : "Create Account"}
            </button>
          </form>

          <div className="mt-4 text-center">
            <button
              onClick={() => setMode(mode === "login" ? "register" : "login")}
              className="text-white/30 text-xs hover:text-white/60 transition-colors"
            >
              {mode === "login"
                ? "Don't have an account? Register"
                : "Already have an account? Sign in"}
            </button>
          </div>
        </div>

        <p className="text-white/15 text-xs text-center mt-4 tracking-wider">
          YOUR PERSONAL AI ASSISTANT
        </p>
      </div>
    </div>
  );
}
