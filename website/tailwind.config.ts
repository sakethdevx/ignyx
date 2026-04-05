import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "1.5rem",
      screens: {
        "2xl": "1280px",
      },
    },
    extend: {
      fontFamily: {
        body: ["Geist", "Inter", "Segoe UI", "sans-serif"],
        display: ["Space Grotesk", "Geist", "Inter", "sans-serif"],
      },
      colors: {
        background: "#090d16",
        foreground: "#f5f7fb",
        muted: "#9ca8c4",
        panel: "#101626",
        border: "rgba(126, 146, 189, 0.18)",
        electric: {
          400: "#61a8ff",
          500: "#4387ff",
          600: "#3559ff",
        },
        violet: {
          400: "#8f7dff",
          500: "#725bff",
        },
      },
      backgroundImage: {
        "hero-grid":
          "linear-gradient(to right, rgba(255,255,255,0.04) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.04) 1px, transparent 1px)",
        "radial-glow":
          "radial-gradient(circle at top, rgba(97,168,255,0.22), transparent 45%), radial-gradient(circle at 80% 20%, rgba(143,125,255,0.18), transparent 35%)",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(97,168,255,0.15), 0 18px 70px rgba(40,90,255,0.18)",
        card: "0 24px 80px rgba(7, 13, 28, 0.45)",
      },
      borderRadius: {
        "4xl": "2rem",
      },
      animation: {
        float: "float 6s ease-in-out infinite",
        pulseline: "pulseline 8s linear infinite",
      },
      keyframes: {
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
        pulseline: {
          "0%": { transform: "translateX(-10%)" },
          "100%": { transform: "translateX(10%)" },
        },
      },
    },
  },
  plugins: [],
};

export default config;
