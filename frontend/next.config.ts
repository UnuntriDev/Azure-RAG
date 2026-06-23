import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emit a fully static build to `out/` for Azure Static Web Apps. `next dev` is unaffected.
  output: "export",
  images: { unoptimized: true },
};

export default nextConfig;
