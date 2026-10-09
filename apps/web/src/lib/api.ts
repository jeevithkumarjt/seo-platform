const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function j(res: Response) {
  if (!res.ok) throw new Error(`API ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

export const api = {
  base: BASE,
  runAudit: (body: any) => fetch(`${BASE}/api/v1/audit/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  history: (site_id: number) => fetch(`${BASE}/api/v1/audit/history?site_id=${site_id}`).then(j),
  sites: () => fetch(`${BASE}/api/v1/sites`).then(j),
  createSite: (body: any) => fetch(`${BASE}/api/v1/sites`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  alerts: () => fetch(`${BASE}/api/v1/alerts`).then(j),
  integrations: () => fetch(`${BASE}/api/v1/integrations`).then(j),
  syncIntegration: (kind: string) => fetch(`${BASE}/api/v1/integrations/sync?kind=${kind}`, { method: "POST" }).then(j),
  techDiff: (site_id: number) => fetch(`${BASE}/api/v1/techstack/diff?site_id=${site_id}`).then(j),
  compare: (ids: number[]) => fetch(`${BASE}/api/v1/sites/compare?ids=${ids.join(",")}`).then(j),
  schedules: () => fetch(`${BASE}/api/v1/monitoring/schedules`).then(j),
  saveSchedule: (body: any) => fetch(`${BASE}/api/v1/monitoring/schedules`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  screenshot: (url: string) => fetch(`${BASE}/api/v1/audit/screenshot?url=${encodeURIComponent(url)}&data_url=true`).then(j),
  designView: (url: string, engine: string = "chromium") => fetch(`${BASE}/api/v1/audit/design?url=${encodeURIComponent(url)}&engine=${engine}`).then(j),
  designCell: (url: string, engine: string, device: string) => fetch(`${BASE}/api/v1/audit/design?url=${encodeURIComponent(url)}&engine=${engine}&device=${encodeURIComponent(device)}`).then(j),
  responsive: (url: string, engine: string = "chromium", category: string | null = null) => fetch(`${BASE}/api/v1/audit/responsive?url=${encodeURIComponent(url)}&engine=${engine}${category ? "&category=" + category : ""}`).then(j),
  frameable: (url: string) => fetch(`${BASE}/api/v1/audit/frameable?url=${encodeURIComponent(url)}`).then(j),
  devices: () => fetch(`${BASE}/api/v1/audit/devices`).then(j),
  lighthouse: (url: string, strategy: string = "mobile") => fetch(`${BASE}/api/v1/audit/lighthouse?url=${encodeURIComponent(url)}&strategy=${strategy}`).then(j),
};
