/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0F1720",
        panel: "#16212C",
        panel2: "#1C2A37",
        line: "#2A3B49",
        shield: "#3B82F6",
        verify: "#2DD4BF",
        warn: "#F5A524",
        danger: "#EF4444",
        mist: "#B7C4CF",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(59,130,246,0.25), 0 8px 30px -10px rgba(59,130,246,0.35)",
      },
    },
  },
  plugins: [],
};
