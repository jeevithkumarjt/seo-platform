export type CheckResult = {
  key: string; label: string; category: string;
  status: "pass" | "warning" | "fail" | "unavailable" | "info";
  severity: string; found: string; source: string;
  evidence: any; // when type==="image" → { type:"image", dataUrl:string, timing?:number }
  why_matters: string; how_to_fix: string;
  checked_at: string; confidence?: string;
};

export const CATEGORIES = [
  { id: "A-onpage", code: "A", name: "On-Page" },
  { id: "B-technical", code: "B", name: "Technical" },
  { id: "C-structured", code: "C", name: "Structured Data" },
  { id: "D-performance", code: "D", name: "Performance (lab+field)" },
  { id: "E-a11y", code: "E", name: "Accessibility" },
  { id: "F-links", code: "F", name: "Links" },
  { id: "G-content", code: "G", name: "Content" },
  { id: "H-xbrowser", code: "H", name: "Cross-Browser & Device" },
  { id: "I-jshealth", code: "I", name: "JS/CSS Health" },
  { id: "J-techstack", code: "J", name: "Tech Stack / Tags" },
  { id: "K-aeo", code: "K", name: "AEO / GEO sample" },
  { id: "L-rank", code: "L", name: "Rank Tracking" },
  { id: "M-gsc", code: "M", name: "Search Console Health ★" },
  { id: "N-architecture", code: "N", name: "Site Architecture" },
  { id: "O-security", code: "O", name: "Security Headers" },
  { id: "Q-pwa", code: "Q", name: "PWA" },
  { id: "R-intl", code: "R", name: "International" },
  { id: "S-frontend", code: "S", name: "Front-End Depth" },
  { id: "T-local", code: "T", name: "Local SEO (conditional)" },
];

export const NAV = [
  { href: "/", label: "Overview" },
  { href: "/audit", label: "Audit" },
  { href: "/performance", label: "Performance" },
  { href: "/responsive", label: "Responsive" },
  { href: "/monitoring", label: "Monitoring" },
  { href: "/integrations", label: "Integrations" },
  { href: "/alerts", label: "Alerts" },
  { href: "/tech-stack", label: "Tech Stack" },
];
