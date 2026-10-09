"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { NAV } from "@/lib/types";

export function Sidebar() {
  const path = usePathname();
  return (
    <aside className="w-52 shrink-0 bg-ink-900 text-ink-100 min-h-screen p-4">
      <div className="font-bold text-white mb-1">Website Intelligence</div>
      <div className="text-[11px] text-ink-300 mb-4">INTERNAL USE ONLY · no external redirects</div>
      <nav className="space-y-1">
        {NAV.map((n) => (
          <Link key={n.href} href={n.href}
            className={`block px-3 py-2 rounded text-[13px] ${path === n.href ? "bg-white/10 text-white" : "text-ink-300 hover:bg-white/5"}`}>
            {n.label}
          </Link>
        ))}
      </nav>
      <div className="mt-6 text-[11px] text-ink-300 leading-relaxed">
        Every value measured.<br />Failed checks show<br /><span className="text-white">UNAVAILABLE</span> (gray) — never guessed.
      </div>
    </aside>
  );
}
