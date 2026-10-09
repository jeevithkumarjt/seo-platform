import { CheckResult } from "@/lib/types";

const MAP: Record<string, string> = {
  pass: "bg-green-100 text-ok border border-green-300",
  info: "bg-ink-50 text-ink-700 border border-ink-300",
  warning: "bg-amber-100 text-warn border border-amber-300",
  fail: "bg-red-100 text-crit border border-red-300",
  unavailable: "bg-ink-100 text-mute border border-ink-300",
};

export function SeverityBadge({ status }: { status: CheckResult["status"] }) {
  return <span className={`badge ${MAP[status]}`}>{status.toUpperCase()}</span>;
}

export function SourceBadge({ source, confidence }: { source: string; confidence?: string }) {
  const star = confidence === "google-official" || source.includes("Search Console") ? " ★ highest trust" : "";
  const sample = source.includes("sample") || confidence === "sampled" ? " · sampled signal" : "";
  return <span className="badge bg-ink-100 text-ink-700 border border-ink-300/60" title={source}>{source.slice(0, 48)}{star}{sample}</span>;
}
