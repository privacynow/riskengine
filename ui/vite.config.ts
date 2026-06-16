import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  base: "/admin/",
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    proxy: {
      "/ui": { target: "http://localhost:8000", changeOrigin: true },
      "/decisions": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  preview: {
    proxy: {
      "/ui": { target: "http://localhost:8000", changeOrigin: true },
      "/decisions": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    sourcemap: false,
  },
});
