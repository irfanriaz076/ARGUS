import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_HOST = process.env.API_HOST ?? 'localhost'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    // Polling is required for HMR to see file changes through the Windows ->
    // Docker Desktop bind-mount boundary, where native fs events don't propagate.
    watch: { usePolling: true, interval: 300 },
    proxy: {
      '/api': `http://${API_HOST}:8000`,
      '/ws': { target: `ws://${API_HOST}:8000`, ws: true },
    },
  },
})
