import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { VitePWA } from 'vite-plugin-pwa'
import packageJson from './package.json'

export default defineConfig(({ command, mode }) => {
  const plugins = [
    
    react(),
    // Configurazione PWA
    VitePWA({
      // --- MODIFICHE PER WEB PUSH (Livello 2) ---
      strategies: 'injectManifest', // Usa il nostro service worker custom
      srcDir: 'src',                // Cartella dove si trova il file sorgente
      filename: 'sw.js',            // Nome del file sorgente (creato nel passo precedente)
      // Disabilita l'auto-registrazione del Service Worker dal bundle client.
      // Evita cache runtime incoerente finché non chiudiamo il bug "Cannot access ... before initialization".
      injectRegister: false,
      // Workbox rifiuta di precachare file > 2 MiB (default). Il bundle principale può superarlo.
      // https://vite-pwa-org.netlify.app/guide/faq.html#missing-assets-from-sw-precache-manifest
      injectManifest: {
        maximumFileSizeToCacheInBytes: 5 * 1024 * 1024, // 5 MiB
      },
      // ------------------------------------------
      
      registerType: 'autoUpdate', // Aggiorna l'app appena c'è una nuova versione
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'masked-icon.svg'],
      
      // Permette di testare la PWA in modalità dev (npm run dev)
      devOptions: {
        enabled: true,
        type: 'module', // Spesso necessario con injectManifest in dev
      },

      manifest: {
        name: 'KOR-35 Gestione personaggi',
        short_name: 'KOR-35 PG',
        description: 'Web app per il gioco di ruolo dal vivo (LARP) KOR-35 per la gestione dei propri personaggi',
        theme_color: '#ffffff',
        background_color: '#ffffff',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        icons: [
          {
            src: '/pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: '/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: '/pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ],
        screenshots: [
          {
            src: 'screenshots/desktop-home.png',
            sizes: '1577x998',
            type: 'image/png',
            form_factor: 'wide'
          },
          {
            src: 'screenshots/mobile-home.png',
            sizes: '981x2048',
            type: 'image/png'
          }
        ]
      }
    })
  ];

  // Attiva basicSsl SOLO se stiamo eseguendo il server di sviluppo ('serve')
  if (command === 'serve') {
    plugins.push(basicSsl());
  }

  return {
    plugins: plugins,
    build: {
      sourcemap: true,
    },
    define: {
      '__APP_VERSION__': JSON.stringify(packageJson.version),
    },
    server: {
      host: true,
      https: command === 'serve',
      // Con API_BASE_URL vuoto (default), fetch usa /api e /media relativi: qui in dev li proxy a Django.
      proxy: command === 'serve' ? {
        '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
        '/media': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      } : undefined,
    }
  };
});