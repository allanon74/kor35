import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCharacter } from '../components/CharacterContext';
import StaffDashboard from '../components/StaffDashboard';
import MainPage from '../components/MainPage';

const AppLayout = ({ token, onLogout }) => {
  const { isStaff } = useCharacter();
  const navigate = useNavigate();
  const location = useLocation();
  
  // Stato per gestire quale interfaccia mostrare (solo per lo staff)
  // 'staff' = Dashboard Master | 'player' = Interfaccia Giocatore
  const [viewMode, setViewMode] = useState('player'); 

  // Memorizza quale tool aprire nella dashboard (default 'home')
  const [dashboardInitialTool, setDashboardInitialTool] = useState('home');

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const mode = params.get('mode');
    const tool = params.get('tool');

    if (!isStaff) {
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
  }, [isStaff, location.search]);

  // Effetto: Se l'utente non è staff, forziamo sempre la vista player
  useEffect(() => {
    if (!isStaff) {
      setViewMode('player');
    }
  }, [isStaff]);

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
  if (isStaff && viewMode === 'staff') {
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

  // Render: Vista Giocatore (Default per tutti)
  return (
    <MainPage 
      token={token}
      onLogout={onLogout}
      isStaff={isStaff} 
      onSwitchToMaster={(tool = 'home') => {
          setDashboardInitialTool(tool);
          setViewMode('staff');
          updateUrlParams('master', tool);
      }}
    />
  );
};

export default AppLayout;