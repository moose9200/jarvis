import { useEffect, useState } from "react";
import ReactMarkdown from "react-markdown";

const API = (import.meta as any).env?.VITE_API_BASE || "http://localhost:8000";

const DOC_LABELS: Record<string, string> = {
  privacy: "Privacy Policy",
  terms: "Terms of Service",
  cookies: "Cookie Policy",
  aup: "Acceptable Use Policy",
  "ai-disclosure": "AI Disclosure",
};

/**
 * Renders one of the public legal documents fetched from
 * `/api/legal/<slug>`. The router exposes raw markdown; we render with
 * react-markdown so headings + tables come out cleanly. No auth — these
 * URLs are part of the OAuth verification submission (USER TODO #10) so
 * they MUST be reachable anonymously.
 */
export default function LegalPage({ slug }: { slug: string }) {
  const [body, setBody] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    setBody(null);
    setError(null);
    fetch(`${API}/api/legal/${slug}`)
      .then(async (r) => {
        if (!alive) return;
        if (!r.ok) {
          setError(`HTTP ${r.status} — document not found`);
          return;
        }
        const text = await r.text();
        if (alive) setBody(text);
      })
      .catch((e) => {
        if (alive) setError(e?.message || "network error");
      });
    return () => {
      alive = false;
    };
  }, [slug]);

  const label = DOC_LABELS[slug] || slug;

  return (
    <div className="min-h-screen bg-black text-white/90 px-6 py-10 sm:px-12 sm:py-16">
      <div className="max-w-3xl mx-auto">
        <a
          href="/"
          className="inline-block mb-6 text-xs uppercase tracking-wide text-jcyan/70 hover:text-jcyan"
        >
          ← Back to JARVIS
        </a>
        {error && (
          <div className="text-sm text-red-300 border border-red-400/30 bg-red-400/10 rounded p-3">
            Failed to load {label}: {error}
          </div>
        )}
        {body === null && !error && (
          <div className="text-sm text-white/40">Loading {label}…</div>
        )}
        {body && (
          <article className="legal-prose prose prose-invert max-w-none">
            <ReactMarkdown>{body}</ReactMarkdown>
          </article>
        )}
      </div>
    </div>
  );
}
