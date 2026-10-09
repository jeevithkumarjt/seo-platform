"use client";
import { useEffect, useMemo, useRef, useState } from "react";
import { api } from "@/lib/api";
import { CATEGORIES, CheckResult } from "@/lib/types";
import { ResultCard } from "@/components/ResultCard";
import { DesignViewPanel } from "@/components/design/DesignViewPanel";
import { PerfDeepDive } from "@/components/performance/PerfDeepDive";
import LighthouseReport from "@/components/performance/LighthouseReport";

const STEPS = [
  { id: "fetch", label: "Fetching page" },
  { id: "onpage", label: "Running on-page & content checks" },
  { id: "lighthouse", label: "Lighthouse · performance / a11y / front-end" },
  { id: "crawl", label: "Links · architecture · tech stack" },
  { id: "browser", label: "Cross-browser rendering (3 engines)" },
  { id: "rank", label: "Rank · GSC health" },
  { id: "done", label: "Building report" },
];

type CatQ = "ok" | "warning" | "critical" | "unknown";

function catWorst(res: CheckResult[]): CatQ {
  if (res.some((r) => r.status === "fail")) return "critical";
  if (res.some((r) => r.status === "warning")) return "warning";
  if (res.some((r) => r.status === "unavailable")) return "unknown";
  return "ok";
}

const CAT_ACCENT = [
  { bg: "bg-indigo-500", soft: "bg-indigo-50 text-indigo-700", ring: "ring-indigo-500" },
  { bg: "bg-sky-500", soft: "bg-sky-50 text-sky-700", ring: "ring-sky-500" },
  { bg: "bg-emerald-500", soft: "bg-emerald-50 text-emerald-700", ring: "ring-emerald-500" },
  { bg: "bg-amber-500", soft: "bg-amber-50 text-amber-700", ring: "ring-amber-500" },
  { bg: "bg-violet-500", soft: "bg-violet-50 text-violet-700", ring: "ring-violet-500" },
  { bg: "bg-rose-500", soft: "bg-rose-50 text-rose-700", ring: "ring-rose-500" },
  { bg: "bg-cyan-500", soft: "bg-cyan-50 text-cyan-700", ring: "ring-cyan-500" },
  { bg: "bg-teal-500", soft: "bg-teal-50 text-teal-700", ring: "ring-teal-500" },
];

const STATUS_COLOR: Record<string, string> = {
  ok: "#15803d", warning: "#b45309", fail: "#b91c1c", unavailable: "#cbd5e1",
};
const STATUS_BG: Record<string, string> = {
  ok: "bg-ok", warning: "bg-warn", fail: "bg-crit", unavailable: "bg-ink-300",
};
const STATUS_BADGE: Record<string, string> = {
  ok: "bg-ok/10 text-ok border-ok/30",
  warning: "bg-warn/10 text-warn border-warn/30",
  fail: "bg-crit/10 text-crit border-crit/30",
  unavailable: "bg-ink-50 text-ink-500 border-ink-300/60",
};

function Donut({ pass, warning, fail, unavailable }: { pass: number; warning: number; fail: number; unavailable: number }) {
  const total = Math.max(pass + warning + fail + unavailable, 1);
  const r = 48, C = 2 * Math.PI * r;
  const segs = [
    { v: pass, color: STATUS_COLOR.ok },
    { v: warning, color: STATUS_COLOR.warning },
    { v: fail, color: STATUS_COLOR.fail },
    { v: unavailable, color: STATUS_COLOR.unavailable },
  ];
  let acc = 0;
  return (
    <div className="relative h-32 w-32 shrink-0">
      <svg viewBox="0 0 130 130" className="h-full w-full">
        <circle cx="65" cy="65" r={r} fill="none" stroke="#f1f5f9" strokeWidth="15" />
        {segs.map((s, i) => {
          if (s.v <= 0) return null;
          const len = (s.v / total) * C;
          const el = (
            <circle key={i} cx="65" cy="65" r={r} fill="none" stroke={s.color} strokeWidth="15"
              strokeDasharray={`${len} ${C - len}`} strokeDashoffset={-acc} transform="rotate(-90 65 65)" />
          );
          acc += len;
          return el;
        })}
      </svg>
      <div className="absolute inset-0 grid place-items-center text-center">
        <div>
          <div className="text-2xl font-extrabold leading-none text-ink-900">{total}</div>
          <div className="text-[10px] uppercase tracking-wider text-ink-400 mt-0.5">checks</div>
        </div>
      </div>
    </div>
  );
}

function MiniDonut({ p, w, f, u }: { p: number; w: number; f: number; u: number }) {
  const t = Math.max(p + w + f + u, 1);
  let acc = 0;
  return (
    <svg viewBox="0 0 40 40" className="h-9 w-9 shrink-0 -rotate-90">
      <circle cx="20" cy="20" r="16" fill="none" stroke="#e2e8f0" strokeWidth="7" />
      {[
        { v: p, c: STATUS_COLOR.ok },
        { v: w, c: STATUS_COLOR.warning },
        { v: f, c: STATUS_COLOR.fail },
        { v: u, c: STATUS_COLOR.unavailable },
      ].map((s, i) => {
        if (s.v <= 0) return null;
        const len = (s.v / t) * (2 * Math.PI * 16);
        const el = <circle key={i} cx="20" cy="20" r="16" fill="none" stroke={s.c} strokeWidth="7"
          strokeDasharray={`${len} ${2 * Math.PI * 16 - len}`} strokeDashoffset={-acc} />;
        acc += len;
        return el;
      })}
    </svg>
  );
}

/* Browser-frame around a live site screenshot (from our Playwright capture) */
function BrowserFrame({ src, loading }: { src?: string; loading: boolean }) {
  return (
    <div className="overflow-hidden rounded-xl border border-ink-300/60 shadow-sm bg-white">
      <div className="flex items-center gap-1.5 px-3 py-2 bg-ink-900">
        <span className="h-2.5 w-2.5 rounded-full bg-red-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-amber-400" />
        <span className="h-2.5 w-2.5 rounded-full bg-green-400" />
        <span className="ml-2 flex-1 truncate rounded bg-white/10 px-2 py-0.5 text-[10px] text-white/70 font-mono" />
      </div>
      <div className="relative aspect-[3/2] bg-ink-50">
        {loading && <div className="absolute inset-0 grid place-items-center text-ink-400 text-xs">Capturing live screenshot…</div>}
        {src && <img src={src} alt="live site capture" className="h-full w-full object-cover object-top" />}
      </div>
    </div>
  );
}

export default function AuditPage() {
  const [url, setUrl] = useState("");
  const [keyword, setKeyword] = useState("");
  const [isLocal, setIsLocal] = useState(false);
  const [tab, setTab] = useState("A-onpage");
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");
  const [step, setStep] = useState(-1);
  const [elapsed, setElapsed] = useState(0);
  const [logs, setLogs] = useState<string[]>([]);
  const [shot, setShot] = useState<string | undefined>();
  const [lh, setLh] = useState<any>(null);
  const [lhLoading, setLhLoading] = useState(false);
  const [lhStrategy, setLhStrategy] = useState<"mobile" | "desktop">("mobile");
  const timer = useRef<any>(null);
  const stepIdx = useRef(0);
  const resultsRef = useRef<HTMLDivElement>(null);

  const STEP_MS = [1200, 700, 1400, 800, 1800, 900, 600];

  function advanceStep() {
    setStep(stepIdx.current);
    const delay = STEP_MS[stepIdx.current] ?? 600;
    stepIdx.current += 1;
    if (stepIdx.current < STEPS.length) {
      setTimeout(() => { setLogs((l) => [...l, STEPS[stepIdx.current - 1]?.id || ""]); advanceStep(); }, delay);
    }
  }

  async function run() {
    if (!url.trim()) return;
    setLoading(true); setErr(""); setData(null); setShot(undefined); setLh(null); setLhLoading(false);
    setElapsed(0); stepIdx.current = 0; setStep(-1);
    setLogs([`STARTING audit for ${url.trim()}`]);
    timer.current = setInterval(() => setElapsed((s) => s + 1), 1000);
    advanceStep();
    const t0 = Date.now();
    setShot(undefined);
    api.screenshot(url.trim()).then((r) => setShot(r.dataUrl)).catch(() => {});
    try {
      const res = await api.runAudit({ url, keyword: keyword || null, is_local_business: isLocal, include_rendered: true });
      setData(res);
      stepIdx.current = STEPS.length; setStep(STEPS.length - 1);
      setLogs((l) => [...l, `DONE ${res.results.length} checks in ${((Date.now() - t0) / 1000).toFixed(1)}s`]);
    } catch (e: any) {
      setErr(e.message);
      setLogs((l) => [...l, `FAILED ${e.message}`]);
    } finally {
      clearInterval(timer.current);
      setLoading(false);
    }
  }

  useEffect(() => () => clearInterval(timer.current), []);

  const results: CheckResult[] = data?.results || [];
  const byCat = useMemo(() => {
    const m: Record<string, CheckResult[]> = {};
    for (const r of results) (m[r.category] = m[r.category] || []).push(r);
    return m;
  }, [results]);
  const filtered = useMemo(() => results.filter((r) => r.category === tab), [results, tab]);
  const worst = useMemo(() => catWorst(filtered), [filtered]);

  const s = data?.summary || {};
  const overall = s.fail > 0 ? "Needs attention" : s.warning > 0 ? "Needs review" : "Healthy";
  const overallCls = s.fail > 0 ? "text-crit" : s.warning > 0 ? "text-warn" : "text-ok";
  const overallBadge = s.fail > 0 ? "bg-crit/10 text-crit border-crit/30" : s.warning > 0 ? "bg-warn/10 text-warn border-warn/30" : "bg-ok/10 text-ok border-ok/30";

  const mm = String(Math.floor(elapsed / 60)).padStart(2, "0");
  const ss = String(elapsed % 60).padStart(2, "0");

  function pickCat(id: string) {
    setTab(id);
    requestAnimationFrame(() => resultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }));
  }

  async function runLighthouse() {
    if (!data?.url) return;
    setLhLoading(true);
    try { setLh(await api.lighthouse(data.url, lhStrategy)); }
    catch (e: any) { setLh({ error: e.message }); }
    finally { setLhLoading(false); }
  }

  const accIdx = useMemo(() => Object.fromEntries(CATEGORIES.map((c, i) => [c.id, CAT_ACCENT[i % CAT_ACCENT.length]])), []);
  const catList = useMemo(() => CATEGORIES.filter((c) => (byCat[c.id] || []).length), [byCat]);

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3">
        <h1 className="text-xl font-bold">Site Audit</h1>
        <span className="text-[12px] text-ink-500">runs on our backend · free APIs · nothing links out</span>
      </div>

      <div className="card p-4 mb-3">
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex-1 min-w-52 text-[12px] font-semibold text-ink-700">URL
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://yoursite.com" className="mt-1 border border-ink-300 rounded-md px-3 py-2 w-full text-sm focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 outline-none" />
          </label>
          <label className="text-[12px] font-semibold text-ink-700">Keyword (G)
            <input value={keyword} onChange={(e) => setKeyword(e.target.value)} placeholder="optional" className="mt-1 border border-ink-300 rounded-md px-3 py-2 w-44 text-sm focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 outline-none" />
          </label>
          <label className="text-[12px] flex items-center gap-1.5 pb-2"><input type="checkbox" checked={isLocal} onChange={(e) => setIsLocal(e.target.checked)} /> local business (T)</label>
          <button onClick={run} disabled={loading || !url}
            className="bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white px-6 py-2 rounded-md font-semibold transition disabled:opacity-40 shadow-sm">
            {loading ? `Auditing… ${mm}:${ss}` : "Run audit"}
          </button>
        </div>
      </div>

      {err && <div className="card p-3 mb-3 border-red-300 text-crit">{err}</div>}

      {loading && (
        <div className="card p-5 mb-3">
          <div className="flex items-center gap-3 mb-3">
            <div className="h-5 w-5 rounded-full border-2 border-ink-300 border-t-indigo-600 animate-spin"></div>
            <div className="font-semibold">Auditing <span className="text-ink-500">{url}</span></div>
            <div className="ml-auto font-mono text-[12px] text-ink-500">{mm}:{ss}</div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-1">
            {STEPS.map((s2, i) => (
              <div key={s2.id} className="flex items-center gap-2 px-2 py-1">
                <span className={`h-2 w-2 rounded-full ${i < step ? "bg-ok" : i === step ? "bg-indigo-600 animate-pulse" : "bg-ink-200"}`}></span>
                <span className={`text-[12px] ${i < step ? "text-ok" : i === step ? "font-semibold text-ink-900" : "text-ink-400"}`}>{s2.label}</span>
              </div>
            ))}
          </div>
          <div className="mt-3 border-t pt-2">
            {logs.slice(-3).map((l, i) => <div key={i} className="font-mono text-[11px] text-ink-500">› {l}</div>)}
          </div>
        </div>
      )}

      {data && !loading && (
        <>
          {/* HERO: site preview + health */}
          <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1fr)_320px] gap-3 mb-3">
            <BrowserFrame src={shot} loading={!shot} />

            <div className="card p-4 flex flex-col gap-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  <span className="badge bg-ink-900 text-white">{new URL(data.url).hostname}</span>
                  <span className={`badge border ${overallBadge}`}>{overall}</span>
                </div>
                <button onClick={() => api.screenshot(data.url).then((r) => setShot(r.dataUrl)).catch(() => {})}
                  className="text-[11px] font-semibold text-indigo-600 hover:text-indigo-800">⟳ capture</button>
              </div>

              <div className="flex items-center gap-4">
                <Donut pass={s.pass ?? 0} warning={s.warning ?? 0} fail={s.fail ?? 0} unavailable={s.unavailable ?? 0} />
                <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[12px] min-w-0">
                  <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-ok inline-block" /> Pass <b className="ml-auto">{s.pass}</b></span>
                  <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-warn inline-block" /> Warn <b className="ml-auto">{s.warning}</b></span>
                  <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-crit inline-block" /> Fail <b className="ml-auto">{s.fail}</b></span>
                  <span className="flex items-center gap-1.5"><i className="h-2.5 w-2.5 rounded-full bg-ink-300 inline-block" /> Unavail <b className="ml-auto">{s.unavailable}</b></span>
                </div>
              </div>

              <div className="mt-auto border-t pt-2 text-[11px] text-ink-500">
                finished {new Date(data.finished_at).toLocaleString()} · started {new Date(data.started_at).toLocaleTimeString()}
              </div>
            </div>
          </div>

          {/* PERFORMANCE DEEP-DIVE (D-performance + S-frontend) */}
          {results.some((r) => r.category === "D-performance") && <PerfDeepDive checks={results} />}

          {/* FULL LIGHTHOUSE REPORT (PSI · on demand) */}
          <div className="mb-3">
            <div className="card p-3 mb-3 flex flex-wrap items-center gap-2">
              <div className="mr-1">
                <div className="text-[13px] font-bold text-ink-900">Full Lighthouse report</div>
                <div className="text-[11px] text-ink-400">PageSpeed Insights — score, weighted metrics, per-resource insights, a11y</div>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <label className="text-[11px] font-semibold text-ink-600">Strategy
                  <select value={lhStrategy} onChange={(e) => setLhStrategy(e.target.value as "mobile" | "desktop")}
                    className="ml-1 border border-ink-300 rounded-md px-2 py-1.5 text-[11px] outline-none focus:ring-2 focus:ring-indigo-500/40">
                    <option value="mobile">Mobile</option>
                    <option value="desktop">Desktop</option>
                  </select>
                </label>
                <button onClick={runLighthouse} disabled={lhLoading}
                  className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-md text-[12px] font-semibold transition disabled:opacity-40 shadow-sm">
                  {lhLoading ? "Running…" : lh ? "Re-run" : "Run report"}
                </button>
              </div>
            </div>
            {lh && <LighthouseReport report={lh} loading={lhLoading} />}
          </div>

          {/* RESPONSIVE DESIGN VIEW (H-xbrowser screenshots per engine/device) */}
          {results.some((r) => r.key.startsWith("h-screenshot-")) && <DesignViewPanel checks={results} />}

          {/* CATEGORY HEALTH */}
          <div className="mb-3">
            <div className="text-[11px] uppercase tracking-wide text-ink-500 font-semibold mb-2">Category health</div>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-2">
              {catList.map((c, idx) => {
                const rows = byCat[c.id] || [];
                const w = catWorst(rows);
                const p = rows.filter((r) => r.status === "pass" || r.status === "info").length;
                const wC = rows.filter((r) => r.status === "warning").length;
                const f = rows.filter((r) => r.status === "fail").length;
                const u = rows.length - p - wC - f;
                const wp = Math.round((wC) / rows.length * 100);
                const fp = Math.round((f) / rows.length * 100);
                const up = Math.round((u) / rows.length * 100);
                const okp = 100 - wp - fp - up;
                const accent = CAT_ACCENT[idx % CAT_ACCENT.length];
                const active = tab === c.id;
                return (
                  <button key={c.id} onClick={() => pickCat(c.id)}
                    className={`card p-3 text-left transition hover:-translate-y-0.5 hover:shadow-md ${active ? "ring-2 ring-indigo-500" : ""}`}>
                    <div className="flex items-center gap-2 mb-2">
                      <MiniDonut p={p} w={wC} f={f} u={u} />
                      <div className="min-w-0">
                        <div className="flex items-center gap-1.5">
                          <span className={`h-4 w-4 shrink-0 rounded grid place-items-center text-[9px] font-bold text-white ${accent.bg}`}>{c.code}</span>
                          <span className="text-[12px] font-semibold truncate">{c.name}</span>
                        </div>
                        <div className="text-[11px] text-ink-500">{rows.length} checks · {w === "ok" ? "all good" : w === "critical" ? "action needed" : w === "warning" ? "review" : "no data"}</div>
                      </div>
                    </div>
                    <div className="flex h-1.5 overflow-hidden rounded bg-ink-100 mt-1">
                      {okp > 0 && <i className="bg-ok h-full" style={{ width: `${okp}%` }} />}
                      {wp > 0 && <i className="bg-warn h-full" style={{ width: `${wp}%` }} />}
                      {fp > 0 && <i className="bg-crit h-full" style={{ width: `${fp}%` }} />}
                      {up > 0 && <i className="bg-ink-300 h-full" style={{ width: `${up}%` }} />}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}

      <div ref={resultsRef}>
        {data && !loading && (
          <>
            <div className="flex items-center gap-2 mt-2 mb-2">
              <h2 className="text-[13px] font-bold">{tab} results</h2>
              <span className={`badge border ${STATUS_BADGE[worst]}`}>
                {worst === "ok" ? "All passing" : worst === "warning" ? "Needs review" : worst === "critical" ? "Action required" : "Data unavailable"}
              </span>
            </div>
            <div className="grid grid-cols-1 gap-2">
              {filtered.map((r) => <ResultCard key={r.key} r={r} />)}
              {!filtered.length && <div className="card p-4 text-ink-500">No checks in this sub-category for this run.</div>}
            </div>
          </>
        )}
        {!data && (
          <div className="card p-10 text-center text-ink-500">
            <div className="text-3xl mb-2">🛠</div>
            <div className="mb-3">Enter a URL and click <span className="font-semibold">Run audit</span>.</div>
            <div className="max-w-md mx-auto text-[12px] text-ink-400">
              19 categories · 80+ measured checks · real PageSpeed + Search Console data ·
              cross-browser rendering · live site screenshot · <span className="text-ink-500">no invented scores</span>.
              The report appears here in 1–3 minutes.
            </div>
          </div>
        )}
      </div>
    </div>
  );
}