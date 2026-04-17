import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCharacter } from '../components/CharacterContext';
import StaffDashboard from '../components/StaffDashboard';
import MainPage from '../components/MainPage';
import StartPage from '../components/StartPage';

const AppLayout = ({ token, onLogout }) => {
  const { isCampaignStaffer, isCampaignMaster } = useCharacter();
  const navigate = useNavigate();
  const location = useLocation();
  const isStartPagePath = location.pathname === '/app' || location.pathname === '/app/start';
  
  // Stato per gestire quale interfaccia mostrare (solo per lo staff)
  // 'staff' = Dashboard Master | 'player' = Interfaccia Giocatore
  const [viewMode, setViewMode] = useState('player'); 

  // Memorizza quale tool aprire nella dashboard (default 'home')
  const [dashboardInitialTool, setDashboardInitialTool] = useState('home');

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const mode = params.get('mode');
    const tool = params.get('tool');

    if (!isCampaignStaffer) {
      setViewMode('player');
      return;
    }

    if (mode === 'master' || mode === 'staff') {
      setViewMode('staff');
      setDashboardInitialTool(tool || 'home');
      return;
    }

    if (mode === 'player' || mode === 'personaggi') {
      setViewMode('player');
      return;
    }

    // Default staff senza mode esplicito: resta/entra in vista player.
    setViewMode('player');
  }, [isCampaignStaffer, isCampaignMaster, location.search]);

  // Effetto: Se l'utente non è staff, forziamo sempre la vista player
  useEffect(() => {
    if (!isCampaignStaffer) {
      setViewMode('player');
    }
  }, [isCampaignStaffer, isCampaignMaster]);

  const updateUrlParams = (nextMode, nextTool = null) => {
    const params = new URLSearchParams(location.search);
    params.set('mode', nextMode);
    if (nextMode === 'master' && nextTool) {
      params.set('tool', nextTool);
    } else {
      params.delete('tool');
    }
    const nextSearch = params.toString();
    const currentSearch = (location.search || '').replace(/^\?/, '');
    if (nextSearch === currentSearch) return;
    navigate({ pathname: location.pathname, search: `?${nextSearch}` }, { replace: true });
  };

  // Render: Vista Master (Solo se è staff E siamo in modalità staff)
  if (isCampaignStaffer && viewMode === 'staff') {
    return (
      <StaffDashboard 
        token={token}
        onLogout={onLogout} 
        onSwitchToPlayer={() => {
            setViewMode('player');
            setDashboardInitialTool('home'); 
            updateUrlParams('player');
        }}
        onToolChange={(tool) => {
          setDashboardInitialTool(tool || 'home');
          updateUrlParams('master', tool || 'home');
        }}
        initialTool={dashboardInitialTool}
      />
    );
  }

  if (isStartPagePath) {
    return (
      <StartPage
        onLogout={onLogout}
        onSwitchToMaster={(tool = 'home') => {
          setDashboardInitialTool(tool);
          setViewMode('staff');
          updateUrlParams('master', tool);
          navigate('/app/play', { replace: true });
        }}
      />
    );
  }

  // Render: Vista Giocatore (Default per tutti)
  return (
    <MainPage 
      token={token}
      onLogout={onLogout}
      onSwitchToMaster={(tool = 'home') => {
          setDashboardInitialTool(tool);
          setViewMode('staff');
          updateUrlParams('master', tool);
      }}
    />
  );
};

export default AppLayout;