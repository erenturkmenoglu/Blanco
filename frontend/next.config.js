/** @type {import('next').NextConfig} */
// Üç hedef: Vercel (varsayılan, sunucu), Docker imajı (DOCKER_BUILD=1 → standalone), GitHub Pages (STATIC_EXPORT=1 → out/ + basePath).
const basePath = process.env.NEXT_PUBLIC_BASE_PATH || "";
const nextConfig = {
  reactStrictMode: true,
  ...(process.env.DOCKER_BUILD ? { output: "standalone" } : {}),
  ...(process.env.STATIC_EXPORT ? { output: "export", trailingSlash: true, basePath, images: { unoptimized: true } } : {}),
};
module.exports = nextConfig;
