"use client";
import { useState } from "react";
import { api } from "@/lib/api";
import LighthouseReport from "@/components/performance/LighthouseReport";

export default function PerformancePage() {
  const [url, setUrl] = useState("");
  const [strategy, setStrategy] = useState<"mobile" | "desktop">("mobile");
  const [report, setReport] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState("");

  async function run() {
    if (!url.trim()) return;
    setLoading(true); setErr(""); setReport(null);
    try {
      setReport(await api.lighthouse(url.trim(), strategy));
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div>
      <div className="flex items-baseline justify-between mb-3 flex-wrap gap-1">
        <h1 className="text-xl font-bold">Performance Report</h1>
        <span className="text-[12px] text-ink-500">full Lighthouse report · Performance · Accessibility · Best Practices · SEO</span>
      </div>

      <div className="card p-4 mb-3">
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex-1 min-w-52 text-[12px] font-semibold text-ink-700">URL
            <input value={url} onChange={(e) => setUrl(e.target.value)} placeholder="https://yoursite.com"
              className="mt-1 border border-ink-300 rounded-md px-3 py-2 w-full text-sm focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500 outline-none" />
          </label>
          <label className="text-[12px] font-semibold text-ink-700">Strategy
            <select value={strategy} onChange={(e) => setStrategy(e.target.value as any)}
              className="mt-1 border border-ink-300 rounded-md px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500/40 outline-none">
              <option value="mobile">Mobile</option>
              <option value="desktop">Desktop</option>
            </select>
          </label>
          <button onClick={run} disabled={loading || !url}
            className="bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white px-6 py-2 rounded-md font-semibold transition disabled:opacity-40 shadow-sm">
            {loading ? "Running Lighthouse…" : "Run Lighthouse"}
          </button>
        </div>
      </div>

      {err && <div className="card p-3 mb-3 border-red-300 text-crit">{err}</div>}

      <LighthouseReport report={report} loading={loading} />

      {!report && !loading && (
        <div className="card p-10 text-center text-ink-500">
          <div className="text-4xl mb-3">⚡📊</div>
          <div className="mb-2">Paste a URL and click <span className="font-semibold">Run Lighthouse</span>.</div>
          <div className="max-w-lg mx-auto text-[12px] text-ink-400 space-y-1">
            <div>Category scores (Performance · Accessibility · Best Practices · SEO) with the exact Lighthouse metric weights.</div>
            <div>Insights show the <b>specific CSS/JS/DOM resources</b> — URL, transfer size, wasted bytes and estimated savings — so you can fix precisely what Lighthouse flags.</div>
          </div>
        </div>
      )}
    </div>
  );
}