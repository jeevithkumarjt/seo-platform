"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function AlertsPage() {
  const [alerts, setAlerts] = useState<any[]>([]);
  useEffect(() => { api.alerts().then((d) => setAlerts(d.alerts || [])).catch(() => {}); }, []);
  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Alerts — triggered issues feed</h1>
      <p className="text-ink-500 mb-3">Rank drop · CWV regression · site down · new critical · broken link · tag added/removed/changed · SSL/domain &lt;30d. In-platform feed is primary.</p>
      <div className="space-y-2">
        {alerts.map((a: any) => (
          <div key={a.id} className="card p-3 text-[13px]">
            <span className={`badge ${a.severity === "critical" ? "bg-red-100 text-crit border" : "bg-amber-100 text-warn border"}`}>{a.severity}</span>
            <span className="ml-2 font-semibold">{a.kind}</span>
            <span className="ml-2 text-ink-500">{new Date(a.created_at).toLocaleString()} · delivered: {String(a.delivered)}</span>
            <div className="mt-1">{a.message}</div>
          </div>
        ))}
        {!alerts.length && <div className="card p-6 text-center text-ink-500">No alerts yet.</div>}
      </div>
    </div>
  );
}
