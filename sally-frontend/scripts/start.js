const { createProxyMiddleware } = require('http-proxy-middleware')
const express = require('express')
const { createServer } = require('http')
const { parse } = require('url')
const next = require('next')

// Custom development server with client-side routing support
const app = express()
const server = createServer(app)

// Proxy API requests to the backend
app.use(
  '/api',
  createProxyMiddleware({
    target: 'http://localhost:8000',
    changeOrigin: true,
  })
)

// Handle client-side routing - serve index.html for all non-API routes
app.get('*', (req, res, next) => {
  // Skip API routes
  if (req.path.startsWith('/api')) {
    return next()
  }

  // Skip static files
  if (req.path.match(/\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|map)$/)) {
    return next()
  }

  // For all other routes (including /super-admin, /dashboard, etc.), serve the index.html file
  // This allows React Router to handle the routing on the client side
  const path = require('path')
  res.sendFile(path.join(__dirname, '../public/index.html'))
})

// Start the server
const PORT = process.env.PORT || 3000
server.listen(PORT, (err) => {
  if (err) throw err
  console.log(`> Ready on http://localhost:${PORT}`)
  console.log('> Client-side routing enabled')
})