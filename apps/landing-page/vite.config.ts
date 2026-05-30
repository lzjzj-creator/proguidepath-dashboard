import { defineConfig } from "vite";

export default defineConfig({
  root: ".",
  server: {
    port: 3456,
    open: true,
  },
  build: {
    outDir: "dist",
  },
});
