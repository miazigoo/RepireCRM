const PROXY_CONFIG = {
  '/api/**': {
    target: 'http://127.0.0.1:8030',
    secure: false,
    changeOrigin: true,
    logLevel: 'debug',
    onProxyReq: function(proxyReq, req, res) {
      if (req.headers.cookie) {
        proxyReq.setHeader('Cookie', req.headers.cookie);
      }
      console.log('🔄 LOCAL Proxying:', req.method, req.url);
    },
    onProxyRes: function(proxyRes, req, res) {
      proxyRes.headers['Access-Control-Allow-Origin'] = 'http://localhost:4200';
      proxyRes.headers['Access-Control-Allow-Credentials'] = 'true';
      console.log('✅ LOCAL Response:', proxyRes.statusCode, req.url);
    },
    onError: function(err, req, res) {
      console.error('💥 LOCAL Proxy error:', err.message);
      console.error('Make sure Django is running: python manage.py runserver 127.0.0.1:8030');
    }
  },
  '/static/**': {
    target: 'http://127.0.0.1:8030',
    secure: false,
    changeOrigin: true
  },
  '/media/**': {
    target: 'http://127.0.0.1:8030',
    secure: false,
    changeOrigin: true
  }
};

module.exports = PROXY_CONFIG;
