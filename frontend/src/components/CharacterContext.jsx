import React, { createContext, useState, useContext, useCallback, useEffect, useRef } from 'react';
import { useQueryClient, useIsMutating } from '@tanstack/react-query';
import { 
  getMessages, 
  markMessageAsRead, 
  deleteMessage, 
  getAdminPendingProposalsCount, 
  saveWebPushSubscription,
  fetchAuthenticated,
  getPreferredPersonaggio,
  setPreferredPersonaggio,
  getPersonaggioDetail,
  getPersonaggioGameState,
  getAcquirableSkills,
  getAcquirableInfusioni,
  getAcquirableTessiture,
  getAcquirableCerimoniali,
  getCampaigns,
  validateActiveCampaign,
  getActiveCampaignSlug,
  setActiveCampaignSlug,
  normCampaignSlug,
  postEventoPremiApplica,
  getGiocoEventoStato,
} from '../api';
import NotificationPopup from './NotificationPopup';
import { putOfflineGameStateSnapshot } from '../lib/offlineGameStateDb';
import { activateWebPush, isWebPushSupported } from '../lib/webpush';

import { 
  usePunteggi, 
  useStatisticaContainers,
  usePersonaggiList, 
  usePersonaggioDetail, 
  useAcquirableSkills, 
  useAcquirableInfusioni, 
  useAcquirableTessiture,
  useAcquirableCerimoniali
} from '../hooks/useGameData';

export const CharacterContext = createContext(null);

// --- HELPER UTILS ---

const sendSystemNotification = (title, body) => {
    if (!("Notification" in window)) return;
    if (Notification.permission === "granted") {
      try {
          new Notification(title, { body, icon: '/pwa-192x192.png', vibrate: [200, 100, 200] });
      } catch (e) { console.error("Errore notifica:", e); }
    }
};

export const CharacterProvider = ({ children, onLogout }) => {
  const queryClient = useQueryClient();
  
  const mutatingCount = useIsMutating();
  
  // --- STATI GLOBALI UI ---
  const [selectedCharacterId, setSelectedCharacterId] = useState(() => localStorage.getItem('kor35_last_char_id') || '');
  const [preferredCharacterId, setPreferredCharacterId] = useState(() => localStorage.getItem('kor35_preferred_char_id') || '');
  /**
   * Solo superuser Django: bypass globale (es. notifiche sistema, vedi tutti i PG).
   * I permessi di gioco usano i ruoli di campagna (HEAD_MASTER, MASTER, …), non is_staff.
   */
  const [isGlobalSuperuser, setIsGlobalSuperuser] = useState(() => {
    const stored = localStorage.getItem('kor35_is_admin');
    if (stored !== null) return stored === 'true';
    return localStorage.getItem('kor35_is_master') === 'true';
  });
  const [isDjangoStaff, setIsDjangoStaff] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await fetchAuthenticated(
          '/api/personaggi/api/user/me/',
          { method: 'GET' },
          onLogout
        );
        if (cancelled || !me || typeof me !== 'object') return;
        const serverSuper = !!me.is_superuser;
        setIsGlobalSuperuser(serverSuper);
        localStorage.setItem('kor35_is_admin', String(serverSuper));
        setIsDjangoStaff(!!me.is_staff || serverSuper);
      } catch {
        /* mantieni fallback iniziale da localStorage */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onLogout]);
  const [staffWorkMode, setStaffWorkMode] = useState('dashboard');
  const [campaigns, setCampaigns] = useState([]);
  const [activeCampaign, setActiveCampaign] = useState(() => getActiveCampaignSlug());
  const activeCampaignMeta =
    campaigns.find((c) => normCampaignSlug(c.slug) === normCampaignSlug(activeCampaign)) || null;
  const activeCampaignRole = String(activeCampaignMeta?.ruolo || 'PLAYER').trim().toUpperCase();
  const isCampaignHeadMaster = activeCampaignRole === 'HEAD_MASTER';
  const isCampaignMaster =
    activeCampaignRole === 'MASTER' || activeCampaignRole === 'HEAD_MASTER';
  const isCampaignStaffer =
    activeCampaignRole === 'STAFFER' ||
    activeCampaignRole === 'MASTER' ||
    activeCampaignRole === 'HEAD_MASTER';
  const isCampaignRedactor = isCampaignStaffer || activeCampaignRole === 'REDACTOR';
  const canUseWizardTest = isGlobalSuperuser || isDjangoStaff || isCampaignStaffer;

  const [viewAll, setViewAll] = useState(false);
  const [giocoEventoStato, setGiocoEventoStato] = useState({
    evento_aperto: false,
    evento_titolo: null,
    azioni_live_abilitate: false,
    bypass_evento_gate: false,
    transazioni_giocatore_abilitate: false,
    nodo_scan_abilitato: false,
    allibratore_codici_abilitati: false,
  });
  
  // --- NUOVO STATO PER I TIMER (GESTIONE GLOBALE) ---
  const [activeTimers, setActiveTimers] = useState({});

  const updateTimerState = useCallback((timerData) => {
    setActiveTimers(prev => ({
        ...prev,
        [timerData.nome]: {
            ...timerData,
            endTime: new Date(timerData.data_fine).getTime()
        }
    }));
  }, []);

  const removeTimerState = useCallback((nomeTimer) => {
    setActiveTimers(prev => {
        const newState = { ...prev };
        delete newState[nomeTimer];
        return newState;
    });
  }, []);

  // --- FETCH INIZIALE TIMER ATTIVI ---
  useEffect(() => {
    const syncCampaign = async () => {
      try {
        const valid = await validateActiveCampaign(activeCampaign, onLogout);
        const normalized = setActiveCampaignSlug(valid?.slug || activeCampaign);
        setActiveCampaign(normalized);
      } catch {
        setActiveCampaign(setActiveCampaignSlug('kor35'));
      }
    };
    syncCampaign();
  }, [activeCampaign, onLogout]);

  useEffect(() => {
    const loadCampaigns = async () => {
      try {
        const list = await getCampaigns(onLogout);
        setCampaigns(Array.isArray(list) ? list : []);
      } catch {
        setCampaigns([]);
      }
    };
    loadCampaigns();
  }, [onLogout, activeCampaign]);

  useEffect(() => {
    let cancelled = false;
    const loadGiocoEventoStato = async () => {
      try {
        const data = await getGiocoEventoStato(onLogout);
        if (!cancelled && data && typeof data === 'object') {
          setGiocoEventoStato({
            evento_aperto: !!data.evento_aperto,
            evento_titolo: data.evento_titolo || null,
            azioni_live_abilitate: !!data.azioni_live_abilitate,
            bypass_evento_gate: !!data.bypass_evento_gate,
            transazioni_giocatore_abilitate: !!data.transazioni_giocatore_abilitate,
            nodo_scan_abilitato: !!data.nodo_scan_abilitato,
            allibratore_codici_abilitati: !!data.allibratore_codici_abilitati,
          });
        }
      } catch {
        /* rete: mantieni ultimo stato noto */
      }
    };
    loadGiocoEventoStato();
    const interval = setInterval(loadGiocoEventoStato, 60_000);
    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [onLogout]);

  useEffect(() => {
    const loadInitialTimers = async () => {
      try {
        const data = await fetchAuthenticated('/api/personaggi/api/timers/active/', onLogout);
        if (Array.isArray(data)) {
          data.forEach(t => updateTimerState(t));
        }
      } catch (err) {
        console.error("Errore caricamento timer iniziali", err);
      }
    };
    loadInitialTimers();
  }, [onLogout, updateTimerState]);


  // --- REACT QUERY HOOKS ---
  
  // 1. Punteggi
  const { data: punteggiList = [], isLoading: isLoadingPunteggi } = usePunteggi(onLogout);

  // 1b. Contenitori statistiche (config scheda)
  const { data: statisticaContainers = [], isLoading: isLoadingStatContainers } = useStatisticaContainers(onLogout);

  // 2. Lista Personaggi
  const { 
    data: personaggiList = [], 
    isLoading: isLoadingList, 
    refetch: refetchPersonaggiList 
  } = usePersonaggiList(onLogout, viewAll);

  // 3. Dettaglio Personaggio Selezionato
  const { 
    data: selectedCharacterData, 
    isLoading: isLoadingDetail,
    refetch: refetchCharacterDetail
  } = usePersonaggioDetail(selectedCharacterId, onLogout);

  /** Aggiorna IndexedDB (snapshot di gioco) dopo ogni sync online del personaggio. */
  useEffect(() => {
    if (!selectedCharacterId || typeof navigator === 'undefined' || !navigator.onLine) {
      return undefined;
    }
    if (!selectedCharacterData) {
      return undefined;
    }
    let cancelled = false;
    (async () => {
      try {
        const snap = await getPersonaggioGameState(selectedCharacterId, onLogout);
        if (!cancelled && snap) {
          await putOfflineGameStateSnapshot(selectedCharacterId, snap);
        }
      } catch {
        /* rete / auth: non bloccare la UI */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [selectedCharacterId, selectedCharacterData, onLogout]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        await postEventoPremiApplica(onLogout);
        if (!cancelled) {
          await refetchPersonaggiList();
          if (selectedCharacterId) {
            await refetchCharacterDetail();
          }
          try {
            const stato = await getGiocoEventoStato(onLogout);
            if (stato && typeof stato === 'object') {
              setGiocoEventoStato({
                evento_aperto: !!stato.evento_aperto,
                evento_titolo: stato.evento_titolo || null,
                azioni_live_abilitate: !!stato.azioni_live_abilitate,
                bypass_evento_gate: !!stato.bypass_evento_gate,
                transazioni_giocatore_abilitate: !!stato.transazioni_giocatore_abilitate,
                nodo_scan_abilitato: !!stato.nodo_scan_abilitato,
                allibratore_codici_abilitati: !!stato.allibratore_codici_abilitati,
              });
            }
          } catch {
            /* noop */
          }
        }
      } catch {
        /* Nessun premio applicabile o errore rete: non bloccare l'app */
      }
    })();
    return () => {
      cancelled = true;
    };
    // Eseguito al mount del provider (es. dopo login o refresh): idempotente lato server.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- evita re-run ad ogni cambio refetch RQ
  }, [onLogout]);

  // 4. Dati Lazy Loading (Estraiamo anche i refetch)
  const { 
      data: acquirableSkills = [], 
      refetch: refetchSkills 
  } = useAcquirableSkills(selectedCharacterId, onLogout);

  const { 
      data: acquirableInfusioni = [], 
      refetch: refetchInfusioni 
  } = useAcquirableInfusioni(selectedCharacterId, onLogout);

  const { 
      data: acquirableTessiture = [], 
      refetch: refetchTessiture 
  } = useAcquirableTessiture(selectedCharacterId, onLogout);

  const { 
      data: acquirableCerimoniali = [], 
      refetch: refetchCerimoniali 
  } = useAcquirableCerimoniali(selectedCharacterId, onLogout);

  // --- LOGICA SELEZIONE AUTOMATICA PG ---
  useEffect(() => {
    if (!selectedCharacterId && personaggiList.length > 0) {
        const preferredId = preferredCharacterId || localStorage.getItem('kor35_preferred_char_id');
        const lastId = localStorage.getItem('kor35_last_char_id');
        const targetId = (preferredId && personaggiList.some(p => p.id.toString() === preferredId))
                         ? preferredId
                         : ((lastId && personaggiList.some(p => p.id.toString() === lastId))
                           ? lastId
                           : personaggiList[0].id);
        setSelectedCharacterId(targetId);
    }
  }, [personaggiList, selectedCharacterId, preferredCharacterId]);

  useEffect(() => {
    if (!preferredCharacterId) return;
    const exists = personaggiList.some((p) => p.id.toString() === preferredCharacterId.toString());
    if (!exists) {
      setPreferredCharacterId('');
      localStorage.removeItem('kor35_preferred_char_id');
    }
  }, [personaggiList, preferredCharacterId]);

  useEffect(() => {
    let mounted = true;
    const loadPreferredFromServer = async () => {
      try {
        const data = await getPreferredPersonaggio(onLogout);
        const serverPreferred = data?.preferred_personaggio_id;
        if (!mounted || !serverPreferred) return;
        const normalized = String(serverPreferred);
        setPreferredCharacterId(normalized);
        localStorage.setItem('kor35_preferred_char_id', normalized);
      } catch (err) {
        // fallback locale: nessun blocco UI
      }
    };
    loadPreferredFromServer();
    return () => {
      mounted = false;
    };
  }, [onLogout]);

  // --- AZIONI CONTEXT ---
  const handleSelectCharacter = useCallback(async (id) => {
    const normalizedId = id ? String(id) : '';
    if (!normalizedId) {
      setSelectedCharacterId('');
      localStorage.removeItem('kor35_last_char_id');
      return;
    }

    const target = personaggiList.find((p) => String(p.id) === normalizedId);
    const targetCampaignId = target?.campagna ? String(target.campagna) : null;
    const targetCampaign = targetCampaignId
      ? campaigns.find((c) => String(c.id) === targetCampaignId)
      : null;

    if (
      targetCampaign?.slug &&
      normCampaignSlug(targetCampaign.slug) !== normCampaignSlug(activeCampaign)
    ) {
      try {
        const previousCampaign = campaigns.find(
          (c) => normCampaignSlug(c.slug) === normCampaignSlug(activeCampaign)
        );
        await validateActiveCampaign(targetCampaign.slug, onLogout);
        setActiveCampaign(setActiveCampaignSlug(targetCampaign.slug));
        await queryClient.invalidateQueries();
        setNotification({
          titolo: 'Campagna aggiornata',
          testo: `Cambio automatico da <strong>${previousCampaign?.nome || activeCampaign}</strong> a <strong>${targetCampaign.nome}</strong> per aprire ${target?.nome || 'il personaggio'} in contesto corretto.`,
          mittente: 'Sistema',
        });
      } catch {
        // Se la campagna non è valida/accessibile, lasciamo la campagna corrente.
      }
    }

    setSelectedCharacterId(normalizedId);
    localStorage.setItem('kor35_last_char_id', normalizedId);
  }, [personaggiList, campaigns, activeCampaign, onLogout, queryClient]);

  const setPreferredCharacter = useCallback((id) => {
    const persist = async (value) => {
      try {
        await setPreferredPersonaggio(value || null, onLogout);
      } catch (err) {
        // fallback locale: l'utente mantiene la preferenza sul dispositivo corrente
      }
    };

    if (!id) {
      setPreferredCharacterId('');
      localStorage.removeItem('kor35_preferred_char_id');
      persist(null);
      return;
    }
    const normalized = String(id);
    setPreferredCharacterId(normalized);
    localStorage.setItem('kor35_preferred_char_id', normalized);
    persist(Number(normalized));
  }, [onLogout]);

  const changeActiveCampaign = useCallback(async (slug) => {
    const normalized = setActiveCampaignSlug(slug);
    await validateActiveCampaign(normalized, onLogout);
    setActiveCampaign(normalized);
    setSelectedCharacterId('');
    setPreferredCharacterId('');
    localStorage.removeItem('kor35_last_char_id');
    localStorage.removeItem('kor35_preferred_char_id');
    await queryClient.invalidateQueries();
  }, [onLogout, queryClient]);

  // *** CORREZIONE CRUCIALE ***
  // Invalidazione + refetch esplicito della query personaggio così la UI (timer creazioni
  // consumabili, pulsante "Aggiungi a inventario") si aggiorna subito senza ricaricare la pagina.
  const refreshCharacterData = useCallback(async () => {
    if (selectedCharacterId) {
      const cId = selectedCharacterId;
      await Promise.all([
        queryClient.cancelQueries({ queryKey: ['personaggio', cId] }),
        queryClient.cancelQueries({ queryKey: ['abilita_acquistabili', cId] }),
        queryClient.cancelQueries({ queryKey: ['infusioni_acquistabili', cId] }),
        queryClient.cancelQueries({ queryKey: ['tessiture_acquistabili', cId] }),
        queryClient.cancelQueries({ queryKey: ['cerimoniali_acquistabili', cId] }),
      ]);

      // Soft sync: fetch reale backend e update cache senza svuotarla (evita flicker).
      const [personaggio, abilita, infusioni, tessiture, cerimoniali] = await Promise.all([
        getPersonaggioDetail(cId, onLogout),
        getAcquirableSkills(onLogout, cId),
        getAcquirableInfusioni(cId),
        getAcquirableTessiture(cId),
        getAcquirableCerimoniali(cId, onLogout),
      ]);

      queryClient.setQueryData(['personaggio', cId], personaggio);
      queryClient.setQueryData(['abilita_acquistabili', cId], abilita);
      queryClient.setQueryData(['infusioni_acquistabili', cId], infusioni);
      queryClient.setQueryData(['tessiture_acquistabili', cId], tessiture);
      queryClient.setQueryData(['cerimoniali_acquistabili', cId], cerimoniali);

      // Evita doppio roundtrip: i dati sono gia stati appena sincronizzati via fetch manuale.
      // Le mutation/hook invalidano comunque quando serve una riallineamento successivo.
    } else {
      await Promise.all([
        refetchSkills(),
        refetchInfusioni(),
        refetchTessiture(),
        refetchCerimoniali(),
        refetchCharacterDetail(),
      ]);
    }
  }, [selectedCharacterId, queryClient, refetchCharacterDetail, refetchSkills, refetchInfusioni, refetchTessiture, refetchCerimoniali]);

  // Tornando alla PWA / scheda (es. dopo modifiche dallo smartwatch) allinea i dati se il WS era in pausa.
  useEffect(() => {
    const onVisibility = () => {
      if (document.visibilityState !== 'visible' || !selectedCharacterId) return;
      refreshCharacterData();
    };
    document.addEventListener('visibilitychange', onVisibility);
    return () => document.removeEventListener('visibilitychange', onVisibility);
  }, [selectedCharacterId, refreshCharacterData]);

  const fetchPersonaggi = useCallback(() => {
    return refetchPersonaggiList();
  }, [refetchPersonaggiList]);

  const toggleViewAll = () => setViewAll(prev => !prev);

  // --- GESTIONE MESSAGGI ---
  const [userMessages, setUserMessages] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const toggleReadInProgress = useRef(new Set()); // Lock per prevenire chiamate duplicate

  const fetchUserMessages = useCallback(async (charId) => {
    if (!charId) return;
    try {
      const rawMsgs = await getMessages(charId, onLogout);
      const msgs = (rawMsgs || []).map(msg => ({
          ...msg,
          letto: msg.letto  // Usa direttamente il campo 'letto' dal serializer
      }));
      const sorted = (msgs || []).sort((a, b) => {
        if (a.letto !== b.letto) return a.letto ? 1 : -1;
        return new Date(b.data_invio) - new Date(a.data_invio);
      });
      setUserMessages(sorted);
      setUnreadCount(sorted.filter(m => !m.letto).length);
    } catch (err) { console.error("Err msg:", err); }
  }, [onLogout]);

  useEffect(() => {
    if (selectedCharacterId) fetchUserMessages(selectedCharacterId);
  }, [selectedCharacterId, fetchUserMessages]);

  const handleMarkAsRead = async (msgId) => {
      setUserMessages(prev => prev.map(m => m.id === msgId ? { ...m, letto: true } : m)); 
      setUnreadCount(prev => Math.max(0, prev - 1));
      try { await markMessageAsRead(msgId, selectedCharacterId, onLogout); } 
      catch (e) { fetchUserMessages(selectedCharacterId); }
  };

  const handleToggleRead = async (msgId) => {
      // Previeni chiamate duplicate
      if (toggleReadInProgress.current.has(msgId)) {
          console.log('Toggle già in corso per messaggio', msgId);
          return;
      }
      
      const msg = userMessages.find(m => m.id === msgId);
      if (!msg) return;
      
      // Aggiungi al set di operazioni in corso
      toggleReadInProgress.current.add(msgId);
      
      const newStatus = !msg.letto;
      console.log(`Toggle read per messaggio ${msgId}: ${msg.letto} -> ${newStatus}`);
      
      // Aggiorna ottimisticamente
      setUserMessages(prev => prev.map(m => m.id === msgId ? { ...m, letto: newStatus } : m)); 
      setUnreadCount(prev => newStatus ? Math.max(0, prev - 1) : prev + 1);
      
      try { 
          await fetchAuthenticated(`/api/personaggi/api/messaggi/${msgId}/toggle_letto/`, {
              method: 'POST',
              body: JSON.stringify({ personaggio_id: selectedCharacterId })
          }, onLogout);
          
          // Ricarica dal server DOPO un breve delay per permettere al DB di aggiornarsi
          setTimeout(async () => {
              console.log('Ricaricando messaggi dopo toggle...');
              await fetchUserMessages(selectedCharacterId);
              // Rimuovi dal set dopo il reload
              toggleReadInProgress.current.delete(msgId);
          }, 300);
      } 
      catch (e) { 
          console.error('Errore toggle read:', e);
          // In caso di errore, ricarica subito per ripristinare lo stato corretto
          fetchUserMessages(selectedCharacterId);
          toggleReadInProgress.current.delete(msgId);
      }
  };

  const handleDeleteMessage = async (msgId) => {
      if(!window.confirm("Cancellare messaggio?")) return;
      setUserMessages(prev => prev.filter(m => m.id !== msgId)); 
      try { await deleteMessage(msgId, selectedCharacterId, onLogout); } 
      catch (e) { fetchUserMessages(selectedCharacterId); }
  };

  // --- ADMIN & NOTIFICHE ---
  const [adminPendingCount, setAdminPendingCount] = useState(0);
  useEffect(() => {
      if (isGlobalSuperuser && !viewAll) {
          const check = async () => {
              try { const d = await getAdminPendingProposalsCount(onLogout); setAdminPendingCount(d.count); } 
              catch (e) {}
          };
          check();
          const i = setInterval(check, 60000);
          return () => clearInterval(i);
      }
  }, [isGlobalSuperuser, viewAll, onLogout]);

  const subscribeToPush = useCallback(async () => {
    const result = await activateWebPush();
    if (!result.ok) return result;
    try {
      await saveWebPushSubscription(result.subscription, onLogout);
      return { ok: true };
    } catch (e) {
      console.error('WebPush Error:', e);
      return {
        ok: false,
        reason: 'error',
        message: e?.message || 'Errore nel salvataggio della sottoscrizione.',
      };
    }
  }, [onLogout]);

  // Re-sottoscrive in silenzio solo se l'utente ha già concesso il permesso.
  useEffect(() => {
    if (!selectedCharacterId || !isWebPushSupported()) return;
    if (Notification.permission !== 'granted') return;
    subscribeToPush();
  }, [selectedCharacterId, subscribeToPush]);

  const [notification, setNotification] = useState(null);
  const ws = useRef(null);
  useEffect(() => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${wsProtocol}//${window.location.host}/ws/notifications/`;
    if (ws.current) ws.current.close();
    ws.current = new WebSocket(wsUrl);
    ws.current.onmessage = (e) => {
      try {
        const d = JSON.parse(e.data);
        const inner = d.type === 'notification' ? d.payload : d;
        const action = inner?.action;
        const payload = inner?.payload || inner;

        if (action === 'TIMER_SYNC' && payload) {
            updateTimerState(payload);
        }

        if (action === 'WATCH_SYNC' && payload?.personaggio_id && String(payload.personaggio_id) === String(selectedCharacterId)) {
            queryClient.invalidateQueries({ queryKey: ['personaggio', String(selectedCharacterId)] });
        }

        if (action === 'TIMER_INNESCO_SYNC' && payload) {
            const ids = payload.recipient_personaggio_ids || [];
            const myId = parseInt(selectedCharacterId, 10);
            if (!ids.length || ids.includes(myId)) {
              updateTimerState({
                nome: payload.nome,
                data_fine: payload.data_fine,
                alert_suono: true,
                notifica_push: true,
                messaggio_in_app: true,
              });
            }
        }

        if (action === 'DUELLO_INVITO' && inner?.destinatario_personaggio_id) {
          const myId = parseInt(selectedCharacterId, 10);
          if (String(inner.destinatario_personaggio_id) === String(myId)) {
            const titolo = 'Sfida duello carte';
            const testo = `${inner.sfidante_nome || 'Un avversario'} ti ha sfidato! Apri la tab Carte per accettare la partita.`;
            setNotification({ titolo, testo, tipo: 'INDV' });
            sendSystemNotification(titolo, testo);
          }
        }

        if (
          (action === 'DUELLO_LOBBY' || action === 'DUELLO_PREMATCH' || action === 'DUELLO_INIZIO')
          && inner?.destinatario_personaggio_id
        ) {
          const myId = parseInt(selectedCharacterId, 10);
          if (String(inner.destinatario_personaggio_id) === String(myId)) {
            const titolo = action === 'DUELLO_LOBBY'
              ? 'Scontro carte'
              : action === 'DUELLO_PREMATCH'
                ? 'Pre-partita carte'
                : 'Duello iniziato';
            const testo = action === 'DUELLO_LOBBY'
              ? `${inner.sfidato_nome || 'Un avversario'} si è unito al tuo scontro! Apri la tab Carte.`
              : action === 'DUELLO_PREMATCH'
                ? `${inner.da_nome || 'Il tuo avversario'} ha aggiornato la pre-partita. Apri la tab Carte.`
                : `La partita contro ${inner.avversario_nome || 'l\'avversario'} è iniziata! Apri la tab Carte.`;
            setNotification({ titolo, testo, tipo: 'INDV' });
            sendSystemNotification(titolo, testo);
            window.dispatchEvent(new CustomEvent('kor35:duello-carte', { detail: inner }));
          }
        }

        if (d.type === 'notification') {
           const msg = d.payload;
           if (!msg || msg.action === 'TIMER_SYNC' || msg.action === 'TIMER_INNESCO_SYNC') {
             return;
           }
           const myId = parseInt(selectedCharacterId);
           if (msg.tipo === 'BROAD' || (msg.tipo === 'INDV' && msg.destinatario_id === myId) || msg.tipo === 'GROUP') {
              setNotification(msg);
              sendSystemNotification(msg.titolo, msg.testo.replace(/<[^>]+>/g, ''));
              fetchUserMessages(selectedCharacterId);
              queryClient.invalidateQueries(['personaggio', selectedCharacterId]);
           }
        }
      } catch (err) {}
    };
    return () => { if (ws.current) ws.current.close(); };
  }, [selectedCharacterId, fetchUserMessages, queryClient, updateTimerState]);


  // --- VALUE DEL CONTEXT ---
  const value = {
    onLogout,
    personaggiList,
    punteggiList,
    statisticaContainers,
    selectedCharacterId,
    preferredCharacterId,
    
    characterData: selectedCharacterData,
    selectedCharacterData,
    
    acquirableSkills,
    acquirableInfusioni,
    acquirableTessiture,
    acquirableCerimoniali,

    activeTimers,
    setActiveTimers,
    updateTimerState,
    removeTimerState,
    
    isLoading: isLoadingList || isLoadingDetail || isLoadingPunteggi || isLoadingStatContainers || mutatingCount > 0,
    isLoadingList,
    isLoadingDetail,
    isSyncing: mutatingCount > 0,
    
    selectCharacter: handleSelectCharacter,
    setPreferredCharacter,
    refreshCharacterData,
    fetchPersonaggi, 
    
    loadSkillsOnDemand: () => {}, 
    loadInfusioniOnDemand: () => {},
    loadTessitureOnDemand: () => {},

    isCampaignMaster,
    isCampaignHeadMaster,
    isCampaignStaffer,
    isCampaignRedactor,
    activeCampaignRole,
    staffWorkMode,
    setStaffWorkMode,
    campaigns,
    activeCampaign,
    changeActiveCampaign,
    /** Superuser Django (bypass globale). Alias legacy per il codice esistente. */
    isGlobalSuperuser,
    isAdmin: isGlobalSuperuser,
    isDjangoStaff,
    canUseWizardTest,
    viewAll,
    toggleViewAll,
    adminPendingCount,
    userMessages,
    unreadCount,
    fetchUserMessages,
    handleMarkAsRead,
    handleToggleRead,
    handleDeleteMessage,
    subscribeToPush,
    isWebPushSupported,
    giocoEventoStato,
    eventoAperto: !!giocoEventoStato.evento_aperto,
    azioniLiveAbilitate: !!giocoEventoStato.azioni_live_abilitate,
    bypassEventoGate: !!giocoEventoStato.bypass_evento_gate,
    transazioniGiocatoreAbilitate: !!giocoEventoStato.azioni_live_abilitate,
    nodoScanAbilitato: !!giocoEventoStato.nodo_scan_abilitato,
    allibratoreCodiciAbilitati: !!giocoEventoStato.allibratore_codici_abilitati,
  };

  return (
    <CharacterContext.Provider value={value}>
      {children}
      <NotificationPopup notification={notification} onClose={() => setNotification(null)} />
    </CharacterContext.Provider>
  );
};

export const useCharacter = () => {
  const context = useContext(CharacterContext);
  if (!context) throw new Error('useCharacter deve essere usato dentro un CharacterProvider');
  return context;
};