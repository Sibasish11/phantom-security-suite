import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],

  server: {
    host: "127.0.0.1",
    port: 5173,

    proxy: {
      "/auth": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/security": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/incidents": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/routing": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/domains": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/agents": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },

      "/protections": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },

  build: {
    target: "es2022",
  },
});