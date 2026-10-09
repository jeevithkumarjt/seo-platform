"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function TechStackPage() {
  const [sites, setSites] = useState<any[]>([]);
  const [siteId, setSiteId] = useState<number | null>(null);
  const [diff, setDiff] = useState<any>(null);
  useEffect(() => { api.sites().then((d) => { setSites(d.sites || []); if (d.sites?.[0]) setSiteId(d.sites[0].id); }).catch(() => {}); }, []);
  useEffect(() => { if (siteId) api.techDiff(siteId).then(setDiff).catch(() => {}); }, [siteId]);
  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Tech Stack — detected scripts/tags/pixels + diff</h1>
      <p className="text-ink-500 mb-3">Pattern-matched in network + DOM. First/last seen tracked; diffs trigger alerts.</p>
      <label className="text-[12px]">Site <select value={siteId ?? ""} onChange={(e) => setSiteId(Number(e.target.value))} className="border rounded px-2 py-1">
        {sites.map((s: any) => <option key={s.id} value={s.id}>{s.url}</option>)}
      </select></label>
      <div className="card p-4 mt-3 text-[13px]">
        {diff ? (<>
          <div>Added: <b className="text-warn">{(diff.added || []).join(", ") || "—"}</b></div>
          <div>Removed: <b className="text-crit">{(diff.removed || []).join(", ") || "—"}</b></div>
          <div className="text-ink-500 text-[12px] mt-1">{diff.note || `snapshots: ${diff.snapshots} · first ${diff.first_seen} · last ${diff.last_seen}`}</div>
        </>) : "Run at least two audits to compute a diff."}
      </div>
      <div className="card p-4 mt-3 text-[12px] text-ink-500">Vendors covered: GA4/UA, GTM, Meta, LinkedIn, TikTok, Google Ads, Bing UET, HubSpot, Marketo, Pardot, Apollo, Lusha, ZoomInfo, Clearbit, 6sense, Demandbase, Drift, Intercom, Hotjar, Clarity, Segment.</div>
    </div>
  );
}
