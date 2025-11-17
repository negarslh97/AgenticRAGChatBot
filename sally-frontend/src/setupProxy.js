const { createProxyMiddleware } = require('http-proxy-middleware')

// می‌توانید این متغیر را تغییر دهید تا بین حالت‌های مختلف سوئیچ کنید
const API_TARGET = process.env.API_TARGET || 'localhost:8000'

module.exports = function(app) {
  // Proxy API requests to the backend
  app.use(
    '/api',
    createProxyMiddleware({
      target: `http://${API_TARGET}`,
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
        '^/whisper': '',
      },
      timeout: 300000,
      proxyTimeout: 300000,
      onProxyReq: (proxyReq, req, res) => {
        console.log('🔄 Proxying to Whisper:', req.method, req.url)
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('✅ Response from Whisper:', proxyRes.statusCode)
      },
      onError: (err, req, res) => {
        console.error('❌ Whisper Proxy Error:', err.message)
      }
    })
  )

  // Proxy Vosk API requests
  app.use(
    '/vosk',
    createProxyMiddleware({
      target: 'http://192.168.10.222:8002',
      changeOrigin: true,
      pathRewrite: {
        '^/vosk': '',
      },
      timeout: 300000,
      proxyTimeout: 300000,
      onProxyReq: (proxyReq, req, res) => {
        console.log('🔄 Proxying to Vosk:', req.method, req.url)
      },
      onProxyRes: (proxyRes, req, res) => {
        console.log('✅ Response from Vosk:', proxyRes.statusCode)
      },
      onError: (err, req, res) => {
        console.error('❌ Vosk Proxy Error:', err.message)
      }
    })
  )
}