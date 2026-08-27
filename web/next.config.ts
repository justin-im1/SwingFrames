import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8000/api/:path*",
      },
    ];
  },
  // The /api/:path* rewrite proxies uploads through Next's own server so the
  // browser can call the API same-origin. Next caps proxied request bodies
  // at 10MB by default, silently truncating anything bigger and resetting
  // the connection — well under a real phone video, and well under the
  // API's own 500MB cap (app/config.py: max_upload_bytes). Match that here.
  experimental: {
    middlewareClientMaxBodySize: "500mb",
  },
};

export default nextConfig;
