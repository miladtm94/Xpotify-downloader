import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#17140f",
        paper: "#f4ecdc",
        clay: "#b85f3f",
        moss: "#536b45",
        brass: "#c99235",
        tide: "#1f6f78",
      },
      boxShadow: {
        panel: "0 24px 80px rgba(42, 30, 18, 0.18)",
      },
    },
  },
  plugins: [],
} satisfies Config;

