/** @type {import('next').NextConfig} */
const nextConfig = {
    experimental: {
      appDir: true
    },
    images: {
      domains: ['github.com', 'lh3.googleusercontent.com']
    },
    typescript:{
        ignoreBuildErrors: true
    },
    eslint:{
        ignoreBuildErrors: true
    }
  }
  
  module.exports = nextConfig