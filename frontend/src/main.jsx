import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { installChunkRecovery } from './chunkRecovery.js'

// Crea il client. Configura cache e refetch automatici.
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5, // I dati sono "freschi" per 5 minuti
      refetchOnWindowFocus: false, // Evita refetch continuo se cambi tab browser
      retry: 1,
    },
  },
})

// Recover from stale dynamic-import chunks after deployments.
installChunkRecovery()

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>,
)