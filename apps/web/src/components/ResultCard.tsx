import { CheckResult } from "@/lib/types";
import { SeverityBadge, SourceBadge } from "./badges";
import { EvidenceView } from "./evidence/EvidenceView";

/** Uniform card: what → evidence (smart-rendered) → why → fix → timestamp. Never links out to origin tools. */
export function ResultCard({ r }: { r: CheckResult }) {
  const gray = r.status === "unavailable";
  const status = r.status === "fail" ? "fail" : r.status === "warning" ? "warning" : r.status === "unavailable" ? "unavailable" : "ok";

  const ACCENT: Record<string, string> = {
    ok: "border-l-ok bg-ok/[0.02]",
    warning: "border-l-warn bg-warn/[0.02]",
    fail: "border-l-crit bg-crit/[0.02]",
    unavailable: "border-l-mute bg-ink-50/40",
  };
  const DOT: Record<string, string> = { ok: "bg-ok", warning: "bg-warn", fail: "bg-crit", unavailable: "bg-mute" };

  return (
    <div className={`card p-4 border-l-4 ${ACCENT[status]} ${gray ? "opacity-90 border-dashed" : ""}`}>
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className={`h-2 w-2 shrink-0 rounded-full ${DOT[status]}`} />
            <h3 className="font-semibold text-ink-900 truncate">{r.label}</h3>
          </div>
          <div className="text-[12px] text-ink-500 mt-0.5">{r.category}</div>
        </div>
        <SeverityBadge status={r.status} />
      </div>

      <div className="text-[13px] mb-2 pl-4">
        <span className="text-ink-500">Found: </span>
        <span className="text-ink-800">{r.found || "—"}</span>
      </div>

      <div className="flex flex-wrap gap-1.5 mb-2 pl-4">
        <SourceBadge source={r.source} confidence={r.confidence} />
        <span className="badge bg-ink-50 text-ink-500 border border-ink-300/60">checked {new Date(r.checked_at).toLocaleString()}</span>
      </div>

      {r.evidence !== null && r.evidence !== undefined && (
        <div className="mb-2.5 pl-4">
          <div className="text-[10px] uppercase tracking-wide font-semibold text-ink-400 mb-1.5">Details</div>
          <div className="px-3 py-2.5 rounded-md bg-ink-50/70 border border-ink-300/50">
            <EvidenceView evidence={r.evidence} />
          </div>
        </div>
      )}

      {r.why_matters && <div className="text-[12px] text-ink-700 pl-4"><span className="font-semibold">Why: </span>{r.why_matters}</div>}
      {r.how_to_fix
        ? <div className="text-[12px] text-ink-700 mt-1 pl-4"><span className="font-semibold">Fix: </span>{r.how_to_fix}</div>
        : <div className="text-[12px] text-ink-500 mt-1 pl-4">{r.status === "pass" ? "Fix: no action needed — check passing." : "Fix: informational — no action required."}</div>}

      {(r.category === "F-links" && r.key === "f-backlinks") && (
        <div className="text-[11px] mt-1.5 text-ink-500 pl-4">Known free-tier limitation: Search Console links report is the ceiling. No full backlink index / DA is shown.</div>
      )}
      {r.category === "K-aeo" && (
        <div className="text-[11px] mt-1.5 text-ink-500 pl-4">AI mention sample, not a ranking metric — varies run to run.</div>
      )}
    </div>
  );
}