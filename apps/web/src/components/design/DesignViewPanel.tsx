"use client";
import { useState, useMemo } from "react";

type Shot = { dataUrl?: string; timing?: number; smallTap?: number; hScroll?: boolean; error?: string; status?: string };

/* Responsive Design Gallery — shows per-engine screenshots at Mobile / Tablet / Desktop / Wide widths
   extracted from the H-xbrowser rendered check image evidence. Purely measured, never fabricated. */

const DEVICE_ORDER = ["Mobile", "Desktop"] as const;
type DeviceName = typeof DEVICE_ORDER[number];

const DEVICE_FRAMES: Record<DeviceName, { w: number; h: number; label: string; icon: string }> = {
  Mobile:  { w: 180, h: 380, label: "Mobile 390",  icon: "📱" },
  Desktop: { w: 320, h: 210, label: "Desktop 1440", icon: "🖥" },
};

const ENGINE_LABELS: Record<string, { label: string; icon: string; color: string }> = {
  chromium: { label: "Chromium", icon: "◉", color: "text-blue-600" },
  firefox:  { label: "Firefox",  icon: "🦊", color: "text-orange-500" },
  webkit:   { label: "WebKit/Safari", icon: "◆", color: "text-purple-600" },
};

function StatPill({ label, value, good }: { label: string; value: string | number; good?: boolean }) {
  const cls = good === true ? "bg-emerald-50 text-emerald-700 border-emerald-200" : good === false ? "bg-red-50 text-red-700 border-red-200" : "bg-ink-50 text-ink-600 border-ink-200/60";
  return <span className={`inline-flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded border ${cls}`}>{label} <span className="font-bold">{value}</span></span>;
}

function BrowserFrame({ children, label, icon }: { children: React.ReactNode; label: string; icon: string }) {
  return (
    <div className="overflow-hidden rounded-xl border border-ink-300/60 shadow-sm bg-white">
      <div className="flex items-center gap-1.5 px-2 py-1.5 bg-ink-800">
        <span className="h-2 w-2 rounded-full bg-red-400" />
        <span className="h-2 w-2 rounded-full bg-amber-400" />
        <span className="h-2 w-2 rounded-full bg-green-400" />
        <span className="ml-1 text-[9px] text-white/60 font-semibold">{icon} {label}</span>
      </div>
      <div className="bg-ink-50 overflow-auto">{children}</div>
    </div>
  );
}

export function DesignViewPanel({ checks }: { checks: any[] }) {
  // Group H-xbrowser screenshot evidence by engine then device
  const matrix = useMemo(() => {
    const m: Record<string, Record<string, Shot>> = {};
    for (const r of checks) {
      if (!r.key.startsWith("h-screenshot-") || r.evidence?.type !== "image") continue;
      // key: h-screenshot-chromium-mobile
      const parts = r.key.replace("h-screenshot-", "").split("-");
      const engine = parts[0];
      const dev = parts.slice(1).join("-");
      if (!m[engine]) m[engine] = {};
      m[engine][dev] = {
        dataUrl: r.evidence.dataUrl,
        timing: r.evidence.timing,
        smallTap: r.evidence.smallTap ?? 0,
        hScroll: r.evidence.hScroll ?? false,
      };
    }
    return m;
  }, [checks]);

  // H-xbrowser summary checks (tap targets, h-scroll per engine)
  const hChecks = useMemo(() => {
    const m: Record<string, any> = {};
    for (const r of checks) {
      if (r.category === "H-xbrowser" && r.key.startsWith("h-") && !r.key.startsWith("h-screenshot")) {
        m[r.key] = r;
      }
    }
    return m;
  }, [checks]);

  const engines = Object.keys(matrix);
  const [activeEngine, setActiveEngine] = useState(engines[0] || "chromium");
  const [activeDevice, setActiveDevice] = useState<"side" | DeviceName>("side");

  if (!engines.length) return null;

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-[13px] font-bold text-ink-900">Responsive Design View</h2>
        <span className="text-[11px] text-ink-400">real browser screenshots · mobile + desktop</span>
      </div>

      {/* Engine tabs */}
      <div className="flex gap-1 mb-3">
        {engines.map((eng) => {
          const meta = ENGINE_LABELS[eng] || { label: eng, icon: "•", color: "" };
          const hc = hChecks["h-" + eng];
          const warn = hc?.status === "warning";
          return (
            <button key={eng} onClick={() => setActiveEngine(eng)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-[12px] font-semibold transition
                ${activeEngine === eng ? "bg-ink-900 text-white shadow-sm" : "bg-white border border-ink-300/60 text-ink-700 hover:bg-ink-50"}`}>
              <span className={activeEngine === eng ? "" : meta.color}>{meta.icon}</span>
              {meta.label}
              {warn && <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse" />}
            </button>
          );
        })}
      </div>

      {/* View toggle */}
      <div className="flex gap-1 mb-3">
        {(["side"] as const).map((v) => (
          <button key={v} onClick={() => setActiveDevice(v)}
            className={`px-2 py-1 text-[11px] rounded font-semibold border
              ${activeDevice === v ? "bg-ink-900 text-white" : "bg-white text-ink-600 border-ink-300/60"}`}>
            Side by side
          </button>
        ))}
        {DEVICE_ORDER.map((d) => (
          <button key={d} onClick={() => setActiveDevice(d)}
            className={`px-2 py-1 text-[11px] rounded font-semibold border
              ${activeDevice === d ? "bg-ink-900 text-white" : "bg-white text-ink-600 border-ink-300/60"}`}>
            {d}
          </button>
        ))}
      </div>

      {/* Screenshot frames */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {(activeDevice === "side" ? DEVICE_ORDER : [activeDevice as DeviceName]).map((dev) => {
          const frame = DEVICE_FRAMES[dev];
          const shot = matrix[activeEngine]?.[dev.toLowerCase()];
          const hc = hChecks["h-" + activeEngine];
          return (
            <div key={dev} className="flex flex-col gap-1">
              <BrowserFrame label={`${ENGINE_LABELS[activeEngine]?.label || activeEngine} · ${frame.label}`} icon={ENGINE_LABELS[activeEngine]?.icon || ""}>
                {shot?.dataUrl ? (
                  <div className="flex justify-center p-2">
                    <img src={shot.dataUrl} alt={`${activeEngine} ${frame.label}`}
                      className="rounded border max-w-full object-contain bg-white"
                      style={{ maxHeight: 400 }}
                      loading="lazy" />
                  </div>
                ) : shot?.status === "unavailable" ? (
                  <div className="p-4 text-center text-[11px] text-red-500">{shot.error || "unavailable"}</div>
                ) : (
                  <div className="p-4 text-center text-[11px] text-ink-400">Loading {frame.label}…</div>
                )}
              </BrowserFrame>
              <div className="flex flex-wrap gap-1.5 mt-1">
                <StatPill label="Load" value={shot?.timing ? `${shot.timing}ms` : "—"} good={shot?.timing ? shot.timing < 2500 : undefined} />
                <StatPill label="Tap" value={shot?.smallTap ?? "—"} good={shot?.smallTap === 0} />
                <StatPill label="Scroll" value={shot?.hScroll ? "overflows" : "ok"} good={!shot?.hScroll} />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}