import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Use 8001 locally so a stuck / ghost listener on 8000 does not block dev (see README).
      '/api': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/admin': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/admin-theme': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/saul-admin': { target: 'http://127.0.0.1:8001', changeOrigin: true },
      '/site-media': { target: 'http://127.0.0.1:8001', changeOrigin: true },
    },
  },
})
