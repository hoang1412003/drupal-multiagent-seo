import type { Plugin } from "vite";
// defineConfig lay tu vitest/config chu khong phai vite: ban cua vite khong
// biet khoa `test`, nen `tsc --noEmit` se bao loi kieu o chinh file nay.
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

/**
 * Chuyen huong /console -> /console/ khi dev.
 *
 * FastAPI o production tu tra 307 cho duong dan thieu dau / cuoi, nhung Vite
 * thi in ra mot trang loi chu. Khong co plugin nay thi go localhost:5173/console
 * se thay trang trang - dev va production hanh xu khac nhau o dung cho nguoi
 * ta hay go nhat.
 */
function redirectBaseWithoutSlash(): Plugin {
  return {
    name: "console-redirect-base-without-slash",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        if (req.url === "/console") {
          res.writeHead(307, { Location: "/console/" });
          res.end();
          return;
        }
        next();
      });
    },
  };
}

export default defineConfig({
  plugins: [react(), tailwindcss(), redirectBaseWithoutSlash()],
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
  test: {
    // DOM gia trong Node: khong can trinh duyet, khong can server nao chay.
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    // Chi lay file .test.tsx trong src; khong quet dist/ hay node_modules.
    include: ["src/**/*.test.{ts,tsx}"],
  },
});
