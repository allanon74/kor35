import React, { useCallback, useEffect, useRef, useState } from 'react';
import LoginQR from './components/LoginQR.jsx';
import IdleScreen from './components/IdleScreen.jsx';
import Cockpit from './components/Cockpit.jsx';
import CompattatoreScreen from './components/CompattatoreScreen.jsx';
import ScientificaScreen from './components/ScientificaScreen.jsx';
import ComunicazioniScreen from './components/ComunicazioniScreen.jsx';
import StationPicker from './components/StationPicker.jsx';
import { api, getToken, setToken } from './api.js';
import { speakAllarmeEquipaggio } from './pilotAlerts.js';
import {
  flushOfflineQueue,
  loadCachedState,
  saveCachedState,
  clearCachedState,
} from './engine.js';
import { applyViewportClass, fromStation, navigateScreen } from './viewport.js';

const POLL_INTERVAL_MS = 3000;
const QUERY = new URLSearchParams(window.location.search);
const SCREEN_MODE = QUERY.get('screen') || 'both';
const PREVIEW = QUERY.get('preview') || '';
const POLL_ADVANCE_TICK = SCREEN_MODE !== 'status';
const IS_CONTROL_ONLY = SCREEN_MODE === 'control';
const IS_COMBINED = SCREEN_MODE === 'combined';
const IS_COMPATTATORE = SCREEN_MODE === 'compattatore';
const IS_SCIENTIFICA = SCREEN_MODE === 'scientifica';
const IS_COMUNICAZIONI = SCREEN_MODE === 'comunicazioni';
const IS_STATION = SCREEN_MODE === 'station';
const IS_LAB = IS_COMPATTATORE || IS_SCIENTIFICA;
const IS_PREVIEW_LAYOUT = PREVIEW === 'layout';
const IS_PREVIEW_LOGIN = PREVIEW === 'login';

export default function App() {
  const [authToken, setAuthToken] = useState(getToken());
  const [authError, setAuthError] = useState('');
  const [consoleEnabled, setConsoleEnabled] = useState(true);
  const [loginRequired, setLoginRequired] = useState(true);
  const [navigazioneStatSigla, setNavigazioneStatSigla] = useState('0PI');
  const [consoleChecked, setConsoleChecked] = useState(false);
  const [state, setState] = useState(() => loadCachedState());
  const [percorsi, setPercorsi] = useState([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [online, setOnline] = useState(true);
  const [tentativi, setTentativi] = useState([]);
  const [tickRuntime, setTickRuntime] = useState(null);
  const [commandStatus, setCommandStatus] = useState('');
  const [compact, setCompact] = useState(() => applyViewportClass());

  const pollTimerRef = useRef(null);
  const alarmSpokenAtRef = useRef('');
  const alarmAudioReadyRef = useRef(false);

  useEffect(() => {
    const apply = () => setCompact(applyViewportClass());
    apply();
    window.addEventListener('resize', apply);
    return () => window.removeEventListener('resize', apply);
  }, []);

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
      const data = await api.state({ advanceTick: POLL_ADVANCE_TICK });
      await applyStatePayload(data);
    } catch (e) {
      if (e.status === 500) {
        try {
          const data = await api.state({ advanceTick: POLL_ADVANCE_TICK });
          await applyStatePayload(data);
          return;
        } catch (_) {
          /* fallback sotto */
        }
      }
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
              const data = await api.state({ advanceTick: POLL_ADVANCE_TICK });
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
    if (IS_STATION || IS_PREVIEW_LAYOUT || IS_PREVIEW_LOGIN) {
      setConsoleChecked(true);
      return undefined;
    }
    const loader = IS_COMUNICAZIONI
      ? api.comunicazioniConsoleEnabled
      : IS_SCIENTIFICA
        ? api.scientificaConsoleEnabled
        : IS_COMPATTATORE
          ? api.compattatoreConsoleEnabled
          : api.consoleEnabled;
    loader()
      .then((res) => {
        setConsoleEnabled(!!res?.enabled);
        setLoginRequired(res?.login_required !== false);
        const sigla = res?.comunicazioni_stat_accesso_sigla
          || res?.scientifica_stat_accesso_sigla
          || res?.compattatore_stat_accesso_sigla
          || res?.navigazione_stat_accesso_sigla;
        if (sigla) {
          setNavigazioneStatSigla(String(sigla).toUpperCase());
        }
      })
      .catch(() => setConsoleEnabled(false))
      .finally(() => setConsoleChecked(true));
    return undefined;
  }, []);

  useEffect(() => {
    if (IS_STATION || IS_PREVIEW_LAYOUT || IS_PREVIEW_LOGIN) return undefined;
    if (!consoleChecked || !consoleEnabled || loginRequired || authToken) return undefined;
    const loginFn = IS_COMUNICAZIONI
      ? api.comunicazioniAutoLogin
      : IS_SCIENTIFICA
        ? api.scientificaAutoLogin
        : IS_COMPATTATORE
          ? api.compattatoreAutoLogin
          : api.autoLogin;
    loginFn()
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
    if (!authToken || IS_LAB || IS_COMUNICAZIONI) return;
    refreshState();
    api.percorsi().then(setPercorsi).catch(() => setPercorsi([]));
  }, [authToken, refreshState]);

  useEffect(() => {
    if (!authToken || IS_LAB || IS_COMUNICAZIONI) return;
    const id = setInterval(() => {
      refreshState();
      flushOfflineQueue(api).then(({ applicati }) => {
        if (applicati > 0) refreshState();
      }).catch(() => {});
    }, POLL_INTERVAL_MS);
    pollTimerRef.current = id;
    return () => clearInterval(id);
  }, [authToken, refreshState]);

  useEffect(() => {
    if (IS_COMUNICAZIONI || IS_LAB || IS_STATION) return;
    if (state?.comunicazioni_console_abilitata !== true) return;
    const at = state?.allarme_equipaggio_at || '';
    if (!alarmAudioReadyRef.current) {
      alarmAudioReadyRef.current = true;
      alarmSpokenAtRef.current = at;
      return;
    }
    if (!at || at === alarmSpokenAtRef.current) return;
    alarmSpokenAtRef.current = at;
    const testo = String(state?.allarme_annuncio || '').trim();
    if (!testo) return;
    speakAllarmeEquipaggio(testo, state?.allarme_equipaggio).catch(() => {});
  }, [
    state?.comunicazioni_console_abilitata,
    state?.allarme_equipaggio_at,
    state?.allarme_annuncio,
    state?.allarme_equipaggio,
  ]);

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
    if (fromStation()) navigateScreen('station');
  }, []);

  const handleBackToStation = useCallback(() => {
    setToken('');
    setAuthToken('');
    navigateScreen('station');
  }, []);

  const handleStart = useCallback(async (percorsoId) => {
    setError('');
    setBusy(true);
    try {
      const res = await api.startSession(percorsoId);
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
      await speakItalianAnnouncement(prep?.announcement || '', { allarme: 'blu' });
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

  const consoleNome = IS_COMUNICAZIONI
    ? 'comunicazioni'
    : IS_SCIENTIFICA
      ? 'scientifica'
      : IS_COMPATTATORE
        ? 'ingegneria'
        : 'pilotaggio';
  const consoleTitolo = IS_COMUNICAZIONI
    ? 'CONSOLE COMUNICAZIONI'
    : IS_SCIENTIFICA
      ? 'CONSOLE SCIENTIFICA'
      : IS_COMPATTATORE
        ? 'CONSOLE INGEGNERIA'
        : 'CONSOLE PILOTA';
  const loginTitle = IS_COMUNICAZIONI
    ? 'KOR-35 // CONSOLE COMUNICAZIONI'
    : IS_SCIENTIFICA
      ? 'KOR-35 // CONSOLE SCIENTIFICA'
      : IS_COMPATTATORE
        ? 'KOR-35 // CONSOLE INGEGNERIA'
        : 'KOR-35 // CONSOLE PILOTA';
  const loginRequisito = (IS_LAB || IS_COMUNICAZIONI)
    ? `Requisito: statistica ${navigazioneStatSigla} > 0.`
    : null;
  const backToStation = fromStation() ? handleBackToStation : null;

  if (IS_STATION) {
    return (
      <div className="app-shell app-shell-station">
        <StationPicker preview={IS_PREVIEW_LAYOUT} />
      </div>
    );
  }

  if (IS_PREVIEW_LAYOUT && IS_COMUNICAZIONI) {
    return (
      <div className="app-shell app-shell-comunicazioni">
        <main>
          <ComunicazioniScreen preview onLogout={() => {}} onBack={backToStation} compact={compact} />
        </main>
      </div>
    );
  }

  if (IS_PREVIEW_LAYOUT && !IS_LAB && !IS_STATION && !IS_COMUNICAZIONI) {
    const percorsiPreview = [
      { id: 'bosco', partenza: 'Bosco nord', arrivo: 'Avamposto', distanza_minima: 800, distanza_massima: 1400 },
      { id: 'lunga', partenza: 'Cittadella', arrivo: 'Frontiera', distanza_minima: 3000, distanza_massima: 6000 },
    ];
    return (
      <div className="app-shell">
        <main>
          <IdleScreen percorsi={percorsiPreview} onStart={() => {}} error="" busy={false} />
        </main>
      </div>
    );
  }

  if (IS_PREVIEW_LAYOUT && IS_LAB) {
    return (
      <div className={`app-shell ${IS_COMPATTATORE ? 'app-shell-compattatore' : 'app-shell-scientifica'}`}>
        <main>
          {IS_SCIENTIFICA ? (
            <ScientificaScreen
              onLogout={handleLogout}
              onBack={backToStation}
              navigazioneStatSigla={navigazioneStatSigla || '0SC'}
              compact={compact}
              preview
            />
          ) : (
            <CompattatoreScreen
              onLogout={handleLogout}
              onBack={backToStation}
              compact={compact}
              preview
            />
          )}
        </main>
      </div>
    );
  }

  if (IS_PREVIEW_LOGIN && (IS_LAB || IS_COMUNICAZIONI)) {
    return (
      <div className="app-shell">
        <main>
          <LoginQR
            createTicket={api.createConsoleTicket}
            pollTicket={api.ticketStatus}
            onAuthorized={handleAuthorized}
            navigazioneStatSigla={IS_COMUNICAZIONI ? '0CO' : IS_SCIENTIFICA ? '0SC' : '0IN'}
            title={loginTitle}
            requisito={
              IS_COMUNICAZIONI
                ? 'Requisito: statistica 0CO > 0.'
                : IS_SCIENTIFICA
                  ? 'Requisito: statistica 0SC > 0.'
                  : 'Requisito: statistica 0IN > 0.'
            }
            onBack={backToStation}
            previewClaimUrl="https://www.kor35.it/api/pilot/auth/console-ticket/preview/claim/?c=DEMO"
          />
        </main>
      </div>
    );
  }

  if (!consoleChecked) {
    return <div className="center-screen"><div className="card">Verifica disponibilita console...</div></div>;
  }

  if (!consoleEnabled) {
    return (
      <div className="center-screen">
        <div className="card">
          <h1>KOR-35 // {consoleTitolo}</h1>
          <div className="error">Console {consoleNome} non disponibile su questo ambiente.</div>
          {backToStation ? (
            <button type="button" className="btn" onClick={backToStation}>Torna alla scelta</button>
          ) : null}
        </div>
      </div>
    );
  }

  if (!authToken) {
    return (
      <div className="app-shell">
        <div className="banner">
          <div className="ident">KOR-35 // {IS_COMUNICAZIONI ? 'RADIO' : IS_SCIENTIFICA ? 'LAB CAMPO' : IS_COMPATTATORE ? 'NODO Z' : 'PILOT CONSOLE'}</div>
          <div className="right">
            <span className={online ? 'net-online' : 'net-offline'}>
              {online ? 'BACKEND ON' : 'BACKEND OFF'}
            </span>
          </div>
        </div>
        <main>
          {loginRequired ? (
            <LoginQR
              createTicket={
                IS_COMUNICAZIONI
                  ? api.createComunicazioniConsoleTicket
                  : IS_SCIENTIFICA
                    ? api.createScientificaConsoleTicket
                    : IS_COMPATTATORE
                      ? api.createCompattatoreConsoleTicket
                      : api.createConsoleTicket
              }
              pollTicket={api.ticketStatus}
              onAuthorized={handleAuthorized}
              error={authError}
              navigazioneStatSigla={navigazioneStatSigla}
              title={loginTitle}
              requisito={loginRequisito}
              onBack={backToStation}
            />
          ) : (
            <div className="center-screen"><div className="card">Accesso automatico console in corso...</div></div>
          )}
        </main>
      </div>
    );
  }

  if (IS_COMUNICAZIONI && authToken) {
    return (
      <div className="app-shell app-shell-comunicazioni">
        <main>
          <ComunicazioniScreen
            onLogout={handleLogout}
            onBack={backToStation}
            compact={compact}
          />
        </main>
      </div>
    );
  }

  if (IS_SCIENTIFICA && authToken) {
    return (
      <div className="app-shell app-shell-scientifica">
        <main>
          <ScientificaScreen
            onLogout={handleLogout}
            onBack={backToStation}
            navigazioneStatSigla={navigazioneStatSigla}
            compact={compact}
          />
        </main>
      </div>
    );
  }

  return (
    <div className={`app-shell ${IS_CONTROL_ONLY ? 'app-shell-control' : ''} ${IS_COMBINED ? 'app-shell-combined' : ''} ${IS_COMPATTATORE ? 'app-shell-compattatore' : ''}`}>
      {!IS_CONTROL_ONLY && !IS_COMPATTATORE ? (
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
          <CompattatoreScreen onLogout={handleLogout} onBack={backToStation} compact={compact} />
        ) : (
        <div className={`console-viewport-wrap ${IS_CONTROL_ONLY ? 'is-fixed' : ''} ${IS_COMBINED ? 'is-combined' : ''}`}>
          <div className={`console-viewport-fixed ${IS_CONTROL_ONLY ? 'is-fixed' : ''} ${IS_COMBINED ? 'is-combined' : ''}`}>
            {(!state || !state.sessione || state.sessione.stato === 'idle') ? (
              <IdleScreen
                percorsi={percorsi}
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
