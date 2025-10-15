const { createProxyMiddleware } = require('http-proxy-middleware')

module.exports = function(app) {
  // Proxy API requests to the backend
  app.use(
    '/api',
    createProxyMiddleware({
      target: 'http://localhost:8000',
      changeOrigin: true,
    })
  )
  
  // Proxy Whisper API requests
  app.use(
    '/whisper',
    createProxyMiddleware({
      target: 'http://192.168.10.222:8001',
      changeOrigin: true,
      pathRewrite: {
        '^/whisper': '', // حذف /whisper از path
      },
      timeout: 300000,      // 5 دقیقه timeout برای request
      proxyTimeout: 300000, // 5 دقیقه timeout برای response
      onProxyReq: (proxyReq, req, res) => {
        console.log('🔄 Proxying to Whisper:', req.method, req.url)
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('✅ Response from Whisper:', proxyRes.statusCode)
      },
      onError: (err, req, res) => {
        console.error('❌ Proxy Error:', err.message)
      }
    })
  )
}