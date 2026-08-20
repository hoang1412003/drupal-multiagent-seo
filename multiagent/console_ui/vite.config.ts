import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // BAT BUOC. Thieu dong nay thi duong dan asset trong dist/index.html tro ve
  // "/" va trang trang khi FastAPI serve tai /console.
  base: "/console/",
  server: {
    proxy: {
      // Giu same-origin khi dev: nho vay cookie phien HttpOnly hoat dong y het
      // production, khong can CORS va khong phai doi SameSite.
      "/api": { target: "http://localhost:8900", changeOrigin: false },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
