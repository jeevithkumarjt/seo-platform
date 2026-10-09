"use client";
/** Trend with explicit gaps: null/unavailable points break the line (no interpolation). Rendered as SVG. */
export function TrendChart({ points, label }: { points: { at: string; value: number | null; gap?: boolean }[]; label: string }) {
  const W = 520, H = 120, P = 8;
  const vals = points.map((p) => p.value).filter((v): v is number => v !== null);
  const max = Math.max(1, ...vals);
  const step = points.length > 1 ? (W - 2 * P) / (points.length - 1) : 0;
  const xy = points.map((p, i) => ({ x: P + i * step, y: p.value === null ? null : H - P - (p.value / max) * (H - 2 * P), gap: p.gap || p.value === null }));
  let d = ""; let started = false;
  xy.forEach((pt) => {
    if (pt.y === null || pt.gap) { started = false; return; }
    d += `${started ? "L" : "M"}${pt.x.toFixed(1)},${pt.y.toFixed(1)} `;
    started = true;
  });
  return (
    <div className="card p-3">
      <div className="text-[12px] font-semibold mb-1">{label} <span className="font-normal text-ink-500">(gaps = missing/failed runs, never interpolated)</span></div>
      <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="bg-ink-50 rounded border">
        <path d={d} fill="none" stroke="#334155" strokeWidth="2" />
        {xy.map((pt, i) => pt.y === null || pt.gap
          ? <rect key={i} x={pt.x - 3} y={P} width={6} height={H - 2 * P} fill="#cbd5e1" opacity={0.7}><title>missing data — gap</title></rect>
          : <circle key={i} cx={pt.x} cy={pt.y} r={3} fill="#0f172a"><title>{points[i].at}: {points[i].value}</title></circle>)}
      </svg>
    </div>
  );
}
