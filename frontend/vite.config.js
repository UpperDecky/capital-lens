import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/feed':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/entities':{ target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/themes':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/search':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/auth':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health':  { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/admin':   { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/flow':    { target: 'http://127.0.0.1:8000', changeOrigin: true },
    }
  }
})
