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
import EventoLogisticaPage from './pages/EventoLogisticaPage';
import SocialPage from './pages/SocialPage';
import MaintenanceConsolePage from './pages/MaintenanceConsolePage';
import { API_BASE_URL, getConfigurazioneSito, setApiMaintenanceMode, isApiMaintenanceMode } from './api';

export default function App() {
  const [token, setToken] = useState(localStorage.getItem('kor35_token'));
  const [isLoading, setIsLoading] = useState(true);
  const [isMaintenanceMode, setIsMaintenanceMode] = useState(() => isApiMaintenanceMode());
  const [maintenanceChecked, setMaintenanceChecked] = useState(false);
  const [isDjangoAdmin, setIsDjangoAdmin] = useState(
    String(localStorage.getItem('kor35_is_admin') || '').toLowerCase() === 'true'
  );
  const searchParams = new URLSearchParams(window.location.search);
  const hasArcanaFlowParams = searchParams.has('arcana_ticket') || searchParams.has('arcana_error');

  useEffect(() => {
    const storedToken = localStorage.getItem('kor35_token');
    if (storedToken) {
      setToken(storedToken);
    }
    setIsDjangoAdmin(String(localStorage.getItem('kor35_is_admin') || '').toLowerCase() === 'true');
    setIsLoading(false);
  }, []);

  useEffect(() => {
    let cancelled = false;
    const refresh = async () => {
      try {
        const cfg = await getConfigurazioneSito();
        if (cancelled) return;
        const active = !!cfg?.maintenance_mode;
        setIsMaintenanceMode(active);
        setApiMaintenanceMode(active);
      } catch {
        if (cancelled) return;
      } finally {
        if (!cancelled) setMaintenanceChecked(true);
      }
    };
    refresh();
    const interval = setInterval(refresh, 30000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, []);

  const handleLoginSuccess = (newToken) => {
    localStorage.setItem('kor35_token', newToken);
    setToken(newToken);
    setIsDjangoAdmin(String(localStorage.getItem('kor35_is_admin') || '').toLowerCase() === 'true');
    // Forza una rilettura del config sito subito dopo il login:
    // se la maintenance e' stata appena attivata, il flag globale lato API
    // deve aggiornarsi prima che CharacterProvider lanci nuove chiamate.
    (async () => {
      try {
        const cfg = await getConfigurazioneSito();
        const active = !!cfg?.maintenance_mode;
        setIsMaintenanceMode(active);
        setApiMaintenanceMode(active);
      } catch {
        /* fallback: stato attuale */
      } finally {
        setMaintenanceChecked(true);
      }
    })();
  };

  const handleLogout = () => {
    try {
      sessionStorage.removeItem('kor35_main_active_tab');
    } catch (e) {
      /* noop */
    }
    const loginMethod = String(localStorage.getItem('kor35_login_method') || '').toLowerCase();
    localStorage.removeItem('kor35_token');
    localStorage.removeItem('kor35_is_admin');
    localStorage.removeItem('kor35_is_staff');
    localStorage.removeItem('kor35_is_master');
    localStorage.removeItem('kor35_last_char_id');
    localStorage.removeItem('kor35_active_campaign');
    localStorage.removeItem('kor35_login_method');
    setToken(null);
    setIsDjangoAdmin(false);
    if (loginMethod === 'arcana') {
      window.location.href = `${API_BASE_URL}/api/auth/arcana/frontchannel-logout/?return_to=${encodeURIComponent('/login')}`;
      return;
    }
    window.location.href = '/login'; 
  };

  if (isLoading) {
    return <div className="flex items-center justify-center min-h-screen bg-gray-900 text-white">Caricamento...</div>;
  }

  // Prima del primo check del config sito non montiamo i provider applicativi:
  // se il sito e' in manutenzione, evitiamo che CharacterProvider faccia
  // partire le sue chiamate API (che verrebbero bloccate dal middleware con 503).
  // Bypass: se l'utente non e' loggato non c'e' nulla da pollerare.
  if (token && !maintenanceChecked) {
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
        isGlobalSuperuser: false,
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
            <Route path="eventi/:id" element={<EventoLogisticaPage />} />
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
            path="/app/maintenance"
            element={
              token ? (
                <MaintenanceConsolePage onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route
            path="/app/social"
            element={
              isMaintenanceMode ? (
                isDjangoAdmin ? <Navigate to="/app/maintenance" replace /> : <Navigate to="/" replace />
              ) : token ? (
                <SocialPage onLogout={handleLogout} />
              ) : (
                <Navigate to="/login" replace />
              )
            }
          />
          <Route 
            path="/app/*" 
            element={
              isMaintenanceMode ? (
                isDjangoAdmin ? <Navigate to="/app/maintenance" replace /> : <Navigate to="/" replace />
              ) : token ? (
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