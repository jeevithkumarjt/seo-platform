"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TrendChart } from "@/components/TrendChart";

export default function MonitoringPage() {
  const [sites, setSites] = useState<any[]>([]);
  const [siteId, setSiteId] = useState<number | null>(null);
  const [trend, setTrend] = useState<any[]>([]);
  const [sched, setSched] = useState<any[]>([]);
  const [addUrl, setAddUrl] = useState("");
  const [addLabel, setAddLabel] = useState("");
  const [addLocal, setAddLocal] = useState(false);
  const [addMsg, setAddMsg] = useState("");

  const load = async () => {
    const d = await api.sites();
    setSites(d.sites || []);
    if (d.sites?.[0] && !siteId) setSiteId(d.sites[0].id);
  };

  useEffect(() => { load().catch(() => {}); api.schedules().then((d) => setSched(d.schedules || [])).catch(() => {}); }, []);
  useEffect(() => { if (siteId) api.history(siteId).then((d) => setTrend(d.trend || [])).catch(() => {}); }, [siteId]);

  async function addSite() {
    if (!addUrl.trim()) return;
    setAddMsg(""); setAddMsg("Adding…");
    try {
      const s = await api.createSite({ url: addUrl.trim(), label: addLabel.trim() || undefined, is_local_business: addLocal });
      await load(); setSiteId(s.id); setAddUrl(""); setAddLabel(""); setAddLocal(false);
      setAddMsg(`Added ${s.url} (site #${s.id}).`);
    } catch (e: any) { setAddMsg(`Error: ${e.message}`); }
  }

  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Monitoring — schedules, history, uptime</h1>
      <p className="text-ink-500 mb-3">Per-site recurring checks (configurable per category). Every run persisted with timestamp.</p>
      <div className="card p-4 mb-3">
        <div className="font-semibold mb-2">Add a website to monitor</div>
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex-1 min-w-44">URL<input value={addUrl} onChange={(e) => setAddUrl(e.target.value)} placeholder="https://yoursite.com" className="border rounded px-3 py-2 w-full" /></label>
          <label>Label<input value={addLabel} onChange={(e) => setAddLabel(e.target.value)} placeholder="optional" className="border rounded px-3 py-2 w-40" /></label>
          <label className="text-[12px] flex items-center gap-1"><input type="checkbox" checked={addLocal} onChange={(e) => setAddLocal(e.target.checked)} /> local business (T)</label>
          <button onClick={addSite} className="bg-ink-900 text-white px-4 py-2 rounded">Add site</button>
        </div>
        {addMsg && <div className="text-[12px] mt-2">{addMsg}</div>}
      </div>
      <div className="card p-4 mb-3">
        <div className="font-semibold mb-1">Schedules (Technical / Performance / Tech Stack — cron each)</div>
        {sched.map((s: any) => <div key={s.id} className="text-[12px]">site {s.site_id} · {s.category} · {s.cron} · {s.enabled ? "enabled" : "paused"}</div>)}
        {!sched.length && <div className="text-[12px] text-ink-500">No schedules yet — audits create runs; add a schedule via API (POST /monitoring/schedules).</div>}
      </div>
      <label className="text-[12px]">Site <select value={siteId ?? ""} onChange={(e) => setSiteId(Number(e.target.value))} className="border rounded px-2 py-1">
        {sites.map((s: any) => <option key={s.id} value={s.id}>{s.url}</option>)}
      </select></label>
      <div className="grid grid-cols-2 gap-3 mt-3">
        <TrendChart label="Issue count over time" points={trend.map((t: any) => ({ at: t.at, value: (t.fail ?? 0) + (t.warning ?? 0), gap: t.gap }))} />
        <TrendChart label="Unavailable runs (data-quality)" points={trend.map((t: any) => ({ at: t.at, value: t.unavailable ?? 0, gap: false }))} />
      </div>
    </div>
  );
}
