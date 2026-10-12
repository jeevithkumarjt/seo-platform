import { DEMO, load, demoShot } from "./demo";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function j(res: Response) {
  if (!res.ok) throw new Error(`API ${res.status}: ${(await res.text()).slice(0, 200)}`);
  return res.json();
}

// In the static GitHub Pages build there is no backend: serve the real captured
// data (labelled "demo snapshot" in the UI). The live call is lazy, so demo mode
// never fires a network request and the snapshot is deterministic.
async function withDemo<T>(live: () => Promise<T>, file: string, map: (d: any) => T): Promise<T> {
  if (DEMO) return map(await load(file));
  return live();
}

const demoMap = (d: any) => d;

export const api = {
  base: BASE,
  demo: DEMO,
  runAudit: (body: any) =>
    withDemo(
      () => fetch(`${BASE}/api/v1/audit/run`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
      "audit.json",
      demoMap,
    ),
  history: (site_id: number) => withDemo(() => fetch(`${BASE}/api/v1/audit/history?site_id=${site_id}`).then(j), "audit.json", () => ({ trend: [] })),
  sites: () =>
    withDemo(() => fetch(`${BASE}/api/v1/sites`).then(j), "audit.json", (d) => ({
      sites: [{ id: 1, url: d.url, label: d.url }],
    })),
  createSite: (body: any) => fetch(`${BASE}/api/v1/sites`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  alerts: () => fetch(`${BASE}/api/v1/alerts`).then(j),
  integrations: () => fetch(`${BASE}/api/v1/integrations`).then(j),
  syncIntegration: (kind: string) => fetch(`${BASE}/api/v1/integrations/sync?kind=${kind}`, { method: "POST" }).then(j),
  techDiff: (site_id: number) => fetch(`${BASE}/api/v1/techstack/diff?site_id=${site_id}`).then(j),
  compare: (ids: number[]) => fetch(`${BASE}/api/v1/sites/compare?ids=${ids.join(",")}`).then(j),
  schedules: () => fetch(`${BASE}/api/v1/monitoring/schedules`).then(j),
  saveSchedule: (body: any) => fetch(`${BASE}/api/v1/monitoring/schedules`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(j),
  screenshot: (url: string) =>
    withDemo(
      () => fetch(`${BASE}/api/v1/audit/screenshot?url=${encodeURIComponent(url)}&data_url=true`).then(j),
      "screenshot.json",
      (d) => ({ dataUrl: d.dataUrl }),
    ),
  designView: (url: string, engine: string = "chromium") => fetch(`${BASE}/api/v1/audit/design?url=${encodeURIComponent(url)}&engine=${engine}`).then(j),
  designCell: (url: string, engine: string, device: string) => fetch(`${BASE}/api/v1/audit/design?url=${encodeURIComponent(url)}&engine=${engine}&device=${encodeURIComponent(device)}`).then(j),
  responsive: (url: string, engine: string = "chromium", category: string | null = null) =>
    withDemo(
      () => fetch(`${BASE}/api/v1/audit/responsive?url=${encodeURIComponent(url)}&engine=${engine}${category ? "&category=" + category : ""}`).then(j),
      "responsive_demo.json",
      (d) => {
        // demo JSON stores relative paths (./shots/…) — prefix with basePath
        for (const cat of Object.values<any>(d.categories || {})) {
          for (const dev of Object.values<any>(cat.devices || {})) {
            if (dev.dataUrl && dev.dataUrl.startsWith("./")) dev.dataUrl = demoShot(dev.dataUrl);
          }
        }
        return d;
      },
    ),
  frameable: (url: string) => withDemo(() => fetch(`${BASE}/api/v1/audit/frameable?url=${encodeURIComponent(url)}`).then(j), "audit.json", () => ({ frameable: true })),
  devices: () => withDemo(() => fetch(`${BASE}/api/v1/audit/devices`).then(j), "devices.json", demoMap),
  lighthouse: (url: string, strategy: string = "mobile") =>
    withDemo(() => fetch(`${BASE}/api/v1/audit/lighthouse?url=${encodeURIComponent(url)}&strategy=${strategy}`).then(j), "lighthouse.json", demoMap),
};
