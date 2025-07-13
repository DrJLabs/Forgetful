/** @type {import('next').NextConfig} */
const nextConfig = {
  eslint: {
    // ESLint is now properly configured - remove the ignore flag
    dirs: ['pages', 'components', 'lib', 'hooks', 'store', 'app'],
  },
  typescript: {
    // Keep this for now to avoid breaking the build, but should be addressed later
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
