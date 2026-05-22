import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCharacter } from '../components/CharacterContext';
import StaffDashboard from '../components/StaffDashboard';
import MainPage from '../components/MainPage';
import StartPage from '../components/StartPage';
import EventSubscriptionResultPage from '../pages/EventSubscriptionResultPage';

const AppLayout = ({ token, onLogout }) => {
  const { isCampaignStaffer, isGlobalSuperuser } = useCharacter();
  const navigate = useNavigate();
  const location = useLocation();
  const isStartPagePath = location.pathname === '/app' || location.pathname === '/app/start';
  const isEventSubscriptionResultPath = location.pathname === '/app/iscrizione-esito';

  /** Allineato ai pulsanti «Dashboard staff» (ruolo campagna o superuser). */
  const canAccessStaffDashboard = isCampaignStaffer || isGlobalSuperuser;

  // 'staff' = Dashboard Master | 'player' = Interfaccia Giocatore
  const [viewMode, setViewMode] = useState('player');

  const [dashboardInitialTool, setDashboardInitialTool] = useState('home');

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const mode = params.get('mode');
    const tool = params.get('tool');

    if (!canAccessStaffDashboard) {
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

    setViewMode('player');
  }, [canAccessStaffDashboard, location.search]);

  useEffect(() => {
    if (!canAccessStaffDashboard) {
      setViewMode('player');
    }
  }, [canAccessStaffDashboard]);

  const updateUrlParams = (nextMode, nextTool = null) => {
    const params = new URLSearchParams(location.search);
    params.set('mode', nextMode);
    if (nextMode === 'master' || nextMode === 'staff') {
      params.set('tool', nextTool || 'home');
    } else {
      params.delete('tool');
    }
    const nextSearch = params.toString();
    const currentSearch = (location.search || '').replace(/^\?/, '');
    if (nextSearch === currentSearch) return;
    navigate({ pathname: location.pathname, search: `?${nextSearch}` }, { replace: true });
  };

  /** Ingresso unificato alla dashboard staff (pathname + query sempre coerenti). */
  const goToStaffDashboard = (tool = 'home') => {
    if (!canAccessStaffDashboard) return;
    const resolvedTool = tool || 'home';
    setDashboardInitialTool(resolvedTool);
    setViewMode('staff');
    const params = new URLSearchParams();
    params.set('mode', 'master');
    params.set('tool', resolvedTool);
    navigate({ pathname: '/app/play', search: `?${params.toString()}` }, { replace: true });
  };

  if (canAccessStaffDashboard && viewMode === 'staff') {
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

  if (isEventSubscriptionResultPath) {
    return <EventSubscriptionResultPage onLogout={onLogout} />;
  }

  if (isStartPagePath) {
    return (
      <StartPage
        onLogout={onLogout}
        onSwitchToMaster={goToStaffDashboard}
      />
    );
  }

  // Render: Vista Giocatore (Default per tutti)
  return (
    <MainPage 
      token={token}
      onLogout={onLogout}
      onSwitchToMaster={goToStaffDashboard}
    />
  );
};

export default AppLayout;