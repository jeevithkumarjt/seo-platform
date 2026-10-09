"use client";
import { useState } from "react";

/* Full Lighthouse-style report — mirrors the PSI / DevTools Performance panel.
   Data comes from one PSI call (real, cached). Each opportunity shows the exact
   resource URLs (CSS/JS/etc.), transfer size, and estimated savings. */

function scoreColor(s: number | null) {
  if (s == null) return { text: "text-ink-400", ring: "#cbd5e1", label: "n/a", hex: "#cbd5e1" };
  if (s >= 90) return { text: "text-emerald-600", ring: "#059669", label: "Good", hex: "#059669" };
  if (s >= 50) return { text: "text-amber-600", ring: "#d97706", label: "Needs work", hex: "#d97706" };
  return { text: "text-red-600", ring: "#dc2626", label: "Poor", hex: "#dc2626" };
}

function ScoreRing({ score, size = 56 }: { score: number | null; size?: number }) {
  const c = scoreColor(score);
  const r = size / 2 - 4;
  const circ = 2 * Math.PI * r;
  const pct = score == null ? 0 : score / 100;
  return (
    <div className="flex flex-col items-center gap-0.5">
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-90">
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="#e2e8f0" strokeWidth="4" />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={c.ring} strokeWidth="4" strokeLinecap="round"
          strokeDasharray={`${circ * pct} ${circ}`} />
      </svg>
      <span className="absolute" />
      <div className="relative -mt-[44px] z-10" />
      <span className={`text-lg font-extrabold leading-none ${c.text}`}>{score == null ? "—" : score}</span>
      <span className="text-[9px] text-ink-400 font-semibold">{c.label}</span>
    </div>
  );
}

function Byte({ v }: { v?: string }) { return v ? <td className="border-t border-ink-100 px-2 py-1 font-mono text-[10px] text-right whitespace-nowrap">{v}</td> : null; }

function ResourceRow({ item }: { item: any }) {
  const url = item.url || item.detail || "—";
  const short = url.length > 90 ? url.slice(0, 90) + "…" : url;
  return (
    <tr>
      <td className="border-t border-ink-100 px-2 py-1.5 max-w-[300px]">
        <div className="text-[10px] font-mono text-ink-600 break-all">{short}</div>
        {item.selector && <div className="text-[9px] text-ink-400 truncate">{item.selector}</div>}
      </td>
      <Byte v={item.transferSize} /><Byte v={item.wastedBytes} /><Byte v={item.wastedMs} />
      <Byte v={item.duration} />
    </tr>
  );
}

function Opportunity({ o }: { o: any }) {
  const [open, setOpen] = useState(true);
  const rows = o.items || [];
  const hasUrl = rows.some((i: any) => i.url);
  return (
    <div className="border border-ink-200 rounded-lg mb-2 overflow-hidden">
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center gap-2 text-left px-3 py-2 hover:bg-ink-50">
        <span className={`text-[10px] transition ${open ? "" : "rotate-180"}`}>▾</span>
        <span className="flex-1 text-[12px] font-semibold">{o.title}</span>
        {o.savings && <span className="text-[11px] font-bold text-indigo-600">{o.savings}</span>}
      </button>
      {open && (
        <div className="px-4 pb-3">
          {o.description && <p className="text-[11px] text-ink-500 mb-2">{o.description}</p>}
          {rows.length > 0 && hasUrl && (
            <table className="w-full text-[11px]">
              <thead>
                <tr>
                  <th className="text-left px-2 py-1 text-[9px] uppercase text-ink-400 font-semibold">URL</th>
                  <th className="px-2 py-1 text-[9px] uppercase text-ink-400 font-semibold text-right">Transfer</th>
                  <th className="px-2 py-1 text-[9px] uppercase text-ink-400 font-semibold text-right">Wasted</th>
                  <th className="px-2 py-1 text-[9px] uppercase text-ink-400 font-semibold text-right">Wasted (ms)</th>
                  <th className="px-2 py-1 text-[9px] uppercase text-ink-400 font-semibold text-right">Duration</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((i: any, idx: number) => <ResourceRow key={idx} item={i} />)}
              </tbody>
            </table>
          )}
          {rows.length > 0 && !hasUrl && (
            <div className="flex flex-wrap gap-1.5">
              {rows.map((i: any, idx: number) => (
                <span key={idx} className="bg-ink-50 border border-ink-200 rounded px-2 py-0.5 text-[10px] text-ink-600">{i.detail}</span>
              ))}
            </div>
          )}
          {rows.length === 0 && <div className="text-[11px] text-ink-400">No per-item breakdown reported by Lighthouse.</div>}
        </div>
      )}
    </div>
  );
}

function MetricDelta({ m }: { m: any }) {
  const c = m.weight > 25 ? "text-red-600" : m.weight > 5 ? "text-amber-600" : "text-ink-500";
  const d = m.deltaPct;
  const dir = d != null ? (d <= 0 ? "good" : "bad") : null;
  return (
    <div className="flex items-start gap-2 border border-ink-200 rounded-lg px-3 py-2">
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline justify-between gap-2">
          <span className="text-[12px] font-semibold text-ink-800 truncate">{m.title}</span>
          <span className={`text-[10px] font-bold shrink-0 ${c}`}>+{m.weight}</span>
        </div>
        <div className="flex items-baseline gap-1 mt-0.5">
          <span className="text-lg font-extrabold text-ink-900 font-mono">{m.displayValue}</span>
          {d != null && (
            <span className={`text-[10px] font-bold ${dir === "good" ? "text-emerald-600" : "text-red-600"}`}>
              {d > 0 ? `+${d}` : `${d}`}% vs good
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

function AuditLite({ a }: { a: any }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-ink-200 rounded-lg mb-1.5 overflow-hidden">
      <button onClick={() => setOpen((v) => !v)} className="w-full flex items-center gap-2 text-left px-3 py-2 hover:bg-ink-50">
        <span className="w-2 h-2 rounded-full bg-red-400 shrink-0" />
        <span className="flex-1 text-[12px] font-medium">{a.title}</span>
        {a.displayValue && <span className="text-[11px] text-ink-400">{a.displayValue}</span>}
      </button>
      {open && (
        <div className="px-4 pb-3">
          {a.description && <p className="text-[11px] text-ink-500 mb-2">{a.description}</p>}
          {a.items && a.items.length > 0 && a.items[0].selector ? (
            <div className="bg-ink-50 border border-ink-200 rounded p-2 space-y-1">
              {a.items.map((i: any, idx: number) => (
                <div key={idx} className="text-[10px] font-mono text-ink-600">
                  <span className="text-ink-300">{i.selector}</span>
                  {i.snippet && <div className="text-[9px] text-ink-400 truncate">{i.snippet}</div>}
                </div>
              ))}
            </div>
          ) : a.items && a.items.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {a.items.map((i: any, idx: number) => (
                <span key={idx} className="bg-ink-50 border border-ink-200 rounded px-2 py-0.5 text-[10px] text-ink-600">{i.detail || i.url}</span>
              ))}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

export default function LighthouseReport({ report, loading }: { report: any; loading?: boolean }) {
  const [showAll, setShowAll] = useState(false);

  if (loading) {
    return (
      <div className="card p-10 text-center">
        <div className="h-6 w-6 rounded-full border-2 border-ink-300 border-t-indigo-600 animate-spin mx-auto mb-3" />
        <div className="text-sm text-ink-600">Running Lighthouse (Performance, Accessibility, Best Practices, SEO)…</div>
        <div className="text-[11px] text-ink-400 mt-1">One real PageSpeed Insights call · ~20–60s · cached 10 min</div>
      </div>
    );
  }
  if (!report) return <div className="card p-8 text-center text-ink-500">No report yet — run a URL above.</div>;
  if (report.error) return <div className="card p-8 text-center text-crit">Lighthouse failed: {report.error}</div>;

  const perf = report.categories?.find((c: any) => c.id === "performance");
  const visualStart = 0;
  void visualStart;
  const opps = report.opportunities || [];
  const diags = report.diagnostics || [];
  const fieldM = report.fieldMetrics || {};

  return (
    <div className="space-y-4">
      {/* Strategy banner */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="text-[11px] text-ink-500 font-mono break-all">{report.url}</div>
        <div className="flex items-center gap-3 text-[10px] text-ink-400">
          <span>Emulated <b className="text-ink-600">{report.formFactor === "mobile" ? "Moto G Power" : "Desktop"}</b> · Lighthouse {report.lighthouseVersion}</span>
          <span className="bg-ink-100 px-2 py-0.5 rounded">GPSI</span>
        </div>
      </div>

      {/* Category score tiles */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        {report.categories.map((c: any) => (
          <ScoreRing key={c.id} score={c.score} />
        ))}
      </div>

      {/* Note about score */}
      {perf && (
        <p className="text-[11px] text-ink-400">
          Performance score is calculated directly from the weighted metrics below — real Lighthouse math, shown as-is.
        </p>
      )}

      {/* Metrics with weights */}
      {report.metricWeightsNote && report.metricWeightsNote.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">Metrics <span className="text-[10px] text-ink-400 font-normal">(weight contribution to the performance score)</span></div>
          <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-2">
            {report.metricWeightsNote.map((m: any, i: number) => <MetricDelta key={i} m={m} />)}
          </div>
        </div>
      )}

      {/* Final screenshot */}
      {report.finalScreenshot && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">Final Screenshot</div>
          <div className="rounded-lg border border-ink-200 overflow-hidden bg-white">
            <img src={report.finalScreenshot} alt="Final render" className="w-full max-h-[480px] object-cover object-top" loading="lazy" />
          </div>
        </div>
      )}

      {/* Field metrics */}
      {Object.keys(fieldM).length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">Field Data <span className="text-[10px] text-ink-400 font-normal">(CrUX, real users)</span></div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(fieldM).map(([k, v]: any) => (
              <div key={k} className="border border-ink-200 rounded-lg px-3 py-2 min-w-28">
                <div className="text-[11px] font-semibold text-ink-500">{k}</div>
                <div className="text-lg font-extrabold font-mono">{v.percentile ?? "—"}</div>
                <div className={`text-[10px] font-bold ${v.category === "GOOD" ? "text-emerald-600" : v.category === "NEEDS IMPROVEMENT" ? "text-amber-600" : "text-red-600"}`}>
                  {v.category || "—"}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Opportunities / Insights */}
      {opps.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">
            Insights <span className="text-[10px] text-ink-400 font-normal">({opps.length}) — opportunities with est. savings</span>
          </div>
          <div className="space-y-2">
            {opps.slice(0, showAll ? undefined : 6).map((o: any, i: number) => <Opportunity key={i} o={o} />)}
          </div>
        </div>
      )}

      {/* Diagnostics */}
      {diags.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">
            Diagnostics <span className="text-[10px] text-ink-400 font-normal">({diags.length}) — don't affect score directly, but matter</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {diags.slice(0, showAll ? undefined : 12).map((o: any, i: number) => (
              <span key={i} className="bg-ink-50 border border-ink-200 rounded-full px-2.5 py-1 text-[10px] text-ink-600" title={o.description}>
                {o.title} {o.displayValue ? `· ${o.displayValue}` : ""}
              </span>
            ))}
          </div>
        </div>
      )}

      {((opps.length > 6) || (diags.length > 12)) && (
        <div className="text-center">
          <button onClick={() => setShowAll((v) => !v)} className="text-[12px] font-semibold text-indigo-600 hover:underline">
            {showAll ? "Show fewer" : "Show all audits"}
          </button>
        </div>
      )}

      {/* Accessiblity fails */}
      {report.a11y && report.a11y.fails.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">
            Accessibility <span className="text-[10px] text-ink-400 font-normal">({report.a11y.fails.length} failing audits · {report.a11y.passed.length} passed)</span>
          </div>
          <div className="space-y-1.5">
            {report.a11y.fails.slice(0, showAll ? undefined : 8).map((a: any, i: number) => <AuditLite key={i} a={a} />)}
          </div>
        </div>
      )}

      {/* Best practices fails */}
      {report.bestPractices && report.bestPractices.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">
            Best Practices <span className="text-[10px] text-ink-400 font-normal">({report.bestPractices.length} failing)</span>
          </div>
          <div className="space-y-1.5">
            {report.bestPractices.slice(0, showAll ? undefined : 6).map((a: any, i: number) => <AuditLite key={i} a={a} />)}
          </div>
        </div>
      )}

      {/* SEO fails */}
      {report.seo && report.seo.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">
            SEO <span className="text-[10px] text-ink-400 font-normal">({report.seo.length} failing)</span>
          </div>
          <div className="space-y-1.5">
            {report.seo.slice(0, showAll ? undefined : 6).map((a: any, i: number) => <AuditLite key={i} a={a} />)}
          </div>
        </div>
      )}

      {/* Passed performance audits */}
      {report.passedPerformance && report.passedPerformance.length > 0 && (
        <div className="card p-4">
          <div className="text-[12px] font-bold mb-2">Passed audits <span className="text-[10px] text-ink-400 font-normal">({report.passedPerformance.length})</span></div>
          <div className="flex flex-wrap gap-1.5">
            {report.passedPerformance.slice(0, 30).map(([id, t]: any, i: number) => (
              <span key={i} className="bg-emerald-50 border border-emerald-200 text-emerald-700 rounded-full px-2.5 py-1 text-[10px]">{id.replace(/-/g, " ")}</span>
            ))}
          </div>
        </div>
      )}

      {/* Provenance */}
      <div className="text-[10px] text-ink-400 leading-relaxed">
        Generated by Lighthouse {report.lighthouseVersion} via PageSpeed Insights API · {report.strategy} strategy · {report.summary || "captured now"}.
        All values measured — accessibiity automated checks detect a subset only.
      </div>
    </div>
  );
}