import path from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

const proxyTarget = process.env.VITE_PROXY_TARGET ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "src") },
  },
  server: {
    host: true,
    port: 5173,
    // VPS / Caddy: allow public Host header (otherwise Vite returns 403)
    allowedHosts: [
      "andalucia.luisandresvelazquez.com",
      ".luisandresvelazquez.com",
      "localhost",
      "agro-dashboard-frontend",
    ],
    proxy: {
      "/api": { target: proxyTarget, changeOrigin: true },
      "/health": { target: proxyTarget, changeOrigin: true },
    },
  },
});
