/** @type {import('next').NextConfig} */
const nextConfig = {
  // Self-contained server for the production Docker image (frontend/Dockerfile).
  output: "standalone",
};

export default nextConfig;
