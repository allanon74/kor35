import React, { useCallback, useEffect, useRef, useState } from 'react';
import LoginQR from './components/LoginQR.jsx';
import IdleScreen from './components/IdleScreen.jsx';
import Cockpit from './components/Cockpit.jsx';
import { api, getToken, setToken } from './api.js';
import {
  flushOfflineQueue,
  loadCachedState,
  saveCachedState,
  clearCachedState,
} from './engine.js';

const POLL_INTERVAL_MS = 3000;
const SCREEN_MODE = new URLSearchParams(window.location.search).get('screen') || 'both';

export default function App() {
  const [authToken, setAuthToken] = useState(getToken());
  const [authError, setAuthError] = useState('');
  const [consoleEnabled, setConsoleEnabled] = useState(true);
  const [loginRequired, setLoginRequired] = useState(true);
  const [consoleChecked, setConsoleChecked] = useState(false);
  const [state, setState] = useState(() => loadCachedState());
  const [prefetture, setPrefetture] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(true);
  const [tentativi, setTentativi] = useState([]);
  const [tickRuntime, setTickRuntime] = useState(null);
  const [commandStatus, setCommandStatus] = useState('');

  const pollTimerRef = useRef(null);

  const refreshState = useCallback(async () => {
    if (!getToken()) return;
    try {
      const data = await api.state();
      setState(data);
      setTickRuntime(data?.tick_runtime || null);
      saveCachedState(data);
      setOnline(true);
      try {
        const hist = await api.history();
        setTentativi(hist || []);
      } catch (_) { /* non bloccante */ }
    } catch (e) {
      if (e.network) setOnline(false);
      if (e.status === 401) {
        setToken('');
        setAuthToken('');
        setAuthError('Sessione console scaduta, riautenticarsi.');
      }
    }
  }, []);

  useEffect(() => {
    api.consoleEnabled()
      .then((res) => {
        setConsoleEnabled(!!res?.enabled);
        setLoginRequired(res?.login_required !== false);
      })
      .catch(() => setConsoleEnabled(false))
      .finally(() => setConsoleChecked(true));
  }, []);

  useEffect(() => {
    if (!consoleChecked || !consoleEnabled || loginRequired || authToken) return;
    api.autoLogin()
      .then((res) => {
        if (res?.token) {
          setToken(res.token);
          setAuthToken(res.token);
          clearCachedState();
        }
      })
      .catch(() => {
        setAuthError('Auto-login non disponibile.');
      });
  }, [consoleChecked, consoleEnabled, loginRequired, authToken]);

  useEffect(() => {
    if (!authToken) return;
    refreshState();
    api.prefetture().then(setPrefetture).catch(() => setPrefetture([]));
  }, [authToken, refreshState]);

  useEffect(() => {
    if (!authToken) return;
    const id = setInterval(() => {
      refreshState();
      flushOfflineQueue(api).then(({ applicati }) => {
        if (applicati > 0) refreshState();
      }).catch(() => {});
    }, POLL_INTERVAL_MS);
    pollTimerRef.current = id;
    return () => clearInterval(id);
  }, [authToken, refreshState]);

  const handleAuthorized = useCallback((token) => {
    setToken(token);
    setAuthToken(token);
    clearCachedState();
  }, []);

  const handleLogout = useCallback(async () => {
    try { await api.logout(); } catch (_) { /* offline ok */ }
    setToken('');
    setAuthToken('');
    setState(null);
    setTentativi([]);
    clearCachedState();
  }, []);

  const handleStart = useCallback(async (partenza, arrivo) => {
    setError('');
    setBusy(true);
    try {
      const res = await api.startSession(partenza, arrivo);
      setState(res);
      saveCachedState(res);
    } catch (e) {
      setError(e.message || 'Errore avvio.');
    } finally {
      setBusy(false);
    }
  }, []);

  const handleAbort = useCallback(async () => {
    if (!window.confirm('Interrompere il volo? La sessione verra terminata.')) return;
    try {
      const res = await api.abort();
      setState(res);
      saveCachedState(res);
    } catch (e) {
      setError(e.message || 'Errore abort.');
    }
  }, []);

  const handleSubsystemSet = useCallback(async (payload) => {
    setError('');
    setCommandStatus('Invio comando in corso...');
    try {
      const res = await api.subsystemSet(payload);
      setState(res);
      saveCachedState(res);
      setCommandStatus('Comando applicato.');
      await refreshState();
    } catch (e) {
      setError(e.message || 'Errore aggiornamento sottosistema.');
      setCommandStatus(`Errore comando: ${e.message || 'aggiornamento non riuscito'}`);
    }
  }, [refreshState]);

  const handleTickControl = useCallback(async (action) => {
    try {
      const res = await api.tickControl(action);
      setTickRuntime(res);
    } catch (e) {
      setError(e.message || 'Errore controllo tick.');
    }
  }, []);

  if (!consoleChecked) {
    return <div className="center-screen"><div className="card">Verifica disponibilita console...</div></div>;
  }

  if (!consoleEnabled) {
    return (
      <div className="center-screen">
        <div className="card">
          <h1>KOR-35 // CONSOLE PILOTA</h1>
          <div className="error">Console pilotaggio non disponibile su questo ambiente.</div>
        </div>
      </div>
    );
  }

  if (!authToken) {
    return (
      <div className="app-shell">
        <div className="banner">
          <div className="ident">KOR-35 // PILOT CONSOLE</div>
          <div className="right">
            <span className={online ? 'net-online' : 'net-offline'}>
              {online ? 'BACKEND ON' : 'BACKEND OFF'}
            </span>
          </div>
        </div>
        <main>
          {loginRequired ? (
            <LoginQR
              createTicket={api.createConsoleTicket}
              pollTicket={api.ticketStatus}
              onAuthorized={handleAuthorized}
              error={authError}
            />
          ) : (
            <div className="center-screen"><div className="card">Accesso automatico console in corso...</div></div>
          )}
        </main>
      </div>
    );
  }

  return (
    <div className={`app-shell ${SCREEN_MODE === 'control' ? 'app-shell-control' : ''}`}>
      {SCREEN_MODE !== 'control' ? (
        <div className="banner">
          <div className="ident">
            KOR-35 // PILOT // {state?.pilota?.nome || '...'}
          </div>
          <div className="right">
            <span title={online ? 'Backend raggiungibile' : 'Backend non raggiungibile'} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: online ? '#4caf50' : '#ff5252', display: 'inline-block' }} />
            </span>
            <span title={tickRuntime?.enabled ? (tickRuntime?.alive ? 'Tick attivo' : 'Tick stale') : 'Tick disattivo'} style={{ display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
              <span style={{ width: 10, height: 10, borderRadius: '50%', background: (tickRuntime?.enabled && tickRuntime?.alive) ? '#4caf50' : (tickRuntime?.enabled ? '#ffa940' : '#888'), display: 'inline-block' }} />
            </span>
            <button type="button" className="btn" style={{ padding: '0.35rem 0.45rem', minWidth: 'auto' }} title="Start tick" onClick={() => handleTickControl('start')}>▶</button>
            <button type="button" className="btn danger" style={{ padding: '0.35rem 0.45rem', minWidth: 'auto' }} title="Stop tick" onClick={() => handleTickControl('stop')}>■</button>
            <button type="button" className="btn" style={{ padding: '0.35rem 0.55rem', minWidth: 'auto' }} title="Logout" onClick={handleLogout}>⎋</button>
          </div>
        </div>
      ) : null}
      <main>
        <div className="console-viewport-wrap">
          <div className="console-viewport-fixed">
            {(!state || !state.sessione || state.sessione.stato === 'idle') ? (
              <IdleScreen
                prefetture={prefetture}
                onStart={handleStart}
                error={error}
                busy={busy}
              />
            ) : (
              <Cockpit
                state={state}
                online={online}
                onAbort={handleAbort}
                onLogout={handleLogout}
                tentativi={tentativi}
                mode={SCREEN_MODE}
                onSubsystemSet={handleSubsystemSet}
                error={error}
                commandStatus={commandStatus}
              />
            )}
            {(commandStatus || error) ? (
              <div className={`command-overlay ${error ? 'ko' : 'ok'}`}>
                {error || commandStatus}
              </div>
            ) : null}
          </div>
        </div>
      </main>
    </div>
  );
}
