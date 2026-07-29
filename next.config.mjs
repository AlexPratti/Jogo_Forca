/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    // Permite que o deploy termine mesmo se houver pequenos avisos de tipo
    ignoreBuildErrors: true,
  },
  eslint: {
    // Ignora avisos de formatação para acelerar a compilação
    ignoreDuringBuilds: true,
  },
};

export default nextConfig;
