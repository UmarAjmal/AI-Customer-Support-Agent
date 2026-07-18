import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      { protocol: "https", hostname: "images.unsplash.com" },
    ],
  },
  // Proxy API through Next to avoid browser cold CORS + reuse connections
  async rewrites() {
    const api = process.env.NEXT_PUBLIC_API_URL || "https://ai-customer-support-agent-dchb.onrender.com/api";
    const target = api.replace(/\/api\/?$/, "");
    return [
      {
        source: "/backend-api/:path*",
        destination: `${target}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
