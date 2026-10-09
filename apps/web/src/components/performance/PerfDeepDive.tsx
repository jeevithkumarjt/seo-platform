"use client";
import { useMemo } from "react";

/* Performance Deep-Dive — extracted from D-performance and S-frontend evidence.
   Shows: score gauge, lab metric bars colored to thresholds, CrUX field gauges,
   PSI screenshots, resource weight breakdown, render-blocking lists.
   All measured — thresholds are published Google thresholds. */

const THRESHOLDS: Record<string, { good: number; poor: number; unit: string }> = {
  "LCP (lab)":  { good: 2500, poor: 4000, unit: "ms" },
  "FCP (lab)":  { good: 1800, poor: 3000, unit: "ms" },
  "TTI":        { good: 3800, poor: 7300, unit: "ms" },
  "CLS (lab)":  { good: 0.1,  poor: 0.25, unit: "" },
  "Speed Index":{ good: 3400, poor: 5800, unit: "ms" },
  "TBT (lab)":  { good: 200,  poor: 600,  unit: "ms" },
  "TTFB (lab)": { good: 800,  poor: 1800, unit: "ms" },
};

function valFor(key: string, ev: any): number | null {
  if (ev == null) return null;
  if (typeof ev === "number") return ev;
  if (typeof ev === "object") return ev.numericValue ?? ev.score ?? null;
  const n = parseFloat(String(ev));
  return isNaN(n) ? null : n;
}

function statusColor(pct: number): string {
  if (pct >= 90) return "bg-emerald-500";
  if (pct >= 50) return "bg-amber-500";
  return "bg-red-500";
}

function metricBar(label: string, value: number, thresholds: { good: number; poor: number; unit: string }) {
  const { good, poor, unit } = thresholds;
  const isGood = good < poor ? value <= good : value >= good;
  const isPoor = good < poor ? value >= poor : value <= poor;
  const pct = good < poor
    ? Math.min(100, Math.max(5, (value / (poor * 1.5)) * 100))
    : Math.max(5, Math.min(100, (good * 1.5 > 0 ? value / (good * 1.5) : 0.5) * 100));
  const color = isGood ? "bg-emerald-500" : isPoor ? "bg-red-500" : "bg-amber-500";
  const dotColor = isGood ? "bg-emerald-500" : isPoor ? "bg-red-500" : "bg-amber-500";
  const valStr = unit === "ms" ? `${(value / 1000).toFixed(2)}s` : String(value);
  return (
    <div key={label} className="flex items-center gap-3">
      <span className="w-24 shrink-0 text-[11px] text-ink-500 truncate font-medium">{label}</span>
      <div className="flex-1 h-4 rounded bg-ink-100 overflow-hidden relative">
        {/* threshold markers */}
        <div className="absolute inset-y-0 border-r border-emerald-300/50" style={{ left: `${(good / (poor * 1.5)) * 100}%` }} />
        <div className="absolute inset-y-0 border-r border-red-300/50" style={{ left: `${(poor / (poor * 1.5)) * 100}%` }} />
        <div className={`h-full rounded ${color}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`w-14 text-right font-mono text-[11px] font-bold ${isGood ? "text-emerald-700" : isPoor ? "text-red-700" : "text-amber-700"}`}>{valStr}</span>
    </div>
  );
}

function ScoreGauge({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = pct >= 90 ? "#059669" : pct >= 50 ? "#d97706" : "#dc2626";
  const label = pct >= 90 ? "Good" : pct >= 50 ? "Needs work" : "Poor";
  return (
    <div className="flex flex-col items-center gap-1">
      <svg viewBox="0 0 120 80" className="w-28 h-16">
        <path d="M10,70 A50,50 0 0,1 110,70" fill="none" stroke="#f1f5f9" strokeWidth="10" strokeLinecap="round" />
        <path d="M10,70 A50,50 0 0,1 110,70" fill="none" stroke={color} strokeWidth="10" strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * 157} 157`} />
      </svg>
      <div className="text-2xl font-extrabold" style={{ color }}>{pct}</div>
      <div className="text-[10px] font-semibold text-ink-500">{label}</div>
    </div>
  );
}

export function PerfDeepDive({ checks }: { checks: any[] }) {
  const byKey = useMemo(() => {
    const m: Record<string, any> = {};
    for (const r of checks) { m[r.key] = r; }
    return m;
  }, [checks]);

  // Score
  const scoreR = byKey["d-score"];
  const scoreVal = scoreR?.evidence?.score ?? (typeof scoreR?.found === "string" ? parseInt(scoreR.found) / 100 : null);

  // Lab metrics
  const labMetrics = ["d-largest-contentful-paint", "d-first-contentful-paint", "d-interactive",
    "d-cumulative-layout-shift", "d-speed-index", "d-total-blocking-time", "d-server-response-time"];
  const labBars = labMetrics.map((k) => {
    const r = byKey[k];
    if (!r || r.status === "unavailable") return null;
    const ev = r.evidence;
    const name = r.label.replace(" — lab", "");
    const num = ev?.numericValue ?? valFor(name, ev);
    const thr = THRESHOLDS[name];
    if (num == null || !thr) return null;
    return metricBar(name, num, thr);
  }).filter(Boolean);

  // CrUX field
  const fieldKeys = ["d-field-LARGEST_CONTENTFUL_PAINT_MS", "d-field-FIRST_INPUT_DELAY_MS",
    "d-field-CUMULATIVE_LAYOUT_SHIFT_SCORE", "d-field-INTERACTION_TO_NEXT_PAINT"];
  const fieldRows = fieldKeys.map((k) => {
    const r = byKey[k];
    if (!r) return null;
    const ev = r.evidence || {};
    return { label: r.label.replace(" — field (CrUX)", ""), category: ev.category || r.found?.split("·")[0]?.trim() || "?", p75: ev.percentile || "?", status: r.status };
  }).filter(Boolean);

  // PSI screenshots
  const shots = ["d-screenshot-final", "d-screenshot-loading"].map((k) => byKey[k]).filter(Boolean);

  // Resources
  const renderBlock = byKey["d-renderblock"];
  const unusedJs = byKey["d-unused-js"];
  const unusedCss = byKey["d-unused-css"];
  const thirdParty = byKey["d-3p"];
  const imgOpt = byKey["d-imgopt"];
  const imgSize = byKey["d-imgsize"];
  const mainThread = byKey["d-mainthread"];
  const longTasks = byKey["d-longtasks"];

  if (!scoreVal && !labBars.length && !shots.length) return null;

  const fmtBytes = (b: number) => b > 1024 * 1024 ? `${(b / 1024 / 1024).toFixed(1)} MB` : `${(b / 1024).toFixed(0)} KB`;

  return (
    <div className="mb-4">
      <div className="flex items-center gap-2 mb-2">
        <h2 className="text-[13px] font-bold text-ink-900">Performance Deep-Dive</h2>
        <span className="text-[11px] text-ink-400">PageSpeed Insights lab + field · measured, never fabricated</span>
      </div>

      <div className="card p-4 mb-3">
        <div className="grid grid-cols-1 md:grid-cols-[auto_1fr] gap-4">
          {/* Score */}
          <div className="flex flex-col items-center gap-2">
            {scoreVal != null ? <ScoreGauge score={scoreVal} /> : <span className="text-ink-400 text-[12px]">No score</span>}
            <span className="text-[10px] text-ink-400">Lighthouse performance</span>
          </div>
          {/* Lab metric bars */}
          <div className="space-y-2">
            <div className="text-[10px] uppercase tracking-wide text-ink-500 font-semibold mb-1">Lab Metrics</div>
            {labBars.length ? labBars : <div className="text-[11px] text-ink-400">No lab data</div>}
            <div className="flex gap-4 mt-2 text-[9px] text-ink-400">
              <span className="flex items-center gap-1"><i className="h-1.5 w-3 rounded-sm bg-emerald-500 inline-block" /> good</span>
              <span className="flex items-center gap-1"><i className="h-1.5 w-3 rounded-sm bg-amber-500 inline-block" /> needs work</span>
              <span className="flex items-center gap-1"><i className="h-1.5 w-3 rounded-sm bg-red-500 inline-block" /> poor</span>
            </div>
          </div>
        </div>
      </div>

      {/* CrUX Field Data */}
      {fieldRows.length > 0 && (
        <div className="card p-4 mb-3">
          <div className="text-[10px] uppercase tracking-wide text-ink-500 font-semibold mb-2">Field Data (CrUX · real users)</div>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {fieldRows.filter(Boolean).map((f) => (f ? (
              <div key={f.label} className={`p-2.5 rounded-lg border ${f.status === "pass" ? "bg-emerald-50 border-emerald-200" : f.status === "fail" ? "bg-red-50 border-red-200" : "bg-amber-50 border-amber-200"}`}>
                <div className="text-[11px] font-semibold text-ink-700 truncate">{f.label}</div>
                <div className="text-lg font-bold mt-0.5">{f.category}</div>
                <div className="text-[10px] text-ink-500">p75: {f.p75}</div>
              </div>
            ) : null))}
          </div>
        </div>
      )}

      {/* PSI Screenshots */}
      {shots.length > 0 && (
        <div className="card p-4 mb-3">
          <div className="text-[10px] uppercase tracking-wide text-ink-500 font-semibold mb-2">Page Screenshots (PageSpeed)</div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {shots.map((s) => (
              <div key={s.key} className="rounded-xl border border-ink-300/60 overflow-hidden bg-white shadow-sm">
                <div className="flex items-center gap-1.5 px-2 py-1 bg-ink-800">
                  <span className="h-2 w-2 rounded-full bg-red-400" /><span className="h-2 w-2 rounded-full bg-amber-400" /><span className="h-2 w-2 rounded-full bg-green-400" />
                  <span className="ml-1 text-[9px] text-white/60 font-semibold">{s.label}</span>
                  {s.evidence?.timing && <span className="ml-auto text-[9px] text-white/50">{Math.round(s.evidence.timing)}ms</span>}
                </div>
                <div className="bg-ink-50">
                  {s.evidence?.dataUrl && <img src={s.evidence.dataUrl} alt={s.label} className="max-w-full max-h-64 object-contain mx-auto p-2" loading="lazy" />}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resource Breakdown */}
      <div className="card p-4 mb-3">
        <div className="text-[10px] uppercase tracking-wide text-ink-500 font-semibold mb-2">Resource Breakdown</div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
          {[
            { r: renderBlock, label: "Render-Blocking", icon: "⏸", key: "urls" },
            { r: unusedJs, label: "Unused JS", icon: "📦", key: "wastedBytes" },
            { r: unusedCss, label: "Unused CSS", icon: "🎨", key: "wastedBytes" },
            { r: imgOpt, label: "Unoptimized Images", icon: "🖼", key: "wastedBytes" },
            { r: imgSize, label: "Oversized Images", icon: "📐", key: "wastedBytes" },
            { r: mainThread, label: "Main-Thread Work", icon: "⚙", key: "numericValue" },
            { r: longTasks, label: "Long Tasks", icon: "⏱", key: "count" },
            { r: thirdParty, label: "Third-Party", icon: "🌐", key: "count" },
          ].filter((x) => x.r && x.r.status !== "unavailable").map(({ r, label, icon, key }) => {
            const ev = r.evidence || {};
            const val = ev[key] ?? ev.wastedBytes ?? ev.numericValue ?? ev.count ?? ev.urls?.length ?? 0;
            const status = r.status;
            return (
              <div key={label} className={`p-2.5 rounded-lg border ${status === "pass" ? "bg-emerald-50/50 border-emerald-200/50" : status === "warning" ? "bg-amber-50 border-amber-200" : "bg-red-50 border-red-200"}`}>
                <div className="text-[10px] text-ink-500">{icon} {label}</div>
                <div className="text-lg font-bold mt-0.5">{typeof val === "number" && key.includes("Bytes") ? fmtBytes(val) : val}</div>
                {r.found && <div className="text-[10px] text-ink-500 mt-0.5 truncate" title={r.found}>{r.found.slice(0, 60)}</div>}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}