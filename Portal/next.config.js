/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  async rewrites() {
    return {
      beforeFiles: [],
      afterFiles: [
        {
          source: '/api/agent-runner/:path*',
          destination: '/api/agent-runner/:path*',
        },
        {
          source: '/api/codex-runner/:path*',
          destination: '/api/codex-runner/:path*',
        },
        {
          source: '/api/prompt-manager/:path*',
          destination: '/api/prompt-manager/:path*',
        },
      ],
      fallback: [
        {
          source: '/api/:path*',
          destination: process.env.NEXT_PUBLIC_API_URL 
            ? `${process.env.NEXT_PUBLIC_API_URL}/api/:path*`
            : 'http://localhost:8081/api/:path*',
        },
      ],
    };
  },
};

module.exports = nextConfig;
