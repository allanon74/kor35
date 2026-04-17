import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
// Importiamo sia il Provider "vero" che il Context "nudo"
import { CharacterProvider, CharacterContext } from './components/CharacterContext';
import LoginPage from './components/LoginPage';

// Layouts
import AppLayout from './layouts/AppLayout';
import PublicLayout from './layouts/PublicLayout';

// Pages
import WikiPage from './pages/WikiPage';
import SocialPublicPostPage from './pages/SocialPublicPostPage';
import SocialPage from './pages/SocialPage';
import { API_BASE_URL } from './api';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('kor35_token'));
  const [isLoading, setIsLoading] = useState(true);
  const searchParams = new URLSearchParams(window.location.search);
  const hasArcanaFlowParams = searchParams.has('arcana_ticket') || searchParams.has('arcana_error');

  useEffect(() => {
    const storedToken = localStorage.getItem('kor35_token');
    if (storedToken) {
      setToken(storedToken);
    }
    setIsLoading(false);
  }, []);

  const handleLoginSuccess = (newToken) => {
    localStorage.setItem('kor35_token', newToken);
    setToken(newToken);
  };

  const handleLogout = () => {
    const loginMethod = String(localStorage.getItem('kor35_login_method') || '').toLowerCase();
    localStorage.removeItem('kor35_token');
    localStorage.removeItem('kor35_is_admin');
    localStorage.removeItem('kor35_is_staff');
    localStorage.removeItem('kor35_is_master');
    localStorage.removeItem('kor35_last_char_id');
    localStorage.removeItem('kor35_active_campaign');
    localStorage.removeItem('kor35_login_method');
    setToken(null);
    if (loginMethod === 'arcana') {
      window.location.href = `${API_BASE_URL}/api/auth/arcana/frontchannel-logout/?return_to=${encodeURIComponent('/login')}`;
      return;
    }
    window.location.href = '/login'; 
  };

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">Caricamento...</div>;
  }

  // --- CORREZIONE CHIAVE ---
  // Se c'è il token, usiamo il Provider VERO (che carica dati dal server).
  // Se NON c'è, usiamo un Provider FINTO (che dà valori nulli sicuri).
  const SafeProvider = ({ children }) => {
    if (token) {
      return (
        <CharacterProvider onLogout={handleLogout}>
          {children}
        </CharacterProvider>
      );
    } else {
      // Context per Ospiti: tutto spento/falso
      const guestValue = {
        isCampaignStaffer: false,
        isCampaignMaster: false,
        isCampaignHeadMaster: false,
        isCampaignRedactor: false,
        isAdmin: false,
        character: null,
        notifiche: [],
        punteggiList: [], // Evita crash se qualche componente cerca liste
        personaggiList: [],
        isLoading: false
      };
      
      return (
        <CharacterContext.Provider value={guestValue}>
          {children}
        </CharacterContext.Provider>
      );
    }
  };

  return (
    <BrowserRouter>
      <SafeProvider>
        <Routes>
          <Route path="/social" element={<Navigate to="/app/social" replace />} />
          <Route path="/instafame" element={<Navigate to="/app/social" replace />} />
          {/* --- ROTTE PUBBLICHE --- */}
          <Route path="/" element={<PublicLayout token={token} />}>
            <Route index element={<WikiPage slug="home" />} />
            <Route path="regolamento/:slug" element={<WikiPage />} />
            <Route path="social/post/:slug" element={<SocialPublicPostPage />} />
            <Route 
              path="login" 
              element={
                token && !hasArcanaFlowParams
                  ? <Navigate to="/app" replace />
                  : <LoginPage onLoginSuccess={handleLoginSuccess} />
              } 
            />
          </Route>

          {/* --- ROTTE APP (PROTETTE) --- */}
          <Route
            path="/app/social"
            element={
              token ? (
                <SocialPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route 
            path="/app/*" 
            element={
              token ? (
                <AppLayout token={token} onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            } 
          />
        </Routes>
      </SafeProvider>
    </BrowserRouter>
  );
}