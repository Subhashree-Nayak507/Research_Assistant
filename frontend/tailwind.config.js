/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#12151B",
        slate: {
          950: "#0B0D12",
          900: "#12151B",
          850: "#191D26",
          800: "#1F2430",
        },
        parchment: "#F6F3EC",
        signal: "#C9A15A",   // muted brass/amber — the "verification" accent
        moss: "#5C7A5E",     // grounded/verified green, used sparingly
        rust: "#B5533C",     // error / hallucination-flag red
      },
      fontFamily: {
        display: ["'Fraunces'", "serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'IBM Plex Mono'", "monospace"],
      },
    },
  },
  plugins: [],
}
