"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendChart } from "@/components/TrendChart";

export default function OverviewPage() {
  const [sites, setSites] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [trend, setTrend] = useState<any[]>([]);
  const [sel, setSel] = useState<number[]>([]);
  const [cmp, setCmp] = useState<any>(null);

  useEffect(() => {
    api.sites().then((d) => setSites(d.sites || [])).catch(() => {});
    api.alerts().then((d) => setAlerts((d.alerts || []).slice(0, 8))).catch(() => {});
  }, []);

  useEffect(() => {
    if (sites[0]) api.history(sites[0].id).then((d) => setTrend(d.trend || [])).catch(() => {});
  }, [sites]);

  const sev = (s: string) => s === "critical" ? "text-crit" : s === "warning" ? "text-warn" : "text-ink-500";

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Overview — cross-site health</h1>
      <p className="text-ink-500 mb-4">Landing screen. All data measured in-platform; no external tool links.</p>
      <div className="grid grid-cols-4 gap-3 mb-4">
        {[["Sites monitored", sites.length], ["Recent alerts", alerts.length],
          ["Critical (feed)", alerts.filter((a) => a.severity === "critical").length],
          ["Schedules", "per-category"]].map(([k, v]) => (
          <div key={k as string} className="card p-4"><div className="text-[11px] text-ink-500">{k}</div><div className="text-2xl font-bold">{v as any}</div></div>
        ))}
      </div>
      <div className="grid grid-cols-2 gap-3">
        <TrendChart label="Issue count over time (first site)" points={trend.map((t: any) => ({ at: t.at, value: (t.fail ?? 0) + (t.warning ?? 0), gap: t.gap }))} />
        <div className="card p-4">
          <div className="font-semibold mb-2">Recent alerts (in-platform feed)</div>
          <div className="space-y-1 max-h-48 overflow-auto">
            {alerts.map((a: any) => <div key={a.id} className="text-[12px]"><span className={sev(a.severity)}>{a.severity}</span> · {a.kind} · {a.message.slice(0, 90)}</div>)}
            {!alerts.length && <div className="text-ink-500 text-[12px]">No alerts yet. Run an audit.</div>}
          </div>
        </div>
      </div>
      <div className="card p-4 mt-3 text-[12px] text-ink-500">
        Disclosed limits: Search Console links report is the ceiling for backlinks (no DA shown) · AEO/GEO is a sampled signal, not a ranking metric.
        External competitor authority/backlink totals cannot be measured exactly on free data and are never shown — compare only your own measured sites below.
      </div>
      <div className="card p-4 mt-3">
        <div className="font-semibold mb-1">Compare monitored sites (your own measured audits)</div>
        <div className="flex flex-wrap gap-2 mb-2">
          {sites.map((s: any) => (
            <label key={s.id} className="text-[12px] border rounded px-2 py-1 cursor-pointer">
              <input type="checkbox" className="mr-1" checked={sel.includes(s.id)}
                onChange={() => setSel(sel.includes(s.id) ? sel.filter((x) => x !== s.id) : [...sel, s.id])} />
              {s.label || s.url}
            </label>
          ))}
          {!sites.length && <span className="text-[12px] text-ink-500">No sites yet — run an audit first.</span>}
        </div>
        <button disabled={sel.length < 2} onClick={() => api.compare(sel).then(setCmp).catch(() => {})}
          className="border rounded px-3 py-1 text-[12px] disabled:opacity-40">Compare selected</button>
        {cmp && (
          <table className="w-full text-[12px] mt-2 border-collapse">
            <thead><tr className="text-left text-ink-500">
              <th className="border-b p-1">Site</th><th className="border-b p-1">Pass</th><th className="border-b p-1">Warn</th>
              <th className="border-b p-1">Fail</th><th className="border-b p-1">Unavailable</th><th className="border-b p-1">Last run</th>
            </tr></thead>
            <tbody>
              {cmp.compare.map((c: any) => (
                <tr key={c.site_id}>
                  <td className="border-b p-1">{c.site?.url || "unknown"}</td>
                  {c.summary
                    ? (<><td className="border-b p-1 text-ok">{c.summary.pass}</td><td className="border-b p-1 text-warn">{c.summary.warning}</td>
                        <td className="border-b p-1 text-crit">{c.summary.fail}</td><td className="border-b p-1 text-ink-500">{c.summary.unavailable}</td>
                        <td className="border-b p-1">{new Date(c.last_run_at).toLocaleString()}</td></>)
                    : <td colSpan={5} className="border-b p-1 text-ink-500">no stored run — null, never interpolated</td>}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
