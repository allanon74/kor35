import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { installChunkRecovery } from './chunkRecovery.js'
import { ensureAppServiceWorker } from './lib/appServiceWorker.js'
import { applyNativePlatformMarker, isNativeApp } from './lib/nativePlatform.js'
import { startNativeIncomingCallBridge } from './lib/nativeIncomingCallBridge.js'
import { startNativeArcanaSsoBridge } from './lib/nativeArcanaSsoBridge.js'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
})

installChunkRecovery()
applyNativePlatformMarker()
// Nella shell Capacitor il contenuto arriva dal server remoto: lo SW browser
// non è il canale push primario (usa FCM). Restiamo allineati alla PWA sul web.
if (!isNativeApp()) {
  ensureAppServiceWorker()
}

startNativeIncomingCallBridge().catch(() => {})
startNativeArcanaSsoBridge().catch(() => {})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)
