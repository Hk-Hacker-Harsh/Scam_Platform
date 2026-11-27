import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath } from "node:url";

// `npm run build`       -> dist/ (served by Flask), real HTTP transport.
// `npm run build:proto` -> dist-proto/ (offline prototype): sample-data transport, one JS file, packed into a single
//                          html file by tools/make_prototype.py.
// `npm run dev`         -> http://localhost:5173 with hot reload; API calls are proxied to Flask on :5000.
export default defineConfig(({ mode }) => {
  const proto = mode === "proto";
  return {
    plugins: [vue()],
    base: proto ? "./" : "/",
    resolve: {
      alias: { "@transport": fileURLToPath(new URL(proto ? "./src/proto/transport.js" : "./src/transport-http.js", import.meta.url)) },
    },
    build: {
      outDir: proto ? "dist-proto" : "dist",
      emptyOutDir: true,
      assetsInlineLimit: 0,
      chunkSizeWarningLimit: proto ? 4000 : 900,
      rollupOptions: proto ? { output: { inlineDynamicImports: true } } : {},
    },
    server: {
      port: 5173,
      proxy: { "/api": "http://127.0.0.1:5000", "/result": "http://127.0.0.1:5000", "/police": "http://127.0.0.1:5000",
               "/static": "http://127.0.0.1:5000" },
    },
  };
});
