"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export default function IntegrationsPage() {
  const [data, setData] = useState<any>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [msg, setMsg] = useState<string>("");
  async function load() { setData(await api.integrations().catch(() => null)); }
  useEffect(() => { load(); }, []);
  async function probe(kind: string) {
    setBusy(kind); setMsg("");
    try { const r = await api.syncIntegration(kind); setMsg(`${kind}: ${r.sync} — ${r.detail || ""}`); }
    catch (e: any) { setMsg(`${kind}: probe error — ${e.message}`); }
    finally { setBusy(null); load(); }
  }
  return (
    <div>
      <h1 className="text-xl font-bold mb-1">Integrations — sources & sync status</h1>
      <p className="text-ink-500 mb-3">Each source shows connection status + last successful sync. Highest-trust (GSC) is badged ★. Probes run a <b>live</b> validation — status is never assumed.</p>
      {msg && <div className="card p-3 mb-3 text-[12px]">{msg}</div>}
      <div className="grid grid-cols-1 gap-2">
        {data && Object.values(data.integrations).map((g: any) => (
          <div key={g.kind} className="card p-4 flex items-center justify-between gap-3">
            <div>
              <div className="font-semibold">{g.kind} {g.kind === "gsc" && <span className="badge bg-green-100 text-ok border">★ highest trust (Google-official)</span>}</div>
              <div className="text-[12px] text-ink-500">{g.note}</div>
              <div className="text-[12px]">status: <b className={g.status === "connected" ? "text-ok" : "text-crit"}>{g.status}</b> · last successful sync: {g.last_sync_at ? new Date(g.last_sync_at).toLocaleString() : "never"}</div>
              <div className="text-[11px] text-ink-500">last attempt: {g.last_attempt_at ? new Date(g.last_attempt_at).toLocaleString() : "never"}{g.last_error ? ` · error: ${g.last_error}` : ""}</div>
            </div>
            <button onClick={() => probe(g.kind)} disabled={busy === g.kind} className="border rounded px-3 py-1 text-[12px] shrink-0">
              {busy === g.kind ? "Probing…" : "Probe sync"}
            </button>
          </div>
        ))}
        {!data && <div className="card p-6 text-ink-500 text-[13px]">Loading… (is the API up at {process.env.NEXT_PUBLIC_API_URL}?)</div>}
      </div>
    </div>
  );
}
