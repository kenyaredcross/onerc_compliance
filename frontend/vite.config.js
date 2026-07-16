import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const SITE = process.env.FRAPPE_SITE || 'onerc.localhost'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': path.resolve(__dirname, 'src') },
  },
  base: '/assets/onerc_compliance/compliance/',
  build: {
    outDir: '../onerc_compliance/public/compliance',
    emptyOutDir: true,
    cssCodeSplit: false,
    // Hashed filenames bust browser caches on every deploy; the www pages
    // resolve the real names at request time from this manifest.
    manifest: true,
    rollupOptions: {
      output: {
        entryFileNames: 'compliance-[hash].js',
        chunkFileNames: 'compliance-[name]-[hash].js',
        assetFileNames: 'compliance-[hash][extname]',
      },
    },
  },
  server: {
    port: 8081,
    proxy: {
      '/api': { target: `http://${SITE}:8000`, changeOrigin: true },
      '/assets': { target: `http://${SITE}:8000`, changeOrigin: true },
      '/private': { target: `http://${SITE}:8000`, changeOrigin: true },
    },
  },
})
