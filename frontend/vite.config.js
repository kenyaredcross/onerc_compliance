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
    rollupOptions: {
      output: {
        entryFileNames: 'compliance.js',
        chunkFileNames: 'compliance-[name].js',
        assetFileNames: (info) => {
          if (info.name?.endsWith('.css')) return 'compliance.css'
          return '[name][extname]'
        },
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
