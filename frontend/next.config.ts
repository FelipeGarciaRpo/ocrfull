/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    ignoreDuringBuilds: true,  // ignora errores de ESLint en build
  },
  typescript: {
    ignoreBuildErrors: true,   // ignora errores de TypeScript en build
  },
}

module.exports = nextConfig
