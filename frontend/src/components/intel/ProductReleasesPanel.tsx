/**
 * Product Releases — slide-in panel listing products discovered by
 * the industry watcher (Shopify storefronts: wholesalebodyjewellery,
 * tishlyon, …).
 *
 * Triggered by the 🛍 button in the top bar. Lists newest-first, with
 * site-domain filter chips, a manual Refresh button, and a footer
 * "Ask JARVIS about these" button that routes to chat via
 * `useJarvisStore.sendChat`.
 */
import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  ProductReleasesAPI,
  type ProductRelease,
  type ProductReleaseSite,
} from "../../lib/api";
import { useJarvisStore } from "../../store/jarvisStore";

interface Props {
  open: boolean;
  onClose: () => void;
}

const ASK_PROMPT =
  "Summarize the most interesting new products from my watched sites this week. " +
  "Group by vendor and flag anything that might fit my catalogue.";

export function ProductReleasesPanel({ open, onClose }: Props) {
  const [items, setItems] = useState<ProductRelease[]>([]);
  const [sites, setSites] = useState<ProductReleaseSite[]>([]);
  const [selectedSite, setSelectedSite] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const addToast = useJarvisStore((s) => s.addToast);
  const sendChat = useJarvisStore((s) => s.sendChat);
  const setMode = useJarvisStore((s) => s.setMode);

  const load = async (site: string | null) => {
    setLoading(true);
    try {
      const [list, sitesRes] = await Promise.all([
        ProductReleasesAPI.list({
          site: site || undefined,
          since_hours: 168,
          limit: 100,
        }),
        ProductReleasesAPI.sites(),
      ]);
      setItems(list.items);
      setSites(sitesRes.sites);
    } catch {
      addToast({ type: "error", message: "Failed to load product releases." });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (open) load(selectedSite);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, selectedSite]);

  const refresh = async () => {
    setRefreshing(true);
    addToast({ type: "info", message: "Fetching latest product feeds…" });
    try {
      const r = await ProductReleasesAPI.refresh();
      const newTotal = r.sites.reduce((acc, s) => acc + s.new, 0);
      addToast({
        type: "success",
        message:
          newTotal === 0
            ? "Refreshed — no new products today."
            : `Refreshed — ${newTotal} new product${newTotal !== 1 ? "s" : ""} found.`,
      });
      await load(selectedSite);
    } catch {
      addToast({ type: "error", message: "Refresh failed. Check backend logs." });
    } finally {
      setRefreshing(false);
    }
  };

  const askJarvis = async () => {
    setMode("text");
    onClose();
    await sendChat(ASK_PROMPT);
  };

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 z-[100] bg-black/40 backdrop-blur-sm"
          />
          <motion.div
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ type: "spring", stiffness: 360, damping: 32 }}
            className="fixed right-0 top-0 h-full w-[28rem] z-[110] bg-[#0a0e1a] border-l border-jcyan/30 shadow-2xl flex flex-col"
          >
            {/* Header */}
            <div className="px-5 py-4 border-b border-jcyan/20 flex items-center justify-between">
              <div>
                <h3 className="text-jcyan text-sm font-bold uppercase tracking-widest">
                  Product Releases
                </h3>
                <p className="text-white/30 text-xs">
                  New SKUs on watched competitor / supplier sites
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={refresh}
                  disabled={refreshing}
                  className="px-2.5 py-1 rounded-md border border-jcyan/40 bg-jcyan/5 text-jcyan text-[10px] font-bold uppercase tracking-widest hover:bg-jcyan/15 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                  title="Refresh now"
                >
                  {refreshing ? "…" : "Refresh"}
                </button>
                <button onClick={onClose} className="text-white/30 hover:text-white text-lg leading-none">
                  ✕
                </button>
              </div>
            </div>

            {/* Site filter chips */}
            {sites.length > 0 && (
              <div className="px-4 py-2 border-b border-white/5 flex flex-wrap gap-1.5">
                <FilterChip
                  active={selectedSite === null}
                  label="All"
                  count={sites.reduce((a, s) => a + s.count, 0)}
                  onClick={() => setSelectedSite(null)}
                />
                {sites.map((s) => (
                  <FilterChip
                    key={s.domain}
                    active={selectedSite === s.domain}
                    label={s.domain}
                    count={s.count}
                    onClick={() => setSelectedSite(s.domain)}
                  />
                ))}
              </div>
            )}

            {/* Product list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-2">
              {loading && (
                <div className="text-white/40 text-sm py-10 text-center">Loading…</div>
              )}
              {!loading && items.length === 0 && (
                <div className="flex flex-col items-center justify-center py-10 gap-2 text-center">
                  <span className="text-3xl opacity-30">🛍</span>
                  <span className="text-white/40 text-sm">No product releases yet.</span>
                  <span className="text-white/20 text-xs">Hit Refresh to scan watched feeds.</span>
                </div>
              )}
              {!loading && items.map((p) => <ProductCard key={p.id} p={p} />)}
            </div>

            {/* Footer — ask JARVIS */}
            <div className="px-4 py-3 border-t border-jcyan/20">
              <button
                onClick={askJarvis}
                disabled={items.length === 0}
                className="w-full px-3 py-2 rounded-md border border-jcyan/40 bg-jcyan/5 text-jcyan text-xs font-bold uppercase tracking-widest hover:bg-jcyan/15 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              >
                Ask JARVIS about these
              </button>
              <div className="text-white/20 text-[10px] text-center mt-1.5">
                Auto-runs every 6h. New products surface in Decision Inbox.
              </div>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}

function FilterChip({
  active,
  label,
  count,
  onClick,
}: {
  active: boolean;
  label: string;
  count: number;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`text-[10px] uppercase tracking-wide px-2 py-0.5 rounded-full border transition-colors ${
        active
          ? "bg-jcyan/15 border-jcyan/50 text-jcyan"
          : "bg-white/3 border-white/10 text-white/50 hover:border-white/30 hover:text-white/80"
      }`}
    >
      {label} <span className="opacity-60">· {count}</span>
    </button>
  );
}

function relativeTime(iso: string | null): string {
  if (!iso) return "";
  const d = new Date(iso);
  const diffSec = Math.floor((Date.now() - d.getTime()) / 1000);
  if (diffSec < 60) return `${diffSec}s ago`;
  if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
  if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
  if (diffSec < 604800) return `${Math.floor(diffSec / 86400)}d ago`;
  return d.toLocaleDateString();
}

function ProductCard({ p }: { p: ProductRelease }) {
  return (
    <div className="rounded-lg border border-white/10 bg-white/3 hover:border-white/30 transition-colors p-2.5 flex gap-3">
      {p.image_url ? (
        <img
          src={p.image_url}
          alt=""
          loading="lazy"
          className="w-16 h-16 rounded object-cover bg-black/30 shrink-0"
        />
      ) : (
        <div className="w-16 h-16 rounded bg-black/30 flex items-center justify-center text-white/20 shrink-0">
          ⬜
        </div>
      )}
      <div className="flex-1 min-w-0">
        <a
          href={p.url}
          target="_blank"
          rel="noopener noreferrer"
          className="text-white text-sm font-medium hover:text-jcyan transition-colors line-clamp-2"
          title={p.title}
        >
          {p.title}
        </a>
        <div className="text-white/40 text-[11px] mt-0.5 truncate">
          {p.vendor || "?"} · {p.product_type || "—"}
        </div>
        <div className="flex items-center justify-between mt-1">
          <span className="text-jcyan text-xs font-medium">
            {p.price ? `£${p.price}` : "—"}
          </span>
          <span className="text-white/30 text-[10px]">
            {p.site_domain.replace(/^www\./, "")} · {relativeTime(p.first_seen_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
