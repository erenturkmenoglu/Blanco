/** @type {import('next').NextConfig} */
// output: 'standalone' yalnızca Docker imajı için (DOCKER_BUILD=1); Vercel kendi çıktısını yönetir.
const nextConfig = { reactStrictMode: true, ...(process.env.DOCKER_BUILD ? { output: "standalone" } : {}) };
module.exports = nextConfig;
