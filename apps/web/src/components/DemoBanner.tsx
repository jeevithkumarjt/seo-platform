"use client";
import { DEMO } from "@/lib/demo";

export function DemoBanner() {
  if (!DEMO) return null;
  return (
    <div className="bg-amber-50 border-b border-amber-200 px-4 py-2 text-[12px] text-amber-800">
      <b>Static demo</b> — GitHub Pages cannot host the backend. Every figure below is{" "}
      <b>real measured data</b> captured from our API (audit of tryvium.ai · Lighthouse · 121-device responsive matrix),
      served as a fixed snapshot. Run the platform locally to audit live sites.
    </div>
  );
}
