/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./src/**/*.{ts,tsx}"],
  theme: { extend: {
    colors: {
      ink: { 900: "#0f172a", 700: "#334155", 500: "#64748b", 300: "#cbd5e1", 100: "#f1f5f9", 50: "#f8fafc" },
      crit: "#b91c1c", warn: "#b45309", ok: "#15803d", mute: "#64748b"
    }
  } },
  plugins: []
};
