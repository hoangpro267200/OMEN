/// <reference types="vitest" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { visualizer } from 'rollup-plugin-visualizer'

// https://vite.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [
    react(),
    tailwindcss(),
    mode === 'analyze' || process.env.ANALYZE === 'true'
      ? visualizer({ open: true, gzipSize: true, brotliSize: true, filename: 'dist/stats.html' })
      : undefined,
  ].filter(Boolean),
  server: { port: 5174 },
  optimizeDeps: {
    include: ['react', 'react-dom', 'react-router-dom', '@tanstack/react-query', 'react-simple-maps'],
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          if (id.includes('node_modules')) {
            if (id.includes('react-dom') || id.includes('react/') || id.includes('react-router')) return 'react-vendor'
            if (id.includes('@tanstack/react-query')) return 'query-vendor'
            if (id.includes('framer-motion') || id.includes('recharts')) return 'ui-vendor'
          }
          return undefined
        },
      },
    },
    minify: 'esbuild',
    sourcemap: process.env.NODE_ENV === 'development',
    chunkSizeWarningLimit: 500,
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
    include: ['src/**/*.{test,spec}.{ts,tsx}'],
  },
}))
