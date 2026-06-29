import React, { useCallback, useEffect, useRef, useState } from 'react';
import LoginQR from './components/LoginQR.jsx';
import IdleScreen from './components/IdleScreen.jsx';
import Cockpit from './components/Cockpit.jsx';
import CompattatoreScreen from './components/CompattatoreScreen.jsx';
import { api, getToken, setToken } from './api.js';
import {
  flushOfflineQueue,
  loadCachedState,
  saveCachedState,
  clearCachedState,
} from './engine.js';

const POLL_INTERVAL_MS = 3000;
const SCREEN_MODE = new URLSearchParams(window.location.search).get('screen') || 'both';
const IS_CONTROL_ONLY = SCREEN_MODE === 'control';
const IS_COMBINED = SCREEN_MODE === 'combined';
const IS_COMPATTATORE = SCREEN_MODE === 'compattatore';

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

    const applyStatePayload = async (data) => {
      setState(data);
      setTickRuntime(data?.tick_runtime || null);
      saveCachedState(data);
      setOnline(true);
      try {
        const hist = await api.history();
        setTentativi(hist || []);
      } catch (_) {
        /* cronologia non bloccante */
      }
    };

    try {
      const data = await api.state();
      await applyStatePayload(data);
    } catch (e) {
      if (e.network) setOnline(false);
      if (e.status === 401) {
        /* Evita il lampeggio su kiosk: il poll ogni pochi secondi può ricevere 401
           transitori; se il backend consente auto-login, rinnoviamo il token senza
           smontare la UI (stesso comportamento atteso da una sessione pilota fissa). */
        let recovered = false;
        if (!loginRequired) {
          try {
            const res = await api.autoLogin();
            if (res?.token) {
              setToken(res.token);
              setAuthToken(res.token);
              const data = await api.state();
              await applyStatePayload(data);
              recovered = true;
            }
          } catch (_) {
            /* fallback sotto */
          }
        }
        if (!recovered) {
          setToken('');
          setAuthToken('');
          setAuthError('Sessione console scaduta, riautenticarsi.');
        }
      }
    }
  }, [loginRequired]);

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

  const handleResetSession = useCallback(async () => {
    setError('');
    try {
      const res = await api.resetSession();
      setState(res);
      saveCachedState(res);
      setCommandStatus('');
    } catch (e) {
      setError(e.message || 'Errore reset sessione.');
    }
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

  const handleEmergencyLanding = useCallback(async () => {
    setError('');
    try {
      const res = await api.emergencyLanding();
      setState(res);
      saveCachedState(res);
      setCommandStatus('Atterraggio di emergenza eseguito.');
      await refreshState();
    } catch (e) {
      setError(e.message || "Errore atterraggio d'emergenza.");
      setCommandStatus(`Errore atterraggio emergenza: ${e.message || 'non riuscito'}`);
    }
  }, [refreshState]);

  const handleTakeoff = useCallback(async () => {
    setError('');
    setCommandStatus('Sequenza di decollo in corso...');
    try {
      const prep = await api.takeoffPrepare();
      const { speakItalianAnnouncement } = await import('./pilotAlerts.js');
      await speakItalianAnnouncement(prep?.announcement || '');
      const res = await api.takeoffComplete();
      setState(res);
      saveCachedState(res);
      setCommandStatus('Decollo completato. Crociera attiva.');
      await refreshState();
    } catch (e) {
      setError(e.message || 'Errore decollo.');
      setCommandStatus(`Errore decollo: ${e.message || 'non riuscito'}`);
    }
  }, [refreshState]);

  const handleLanding = useCallback(async () => {
    setError('');
    try {
      const res = await api.landing();
      setState(res);
      saveCachedState(res);
      setCommandStatus('Atterraggio eseguito.');
      await refreshState();
    } catch (e) {
      setError(e.message || 'Errore atterraggio.');
      setCommandStatus(`Errore atterraggio: ${e.message || 'non riuscito'}`);
    }
  }, [refreshState]);

  const handleSetAllarme = useCallback(async (allarme) => {
    setError('');
    const res = await api.setAllarmeEquipaggio(allarme);
    setState(res);
    saveCachedState(res);
    return res;
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
    <div className={`app-shell ${IS_CONTROL_ONLY ? 'app-shell-control' : ''} ${IS_COMBINED ? 'app-shell-combined' : ''}`}>
      {!IS_CONTROL_ONLY ? (
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
        {IS_COMPATTATORE ? (
          <CompattatoreScreen onLogout={handleLogout} />
        ) : (
        <div className={`console-viewport-wrap ${IS_CONTROL_ONLY ? 'is-fixed' : ''} ${IS_COMBINED ? 'is-combined' : ''}`}>
          <div className={`console-viewport-fixed ${IS_CONTROL_ONLY ? 'is-fixed' : ''} ${IS_COMBINED ? 'is-combined' : ''}`}>
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
                onEmergencyLanding={handleEmergencyLanding}
                onTakeoff={handleTakeoff}
                onLanding={handleLanding}
                onSetAllarme={handleSetAllarme}
                onLogout={handleLogout}
                onResetSession={handleResetSession}
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
        )}
      </main>
    </div>
  );
}
