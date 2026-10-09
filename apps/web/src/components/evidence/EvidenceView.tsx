"use client";
import { useMemo, useState } from "react";

/* Smart evidence renderer — turns raw check data into readable visuals.
   Handles: image → screenshot; array of strings → chip grid; array of objects → table;
   object of numbers → horizontal bar chart; object of scalars → key/value table; string → value. */

function fmt(v: any): string {
  if (v === null || v === undefined) return "—";
  if (typeof v === "boolean") return v ? "Yes" : "No";
  if (typeof v === "number") return isNaN(v) ? "—" : String(v);
  return String(v);
}

function isNumericObject(x: any): boolean {
  if (typeof x !== "object" || x === null || Array.isArray(x)) return false;
  const v = Object.values(x);
  return v.length > 0 && v.length <= 12 && v.every((n) => typeof n === "number");
}

function HumanLabel(k: string) {
  let s = k.replace(/_/g, " ").replace(/([a-z])([A-Z])/g, "$1 $2");
  s = s
    .split(" ")
    .map((w) => (w.length <= 3 ? w.toUpperCase() : w.charAt(0).toUpperCase() + w.slice(1)))
    .join(" ");
  return s;
}

/* Bar chart for numeric objects (heading counts, words, ratios, bytes, etc.) */
function NumericBars({ obj }: { obj: Record<string, number> }) {
  const max = Math.max(...Object.values(obj), 1);
  const shortLabel = (k: string) => (k.length <= 12 ? k : k.slice(0, 4) + "…" + k.slice(-5));
  return (
    <div className="space-y-1.5">
      {Object.entries(obj).map(([k, v]) => {
        const pct = Math.max(v > 0 ? 4 : 0, Math.round((v / max) * 100));
        return (
          <div key={k} className="flex items-center gap-2">
            <span className="w-24 shrink-0 text-[11px] text-ink-500 capitalize truncate">{shortLabel(k)}</span>
            <div className="h-3 flex-1 rounded bg-ink-100 overflow-hidden">
              <div className="h-full rounded bg-indigo-500/80" style={{ width: `${pct}%` }} />
            </div>
            <span className="w-9 shrink-0 text-right font-mono text-[11px] font-semibold text-ink-900">{v}</span>
          </div>
        );
      })}
    </div>
  );
}

/* Key/value table for mixed objects (title length, word count, ratio, etc.) */
function KvTable({ obj, max = 8 }: { obj: Record<string, any>; max?: number }) {
  const [open, setOpen] = useState(false);
  const entries = Object.entries(obj).slice(0, open ? undefined : max);
  const hasMore = Object.keys(obj).length > max;
  return (
    <div>
      <div className="grid grid-cols-[minmax(0,auto)_1fr] gap-x-4 gap-y-1 text-[12px]">
        {entries.map(([k, v]) => (
          <div key={k} className="contents">
            <span className="text-ink-500 truncate font-medium">{HumanLabel(k)}</span>
            <span className="text-ink-900">{fmt(v)}</span>
          </div>
        ))}
      </div>
      {hasMore && (
        <button onClick={() => setOpen((o) => !o)} className="mt-1 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800">
          {open ? "Show less" : `Show all ${Object.keys(obj).length}`}
        </button>
      )}
    </div>
  );
}

/* Object-of-objects (nested) or array-of-objects → real table */
function ObjectTable({ rows }: { rows: any[] }) {
  const head = useMemo(() => {
    const seen: string[] = [];
    for (const r of rows) for (const k of Object.keys(r)) if (!seen.includes(k)) seen.push(k);
    return seen.slice(0, 6);
  }, [rows]);
  return (
    <div className="overflow-auto max-h-56 rounded-md border text-[11px]">
      <table className="w-full border-collapse">
        <thead>
          <tr className="bg-ink-50 text-left">
            {head.map((h) => (
              <th key={h} className="px-2 py-1 font-semibold text-ink-500 border-b truncate max-w-32">{HumanLabel(h)}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(0, 12).map((r, i) => (
            <tr key={i} className="border-b last:border-0 odd:bg-white">
              {head.map((h) => (
                <td key={h} className="px-2 py-1 text-ink-900 truncate max-w-32" title={fmt(r[h])}>{fmt(r[h])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/* Chip grid for arrays of short strings (missing alt indices, URLs, tag names) */
function ChipGrid({ arr }: { arr: any[] }) {
  const [open, setOpen] = useState(false);
  const shown = open ? arr : arr.slice(0, 16);
  const looksUrl = (s: string) => /^https?:\/\//i.test(s);
  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {shown.map((v, i) => {
          const s = fmt(v);
          return looksUrl(s) ? (
            <a key={i} href={s} target="_blank" rel="noreferrer" className="badge bg-indigo-50 text-indigo-700 border border-indigo-200 hover:bg-indigo-100 max-w-52 truncate">
              {s.replace(/^https?:\/\//, "").slice(0, 48)}
            </a>
          ) : (
            <span key={i} className="badge bg-ink-50 text-ink-700 border border-ink-200/70 mono">{s.slice(0, 40)}</span>
          );
        })}
      </div>
      {arr.length > 16 && (
        <button onClick={() => setOpen((o) => !o)} className="mt-1.5 text-[11px] font-semibold text-indigo-600 hover:text-indigo-800">
          {open ? "Show less" : `Show all ${arr.length}`}
        </button>
      )}
    </div>
  );
}

/* Big value callout for simple strings/booleans/numbers */
function BigValue({ value }: { value: any }) {
  const s = fmt(value);
  if (typeof value === "boolean")
    return (
      <span className={`inline-flex items-center gap-1.5 text-[13px] font-semibold ${value ? "text-ok" : "text-crit"}`}>
        <i className={`h-2 w-2 rounded-full ${value ? "bg-ok" : "bg-crit"} inline-block`} />
        {value ? "Detected" : "Not detected"}
      </span>
    );
  if (!isNaN(Number(s)) && s.trim() !== "") return <span className="text-[18px] font-bold text-ink-900 mono">{s}</span>;
  return <span className="text-[13px] text-ink-800 break-words">{s.slice(0, 300)}</span>;
}

function isObjectArray(x: any): boolean {
  return Array.isArray(x) && x.some((v) => typeof v === "object" && v !== null && !Array.isArray(v));
}
function isPrimitiveArray(x: any): boolean {
  return Array.isArray(x) && x.every((v) => ["string", "number", "boolean"].includes(typeof v));
}

export function EvidenceView({ evidence }: { evidence: any }) {
  if (evidence === null || evidence === undefined) return null;

  // image evidence (screenshots from PSI)
  if (typeof evidence === "object" && evidence.type === "image" && evidence.dataUrl) {
    return (
      <img
        src={evidence.dataUrl}
        alt="evidence screenshot"
        className="rounded-md border max-w-full max-h-72 object-contain bg-ink-50"
        loading="lazy"
      />
    );
  }

  // array of objects → table
  if (isObjectArray(evidence)) return <ObjectTable rows={evidence} />;
  // primitive arrays → chips
  if (isPrimitiveArray(evidence)) return evidence.length ? <ChipGrid arr={evidence} /> : <span className="text-[12px] text-ink-500">(empty)</span>;
  // numeric records → bars
  if (isNumericObject(evidence)) return <NumericBars obj={evidence} />;
  // other objects → key/value table (avoid leaking giant nested blobs: stringify nontrivial vals)
  if (typeof evidence === "object") {
    const flat: Record<string, any> = {};
    for (const [k, v] of Object.entries(evidence)) {
      flat[k] = typeof v === "object" && v !== null ? JSON.stringify(v).slice(0, 120) : v;
    }
    return <KvTable obj={flat} />;
  }
  // scalars
  return <BigValue value={evidence} />;
}