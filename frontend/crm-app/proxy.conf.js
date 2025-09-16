// frontend/crm-app/proxy.conf.js
const PROXY_CONFIG = {
  '/api/**': {
    target: 'http://backend:8000',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    onProxyReq: function(proxyReq, req, res) {
      if (req.headers.cookie) {
        proxyReq.setHeader('Cookie', req.headers.cookie);
      }
      console.log('🔄 Docker Proxying:', req.method, req.url);
    },
    onProxyRes: function(proxyRes, req, res) {
      proxyRes.headers['Access-Control-Allow-Origin'] = 'http://localhost:4200';
      proxyRes.headers['Access-Control-Allow-Credentials'] = 'true';
      console.log('✅ Docker Response:', proxyRes.statusCode, req.url);
    },
    onError: function(err, req, res) {
      console.error('💥 Docker Proxy error:', err.message);
      console.error('Make sure backend service is running');
    }
  },
  '/static/**': {
    target: 'http://backend:8000',
    secure: false,
    changeOrigin: true
  },
  '/media/**': {
    target: 'http://backend:8000',
    secure: false,
    changeOrigin: true
  }
};

module.exports = PROXY_CONFIG;
