import React, { useCallback, useEffect, useRef, useState } from 'react';
import LoginQR from './components/LoginQR.jsx';
import IdleScreen from './components/IdleScreen.jsx';
import Cockpit from './components/Cockpit.jsx';
import { api, getToken, setToken } from './api.js';
import {
  flushOfflineQueue,
  loadCachedState,
  pushOfflineCommand,
  saveCachedState,
  clearCachedState,
} from './engine.js';

const POLL_INTERVAL_MS = 3000;

export default function App() {
  const [authToken, setAuthToken] = useState(getToken());
  const [authError, setAuthError] = useState('');
  const [consoleEnabled, setConsoleEnabled] = useState(true);
  const [consoleChecked, setConsoleChecked] = useState(false);
  const [state, setState] = useState(() => loadCachedState());
  const [prefetture, setPrefetture] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(true);
  const [lastValutazione, setLastValutazione] = useState(null);
  const [tentativi, setTentativi] = useState([]);

  const pollTimerRef = useRef(null);

  const refreshState = useCallback(async () => {
    if (!getToken()) return;
    try {
      const data = await api.state();
      setState(data);
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
      .then((res) => setConsoleEnabled(!!res?.enabled))
      .catch(() => setConsoleEnabled(false))
      .finally(() => setConsoleChecked(true));
  }, []);

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

  const handleCommand = useCallback(async (codice) => {
    setError('');
    try {
      const res = await api.command(codice);
      setState(res);
      saveCachedState(res);
      setLastValutazione(res.valutazione || null);
      setOnline(true);
      try {
        const hist = await api.history();
        setTentativi(hist || []);
      } catch (_) { /* non bloccante */ }
    } catch (e) {
      if (e.network) {
        pushOfflineCommand(codice);
        setOnline(false);
        setLastValutazione({
          esito: 'offline_queued',
          delta_defcon: 0,
          nuovo_defcon: state?.sessione?.defcon || 0,
          descrizione: 'Backend non raggiungibile: codice in coda offline.',
        });
      } else {
        setError(e.message || 'Errore comando.');
      }
    }
  }, [state]);

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
          <LoginQR
            createTicket={api.createConsoleTicket}
            pollTicket={api.ticketStatus}
            onAuthorized={handleAuthorized}
            error={authError}
          />
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <div className="banner">
        <div className="ident">
          KOR-35 // PILOT // {state?.pilota?.nome || '...'}
        </div>
        <div className="right">
          <span className={online ? 'net-online' : 'net-offline'}>
            {online ? 'BACKEND ON' : 'BACKEND OFF'}
          </span>
          <button type="button" className="btn" onClick={handleLogout}>Logout</button>
        </div>
      </div>
      <main>
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
            lastValutazione={lastValutazione}
            onCommand={handleCommand}
            onAbort={handleAbort}
            onLogout={handleLogout}
            tentativi={tentativi}
          />
        )}
      </main>
    </div>
  );
}
