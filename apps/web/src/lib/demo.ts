// Static-demo helpers — used only when the app is built for GitHub Pages
// (NEXT_PUBLIC_DEMO=1). Real measured data captured from our own backend,
// served as static JSON. The normal docker build never includes this path.

const BASE = process.env.NEXT_PUBLIC_DEMO_BASE || "";
export const DEMO = process.env.NEXT_PUBLIC_DEMO === "1";

const cache: Record<string, any> = {};

export async function load(file: string): Promise<any> {
  if (cache[file]) return cache[file];
  const r = await fetch(`${BASE}/demo/${file}`);
  if (!r.ok) throw new Error(`demo data missing: ${file}`);
  const j = await r.json();
  cache[file] = j;
  return j;
}

export const demoShot = (p: string) => `${BASE}/demo/${p.replace("./", "")}`;
