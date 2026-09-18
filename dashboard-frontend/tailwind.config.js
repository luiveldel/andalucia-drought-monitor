/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        canvas: { DEFAULT: "#F5F2EC", dark: "#141210" },
        surface: { DEFAULT: "#F9F7F2", dark: "#1A1815" },
        ink: { DEFAULT: "#1E1B14", dark: "#D8D4CC" },
        muted: { DEFAULT: "#6B6458", dark: "#7A7570" },
        terracotta: { DEFAULT: "#B84A1B", dark: "#E07040" },
        water: { DEFAULT: "#1A6FA3", dark: "#87CEEB" },
        sev: {
          normal: "#3D7A3A",
          alert: "#C98C00",
          emergency: "#D96520",
          critical: "#B83228",
        },
      },
      fontFamily: {
        display: ["Space Grotesk", "system-ui", "sans-serif"],
        sans: ["Satoshi", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};
