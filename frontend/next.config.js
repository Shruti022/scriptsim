/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    return [
      { source: '/scan', destination: `${backendUrl}/scan` },
      { source: '/session-status', destination: `${backendUrl}/session-status` },
      { source: '/health', destination: `${backendUrl}/health` },
    ];
  },
};

module.exports = nextConfig;
