import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// 개발할 때는 Vite(5173)가 /api, /camera를 파이썬 서버(5000)로 넘겨준다.
// 배포할 때는 npm run build 결과(web/dist)를 Flask가 직접 서빙한다.
const BACKEND = process.env.BACKEND || "http://localhost:5000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    proxy: {
      "/api": BACKEND,
      "/camera": BACKEND,
      "/growth_photos": BACKEND,
    },
  },
  build: {
    outDir: "dist",
    assetsInlineLimit: 0,
  },
});
