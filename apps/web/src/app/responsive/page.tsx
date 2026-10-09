"use client";
import { useState, useMemo, useEffect, useRef, useCallback } from "react";
import { api } from "@/lib/api";

type DeviceShot = {
  status: string; dataUrl?: string; width?: number; height?: number; isMobile?: boolean;
  hScroll?: boolean; smallTap?: number; viewportOk?: boolean; timing?: number;
  error?: string; category?: string;
};
type CatGroup = { label: string; icon: string; devices: Record<string, DeviceShot> };
type CatMeta = { id: string; label: string; icon: string };
type CatalogDevice = { name: string; width: number; height: number; isMobile: boolean; category: string; icon: string };
type CatalogCat = { id: string; label: string; icon: string; devices: CatalogDevice[] };

const CATS: { id: string; label: string; icon: string }[] = [
  { id: "mobile",  label: "Mobile",  icon: "📱" },
  { id: "tablet",  label: "Tablet",  icon: "📋" },
  { id: "laptop",  label: "Laptop",  icon: "💻" },
  { id: "desktop", label: "Desktop", icon: "🖥" },
  { id: "wide",    label: "Wide / TV", icon: "📺" },
];
const ENGINE_META: Record<string, { label: string; color: string }> = {
  chromium: { label: "Chromium", color: "text-blue-600" },
  firefox:  { label: "Firefox",  color: "text-orange-500" },
  webkit:   { label: "WebKit / Safari", color: "text-purple-600" },
};

function StatPill({ label, value, good }: { label: string; value: string | number; good?: boolean }) {
  const cls = good === true ? "bg-emerald-50 text-emerald-700 border-emerald-200" : good === false ? "bg-red-50 text-red-700 border-red-200" : "bg-ink-50 text-ink-600 border-ink-200/60";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${cls}`}>{label} <span className="font-bold">{value}</span></span>;
}

/* ---------- LIVE mode: interactive iframe device ---------- */
function LiveFrame({ name, srcUrl, w, h, mobile, scrollLock }: {
  name: string; srcUrl: string; w: number; h: number; mobile: boolean; scrollLock: boolean;
}) {
  const [rotated, setRotated] = useState(false);
  const [navUrl, setNavUrl] = useState(`${srcUrl}${srcUrl.includes("?") ? "&" : "?"}rt=nonce-${Date.now()}`);
  const [iframeKey, setIframeKey] = useState(0);
  const iframeRef = useRef<HTMLIFrameElement>(null);
  const effW = rotated ? h : w;
  const effH = rotated ? w : h;
  // Per-device scale: phones render near-native, large screens scale to fit the grid.
  const scale = effW <= 560 ? 1 : effW <= 900 ? 0.65 : effW <= 1280 ? 0.5 : effW <= 1920 ? 0.38 : 0.24;
  const frameW = Math.round(effW * scale);
  const frameH = Math.round(effH * scale);

  const refresh = () => setNavUrl(`${srcUrl}${srcUrl.includes("?") ? "&" : "?"}rt=nonce-${Date.now()}`);

  // scroll-lock: pin the iframe to top so the outer page controls scrolling
  useEffect(() => {
    if (scrollLock && iframeRef.current) {
      try { iframeRef.current.contentWindow?.scrollTo(0, 0); } catch { /* cross-origin */ }
    }
  }, [scrollLock, iframeKey]);

  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="flex items-center gap-1 w-full justify-center">
        <span className="text-[11px] font-semibold text-ink-700">{name}</span>
      </div>
      <div className="text-[9px] text-ink-400">{effW}×{effH}px</div>

      {/* device chrome */}
      <div className="relative bg-ink-900 rounded-2xl shadow-lg overflow-hidden p-2" style={{ width: frameW + 12, height: frameH + 40 }}>
        <div className="flex items-center gap-1 mb-1.5 px-1">
          <span className="h-2 w-2 rounded-full bg-red-400" />
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          <span className="h-2 w-2 rounded-full bg-green-400" />
          <div className="flex-1 h-3.5 rounded bg-white/10 ml-2 text-[8px] text-white/70 flex items-center px-1.5 truncate">
            {name} · {effW}×{effH}
          </div>
          <button onClick={() => setRotated((r) => !r)} title="Rotate device" className="text-white/80 hover:text-white text-[10px]">🔄</button>
          <button onClick={refresh} title="Reload" className="text-white/80 hover:text-white text-[10px]">⟳</button>
        </div>
        {/* live iframe at TRUE device size, scaled down to fit */}
        <div className="bg-white rounded overflow-hidden relative" style={{ width: frameW, height: frameH }}>
          <div style={{ width: effW, height: effH, transform: `scale(${scale})`, transformOrigin: "top left", position: "absolute", top: 0, left: 0 }}>
            <iframe ref={iframeRef} key={iframeKey} src={navUrl} title={name} sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
              style={{ width: effW, height: effH, border: 0, pointerEvents: scrollLock ? "auto" : "auto" }} scrolling="yes" />
          </div>
          {/* scroll hint overlay that looks like scrollbars but lets clicks pass */}
          {scrollLock && (
            <div className="absolute right-0 top-0 bottom-0 w-2 bg-ink-900/60 cursor-pointer" title="Scroll locked" />
          )}
        </div>
      </div>
      <div className="flex flex-wrap gap-1 justify-center">
        <span className="text-[9px] text-ink-400">live · click to navigate</span>
        {mobile && <StatPill label="Mobile" value="touch" good />}
      </div>
    </div>
  );
}

/* ---------- COMPARE mode: screenshot device ---------- */
function ShotFrame({ name, shot, scale }: { name: string; shot: DeviceShot; scale: number }) {
  const w = shot.width || 390;
  const h = shot.height || 844;
  const frameW = Math.round(w * scale);
  const frameH = Math.min(Math.round(h * scale), 600);
  const isOk = shot.status === "ok";
  return (
    <div className="flex flex-col items-center gap-1.5">
      <div className="text-[11px] font-semibold text-ink-700 truncate max-w-full">{name}</div>
      <div className="text-[9px] text-ink-400">{w}×{h}px</div>
      <div className="relative bg-ink-900 rounded-xl p-2 shadow-lg overflow-hidden" style={{ width: frameW + 16, height: frameH + 48 }}>
        <div className="flex items-center gap-1 mb-1.5 px-1">
          <span className="h-2 w-2 rounded-full bg-red-400" />
          <span className="h-2 w-2 rounded-full bg-amber-400" />
          <span className="h-2 w-2 rounded-full bg-green-400" />
          <div className="flex-1 h-3 rounded bg-white/10 ml-2 text-[7px] text-white/40 flex items-center px-1.5 truncate">{name}</div>
        </div>
        <div className="bg-white rounded overflow-hidden" style={{ height: frameH }}>
          {isOk && shot.dataUrl ? (
            <img src={shot.dataUrl} alt={name} className="w-full h-full object-cover object-top" loading="lazy" />
          ) : (
            <div className="h-full grid place-items-center text-[10px] text-red-400 px-2 text-center">{shot.error || "unavailable"}</div>
          )}
        </div>
      </div>
      {isOk && (
        <div className="flex flex-wrap gap-1 justify-center">
          <StatPill label="Tap" value={shot.smallTap ?? 0} good={shot.smallTap === 0} />
          <StatPill label="Scroll" value={shot.hScroll ? "overflow" : "ok"} good={!shot.hScroll} />
        </div>
      )}
    </div>
  );
}

export default function ResponsivePage() {
  const [mode, setMode] = useState<"live" | "compare">("live");
  const [url, setUrl] = useState("");
  const [engine, setEngine] = useState("chromium");
  const [activeCat, setActiveCat] = useState<string>("all");
  const [scrollLock, setScrollLock] = useState(false);
  const [customW, setCustomW] = useState("");
  const [customH, setCustomH] = useState("");
  const [catalog, setCatalog] = useState<CatalogCat[]>([]);
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [frameable, setFrameable] = useState<{ ok: boolean; reason?: string } | null>(null);
  const previewKey = useRef(0);

  useEffect(() => { api.devices().then((res) => setCatalog(res.categories)).catch(() => {}); }, []);
  useEffect(() => { setFrameable(null); }, [mode, url]);

  const totalDevices = catalog.reduce((n, c) => n + c.devices.length, 0);
  const deviceCountFor = (id: string) => catalog.find((c) => c.id === id)?.devices.length || 0;

  async function run() {
    if (!url.trim()) return;
    if (mode === "live") {
      setErr("");
      previewKey.current += 1;
      setFrameable(null);
      try { const f = await api.frameable(url.trim()); setFrameable({ ok: f.frameable, reason: f.reason }); }
      catch { setFrameable(null); }
      return;
    }
    setLoading(true); setErr(""); setData(null);
    try { setData(await api.responsive(url.trim(), engine, activeCat === "all" ? null : activeCat)); }
    catch (e: any) { setErr(e.message); }
    finally { setLoading(false); }
  }

  // If the site blocks direct iframes (X-Frame-Options/CSP), bounce the live preview
  // through our server-side proxy so click-through still works.
  const liveSrcUrl = useMemo(() => {
    if (!url.trim()) return "";
    if (frameable && frameable.ok) return url.trim();
    return `${api.base}/api/v1/audit/proxy?url=${encodeURIComponent(url.trim())}`;
  }, [url, frameable]);

  // Live device list = catalog (worldwide, real sizes) + optional custom device
  const liveDevices = useMemo(() => {
    let ds = catalog.flatMap((c) => c.devices.map((d) => ({ name: d.name, w: d.width, h: d.height, mobile: d.isMobile, cat: d.category, icon: d.icon })));
    if (activeCat !== "all") ds = ds.filter((d) => d.cat === activeCat);
    if (customW && Number(customW) >= 200) {
      ds = [...ds, { name: `Custom ${customW}`, w: Math.round(Number(customW)), h: customH ? Math.round(Number(customH)) : 900, mobile: Number(customW) < 700, cat: "mobile", icon: "🖥" }];
    }
    return ds;
  }, [catalog, activeCat, customW, customH]);

  const grouped: Record<string, CatGroup> = data?.categories || {};
  const categories: CatMeta[] = data?.allCategories || [];
  const activeCategories = useMemo(() => {
    if (activeCat !== "all" && grouped[activeCat]) return [grouped[activeCat]];
    return Object.values(grouped);
  }, [activeCat, grouped]);
  const deviceScale = useMemo(() => {
    const allShots = activeCategories.flatMap((g) => Object.values(g.devices));
    const maxW = Math.max(...allShots.map((d) => d.width || 390), 390);
    return maxW > 1920 ? 0.1 : maxW > 1440 ? 0.12 : maxW > 1024 ? 0.16 : maxW > 800 ? 0.22 : 0.3;
  }, [activeCategories]);

  // Render live frames in batches so 130+ iframes don't stall the browser
  const BATCH = 9;
  const [batchCount, setBatchCount] = useState(BATCH);
  useEffect(() => { setBatchCount(BATCH); }, [activeCat, url, mode]);
  const visibleLive = liveDevices.length > BATCH && activeCat === "all" ? liveDevices.slice(0, batchCount) : liveDevices;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3 flex-wrap gap-1">
        <h1 className="text-xl font-bold">Responsive Testing Tool</h1>
        <span className="text-[12px] text-ink-500">live preview · real screenshots · {totalDevices || "130+"} worldwide device sizes · 3 engines</span>
      </div>

      {/* Input form */}
      <div className="card p-4 mb-3">
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex-1 min-w-52 text-[12px] font-semibold text-ink-700">URL
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://yoursite.com"
              className="mt-1 border border-ink-300 rounded-md px-3 py-2 w-full text-sm focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 outline-none" />
          </label>
          <label className="text-[12px] font-semibold text-ink-700">Engine
            <select value={engine} onChange={(e) => setEngine(e.target.value)}
              className="mt-1 border border-ink-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/40 outline-none">
              <option value="chromium">Chromium</option>
              <option value="firefox">Firefox</option>
              <option value="webkit">WebKit / Safari</option>
            </select>
          </label>
          <button onClick={run} disabled={loading || !url}
            className="bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white px-6 py-2 rounded-md font-semibold transition disabled:opacity-40 shadow-sm">
            {loading ? "Capturing…" : "Preview"}
          </button>
        </div>
      </div>

      {/* Mode toggle */}
      <div className="flex gap-1.5 mb-3 flex-wrap">
        <div className="flex gap-1.5">
          {(["live", "compare"] as const).map((m) => (
            <button key={m} onClick={() => setMode(m)}
              className={`px-3 py-1.5 rounded-md text-[12px] font-semibold transition ${mode === m ? "bg-indigo-600 text-white shadow-sm" : "bg-white border border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>
              {m === "live" ? "● Live Preview" : "▦ Compare (screenshots)"}
            </button>
          ))}
        </div>
        {(mode === "live" && url) && (
          <button onClick={() => setScrollLock((v) => !v)}
            className={`px-3 py-1.5 rounded-md text-[12px] font-semibold border transition cursor-pointer ${scrollLock ? "bg-ink-900 text-white border-ink-900" : "bg-white border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>
            {scrollLock ? "🔒 Locked scroll" : "🔓 Scroll pages via iframes"}
          </button>
        )}
        {mode === "live" && (
          <span className="text-[10px] text-ink-400 self-center">Engine applies to Compare screenshots — live frames render in <b>your</b> browser's engine.</span>
        )}
      </div>

      {/* Device category tabs + custom size */}
      {url && (
        <div className="flex gap-1.5 mb-3 flex-wrap items-center">
          <button onClick={() => setActiveCat("all")}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold transition ${activeCat === "all" ? "bg-ink-900 text-white shadow-sm" : "bg-white border border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>
            ALL <span className="text-[10px] opacity-60">({liveDevices.length})</span>
          </button>
          {CATS.map((c) => {
            const count = deviceCountFor(c.id);
            return (
              <button key={c.id} onClick={() => setActiveCat(c.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold transition ${activeCat === c.id ? "bg-ink-900 text-white shadow-sm" : "bg-white border border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>
                <span>{c.icon}</span> {c.label}
                <span className="text-[10px] opacity-60">({count})</span>
              </button>
            );
          })}
          <div className="flex items-end gap-1.5 ml-auto">
            <label className="text-[10px] font-semibold text-ink-500">Custom
              <input value={customW} onChange={(e) => setCustomW(e.target.value.replace(/\D/g, ""))} placeholder="width px"
                className="mt-0.5 w-20 border border-ink-300 rounded-md px-2 py-1 text-xs outline-none" />
            </label>
            <label className="text-[10px] font-semibold text-ink-500">×
              <input value={customH} onChange={(e) => setCustomH(e.target.value.replace(/\D/g, ""))} placeholder="h"
                className="mt-0.5 w-14 border border-ink-300 rounded-md px-2 py-1 text-xs outline-none" />
            </label>
          </div>
        </div>
      )}

      {err && <div className="card p-3 mb-3 border-red-300 text-crit">{err}</div>}

      {/* Live preview grid */}
      {mode === "live" && (
        url ? (
          <>
            {frameable && !frameable.ok && (
              <div className="card p-3 mb-3 border-amber-300 bg-amber-50 text-amber-800 text-sm">
                ⚠ This site blocks direct iframe embedding ({frameable.reason}) — live preview is being routed through our
                <span className="font-semibold"> server-side proxy</span> so click-through still works.
              </div>
            )}
            <div className="flex flex-wrap gap-4 justify-center">
              {visibleLive.map((d) => (
                <LiveFrame key={`${d.name}-${customW}-${previewKey.current}-${d.w}-${d.h}`} name={d.name} srcUrl={liveSrcUrl}
                  w={d.w} h={d.h} mobile={d.mobile} scrollLock={scrollLock} />
              ))}
            </div>
            {liveDevices.length > visibleLive.length && (
              <div className="text-center mt-4">
                <button onClick={() => setBatchCount((b) => b + BATCH)}
                  className="bg-ink-900 hover:bg-ink-800 text-white px-5 py-2 rounded-md font-semibold text-[12px] transition shadow-sm">
                  Load more device sizes ({visibleLive.length}/{liveDevices.length})
                </button>
              </div>
            )}
            <div className="text-[11px] text-ink-400 mt-3 text-center">
              These are live iframes of the real site — scroll up/down inside each, click menus to navigate to inner pages, use 🔄 to rotate or ⟳ to reload a device.
            </div>
          </>
        ) : (
          <div className="card p-10 text-center text-ink-500">
            <div className="text-4xl mb-3">📱💻🖥</div>
            <div className="mb-2">Paste a URL and click <span className="font-semibold">Preview</span> for a <span className="font-semibold">live, clickable</span> preview on every device size — scroll, tap menus, explore inner pages just like the reference tool.</div>
            <div className="max-w-lg mx-auto text-[12px] text-ink-400 space-y-1">
              <div>{catalog.length > 0 ? catalog.map((c) => `${c.icon} ${c.devices.length} ${c.label}`).join(" · ") : "Worldwide devices"}</div>
              <div>Mobile · Tablet · Laptop · Desktop · Wide / TV · custom width — all real, measured, never fabricated.</div>
            </div>
          </div>
        )
      )}

      {/* Compare screenshots grid */}
      {mode === "compare" && (
        loading ? (
          <div className="card p-8 mb-3 text-center">
            <div className="h-6 w-6 rounded-full border-2 border-ink-300 border-t-indigo-600 animate-spin mx-auto mb-3" />
            <div className="text-sm text-ink-600">Rendering {engine} screenshots…</div>
            <div className="text-[11px] text-ink-400 mt-1">Each cell is a real headless render. Takes 1–3 minutes.</div>
          </div>
        ) : data ? (
          <>
            <div className="flex gap-1.5 mb-3 flex-wrap">
              <button onClick={() => setActiveCat("all")}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold transition ${activeCat === "all" ? "bg-ink-900 text-white shadow-sm" : "bg-white border border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>ALL</button>
              {categories.map((c) => (
                <button key={c.id} onClick={() => setActiveCat(c.id)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold transition ${activeCat === c.id ? "bg-ink-900 text-white shadow-sm" : "bg-white border border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>
                  <span>{c.icon}</span> {c.label}
                </button>
              ))}
            </div>
            <div className="flex flex-wrap gap-4 justify-center">
              {activeCategories.length === 0 && <div className="text-sm text-ink-500 text-center py-8 col-span-full">No captures yet — run a screen category above.</div>}
              {activeCategories.map((g) => (
                <div key={g.label} className="w-full">
                  <div className="text-[11px] font-bold uppercase tracking-wide text-ink-400 mb-2">{g.icon} {g.label}</div>
                  <div className="flex flex-wrap gap-4 justify-center">
                    {Object.entries(g.devices).map(([name, shot]) => (
                      <ShotFrame key={name} name={name} shot={shot as DeviceShot} scale={deviceScale} />
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </>
        ) : (
          <div className="card p-8 text-center text-ink-500">
            <div className="text-sm mb-1">Screenshot mode — run a URL above to capture real renders across all device sizes, in your choice of engine.</div>
            <div className="text-[11px] text-ink-400">Best for sites that block live iframes, and for automated verification.</div>
          </div>
        )
      )}
    </div>
  );
}