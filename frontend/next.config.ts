import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow specific development origins to request Next.js dev assets.
  // Add the IP (and port if needed) that showed in the warning.
  allowedDevOrigins: ["http://26.83.101.154"],
};

export default nextConfig;
