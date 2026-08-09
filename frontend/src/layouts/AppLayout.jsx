import React, { useState, useEffect, lazy, Suspense } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useCharacter } from '../components/CharacterContext';

const StaffDashboard = lazy(() => import('../components/StaffDashboard'));
const MainPage = lazy(() => import('../components/MainPage'));
const StartPage = lazy(() => import('../components/StartPage'));
const EventSubscriptionResultPage = lazy(() => import('../pages/EventSubscriptionResultPage'));

const LayoutFallback = () => (
  <div className="flex h-full min-h-[50vh] items-center justify-center bg-gray-900 text-gray-300" role="status">
    <div className="animate-spin rounded-full h-10 w-10 border-t-2 border-b-2 border-indigo-500" />
  </div>
);

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

  // Preload chunk staff in idle se l'utente può aprirlo (non blocca first paint player).
  useEffect(() => {
    if (!canAccessStaffDashboard) return undefined;
    let cancelled = false;
    const run = () => {
      if (!cancelled) import('../components/StaffDashboard');
    };
    let handle;
    if (typeof window.requestIdleCallback === 'function') {
      handle = window.requestIdleCallback(run, { timeout: 4000 });
      return () => {
        cancelled = true;
        window.cancelIdleCallback?.(handle);
      };
    }
    handle = window.setTimeout(run, 2500);
    return () => {
      cancelled = true;
      clearTimeout(handle);
    };
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
      <Suspense fallback={<LayoutFallback />}>
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
      </Suspense>
    );
  }

  if (isEventSubscriptionResultPath) {
    return (
      <Suspense fallback={<LayoutFallback />}>
        <EventSubscriptionResultPage onLogout={onLogout} />
      </Suspense>
    );
  }

  if (isStartPagePath) {
    return (
      <Suspense fallback={<LayoutFallback />}>
        <StartPage
          onLogout={onLogout}
          onSwitchToMaster={goToStaffDashboard}
        />
      </Suspense>
    );
  }

  // Render: Vista Giocatore (Default per tutti)
  return (
    <Suspense fallback={<LayoutFallback />}>
      <MainPage
        token={token}
        onLogout={onLogout}
        onSwitchToMaster={goToStaffDashboard}
      />
    </Suspense>
  );
};

export default AppLayout;
