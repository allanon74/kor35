import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

/**
 * Build separata per la console pilota servita da Nginx su /pilot/.
 *
 * - `base: '/pilot/'` => tutti gli asset usano percorsi relativi a /pilot/.
 * - API sempre relative (/api/...) per compatibilita' Edge/Master.
 * - In dev (`npm run dev`) viene proxiato /api a Django locale.
 */
export default defineConfig(({ command }) => ({
  base: '/pilot/',
  plugins: [react()],
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
  server: {
    host: true,
    port: 5174,
    proxy: command === 'serve' ? {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    } : undefined,
  },
}));
