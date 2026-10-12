/** @type {import('next').NextConfig} */
// DEMO_EXPORT=1 builds a static site for GitHub Pages (https://jeevithkumarjt.github.io/seo/dashboard/)
// — the container build (docker) keeps output: "standalone".
const isDemo = process.env.DEMO_EXPORT === "1";

const nextConfig = {
  reactStrictMode: true,
  // OneDrive rejects Next's symlink readlink during cleanup — allow the build
  // dir to be relocated outside the synced folder for the demo export.
  ...(process.env.NEXT_DIST_DIR ? { distDir: process.env.NEXT_DIST_DIR } : {}),
  ...(isDemo
    ? {
        output: "export",
        basePath: "/seo/dashboard",
        trailingSlash: true,
        images: { unoptimized: true },
      }
    : { output: "standalone" }),
};

module.exports = nextConfig;
