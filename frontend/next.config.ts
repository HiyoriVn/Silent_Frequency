import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  turbopack: {
    root: path.join(__dirname),
  },
  allowedDevOrigins: [
    "localhost",
    "127.0.0.1",
    "26.83.101.154",
    "26.83.101.154:3000",
  ],
};

export default nextConfig;
