import type { NextConfig } from "next";

// In Docker/production Caddy routes /api to the FastAPI service. For local
// `next dev` against a separately running API, set API_PROXY_URL
// (e.g. http://localhost:8000) to proxy /api/* there.
const apiProxy = process.env.API_PROXY_URL;

const nextConfig: NextConfig = {
  output: "standalone",
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return apiProxy ? [{ source: "/api/:path*", destination: `${apiProxy}/:path*` }] : [];
  },
};

export default nextConfig;
