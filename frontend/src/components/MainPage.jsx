import React, { useState, useEffect, useMemo, useCallback, memo } from 'react';
// --- LOGICA PWA ---
import { Link, useLocation, useNavigate } from 'react-router-dom';

import HomeTab from './HomeTab.jsx';
import QrTab from './QrTab.jsx';
import QrResultModal from './QrResultModal.jsx';
import { useCharacter } from './CharacterContext';
import { TimerOverlay } from './TimerOverlay';
import { fetchAuthenticated, fetchStaffMessages, socialGetNotifications, getArcanaPasswordStatus } from '../api'; // <-- [MODIFICA] Import fetchStaffMessages
import packageInfo from '../../package.json';

import { 
    Home, QrCode, Zap, TestTube2, Scroll, LogOut, Mail, Backpack, 
    Menu, X, UserCog, RefreshCw, Filter, DownloadCloud, ScrollText, 
    ArrowRightLeft, Gamepad2, Loader2, ExternalLink, Tag, Users, Sparkles,
    Pin, PinOff, Briefcase, ClipboardCheck, Globe, ChevronRight, Package, Star,
    Key, HelpCircle // <-- [MODIFICA] Icona HelpCircle aggiunta
} from 'lucide-react';

import AbilitaTab from './AbilitaTab.jsx';
import MessaggiTab from './MessaggiTab.jsx';
import InfusioniTab from './InfusioniTab.jsx'; 
import TessitureTab from './TessitureTab.jsx';
import ConsumabiliTab from './ConsumabiliTab.jsx';
import CerimonialiTab from './CerimonialiTab.jsx'; 
import AdminMessageTab from './AdminMessageTab.jsx';
import InventoryTab from './InventoryTab.jsx';
import LogViewer from './LogViewer.jsx';
import TransazioniViewer from './TransazioniViewer.jsx';
import GameTab from './GameTab.jsx';
import JobRequestsWidget from './JobRequestsWidget.jsx'; 
import PersonaggiTab from './PersonaggiTab.jsx';
import StartPage from './StartPage.jsx';
import RazzaModal, { stripRazzaPrefix } from './RazzaCollapsible';

// --- [MODIFICA] Import Modale Password ---
import PasswordChangeModal from './PasswordChangeModal.jsx';

// --- [MODIFICA] Import Modale Wiki Help ---
import WikiHelpModal from './WikiHelpModal.jsx';

// VERSIONE APP
const APP_VERSION = packageInfo.version;
const BUILD_VERSION = (import.meta.env.VITE_BUILD_VERSION || '').trim();
const BUILD_SHA = (import.meta.env.VITE_BUILD_SHA || '').trim();

// CONFIGURAZIONE TAB DISPONIBILI
const AVAILABLE_TABS = [
    { id: 'inventario', label: 'Zaino', icon: Backpack, component: InventoryTab },
    { id: 'abilita', label: 'Abilità', icon: Zap, component: AbilitaTab },
    { id: 'tessiture', label: 'Tessiture', icon: Scroll, component: TessitureTab },
    { id: 'infusioni', label: 'Infusioni', icon: TestTube2, component: InfusioniTab },
    { id: 'cerimoniali', label: 'Cerimoniali', icon: Users, component: CerimonialiTab },
    { id: 'consumabili', label: 'Consumabili', icon: Package, component: ConsumabiliTab },
    { id: 'qr', label: 'Scanner', icon: QrCode, component: QrTab },
    { id: 'messaggi', label: 'Messaggi', icon: Mail, component: MessaggiTab },
    { id: 'logs', label: 'Diario', icon: ScrollText, component: LogViewer },
    { id: 'transazioni', label: 'Transazioni', icon: ArrowRightLeft, component: TransazioniViewer },
    { id: 'personaggi', label: 'Personaggi', icon: Users, component: PersonaggiTab },
];

const DEFAULT_SHORTCUTS = ['inventario', 'abilita', 'messaggi', 'qr'];

// Mappatura tab -> slug pagina wiki
// Nota: gli slug sono unici nel database, le pagine sono organizzate gerarchicamente tramite parent
const TAB_TO_WIKI_SLUG = {
    'inventario': 'inventario',
    'abilita': 'abilita',
    'tessiture': 'tessiture',
    'infusioni': 'infusioni',
    'cerimoniali': 'cerimoniali',
    'messaggi': 'messaggi',
    'qr': 'scanner-qr',
    'logs': 'diario',
    'transazioni': 'transazioni',
    'personaggi': 'gestione-personaggio',
    'social': 'social',
    'consumabili': 'consumabili',
    'home': 'gestione-personaggio',
    'game': 'navigazione-app',
};

const MainPage = ({ token, onLogout, onSwitchToMaster }) => {
  const location = useLocation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('game'); 
  const [qrResultData, setQrResultData] = useState(null);
  const [isMenuOpen, setIsMenuOpen] = useState(false);
  
  // --- [MODIFICA] Stato per Modale Password e Notifiche Staff ---
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [forceSetLocalPassword, setForceSetLocalPassword] = useState(false);
  const [showLocalPasswordReminder, setShowLocalPasswordReminder] = useState(false);
  const [staffUnreadCount, setStaffUnreadCount] = useState(0);
  const [socialUnreadCount, setSocialUnreadCount] = useState(0);
  
  // --- [MODIFICA] Stato per Modale Wiki Help ---
  const [isWikiHelpOpen, setIsWikiHelpOpen] = useState(false);
  const [currentWikiSlug, setCurrentWikiSlug] = useState(null);
  const [messageComposeTarget, setMessageComposeTarget] = useState(null);
  const [nowTs, setNowTs] = useState(Date.now());
  
  // STATO SHORTCUTS (Default salvagente)
  const [userShortcuts, setUserShortcuts] = useState(DEFAULT_SHORTCUTS);

  // --- LOGICA PWA (temporaneamente disattivata per stabilità runtime) ---
  const needRefresh = false;
  const setNeedRefresh = () => {};
  const updateServiceWorker = async () => {
    try {
      if ('serviceWorker' in navigator) {
        const regs = await navigator.serviceWorker.getRegistrations();
        await Promise.all(regs.map(r => r.unregister()));
      }
    } catch (e) {
      // noop
    }
    window.location.reload();
  };

  // Safety net: rimuove eventuali Service Worker già presenti per evitare cache incoerente dei chunk.
  useEffect(() => {
    let mounted = true;
    const cleanupServiceWorkers = async () => {
      try {
        if (!('serviceWorker' in navigator)) return;
        const regs = await navigator.serviceWorker.getRegistrations();
        if (!mounted) return;
        await Promise.all(regs.map(r => r.unregister()));
      } catch (e) {
        // noop
      }
    };
    cleanupServiceWorkers();
    return () => {
      mounted = false;
    };
  }, []);

  // --- COOLDOWN FURTO ---
  const [stealCooldownEnd, setStealCooldownEnd] = useState(0);
  const [cooldownTimer, setCooldownTimer] = useState(0);
  const isStealingOnCooldown = Date.now() < stealCooldownEnd;

  useEffect(() => {
    if (isStealingOnCooldown) {
      const updateTimer = () => {
        const secondsLeft = Math.ceil((stealCooldownEnd - Date.now()) / 1000);
        setCooldownTimer(secondsLeft > 0 ? secondsLeft : 0);
      };
      updateTimer();
      const interval = setInterval(updateTimer, 1000);
      return () => clearInterval(interval);
    } else {
      setCooldownTimer(0);
    }
  }, [stealCooldownEnd, isStealingOnCooldown]);

  const handleStealSuccess = () => {
    setStealCooldownEnd(Date.now() + 30000);
    closeQrModal();
  };

  // --- CONTEXT ---
  const {
    personaggiList,
    selectedCharacterId,
    preferredCharacterId,
    selectedCharacterData,
    refreshCharacterData,
    punteggiList,
    activeTimers,      
    removeTimerState,  
    selectCharacter,
    setPreferredCharacter,
    fetchPersonaggi,
    isLoading,
    isAdmin,
    viewAll,
    toggleViewAll,
    adminPendingCount,
    unreadCount, 
    campaigns,
    activeCampaign,
    changeActiveCampaign,
    isCampaignMaster,
  } = useCharacter();

  const [razzaModalOpen, setRazzaModalOpen] = useState(false);

  const auraInnataRecord = useMemo(
    () => (punteggiList || []).find((p) => p.tipo === 'AU' && String(p.sigla || '').toUpperCase() === 'AIN'),
    [punteggiList]
  );

  const razzaHeader = useMemo(() => {
    const isTrattoInnita = (ab) =>
      ab?.is_tratto_aura &&
      ab?.aura_riferimento &&
      String(ab.aura_riferimento.sigla || '').toUpperCase() === 'AIN';
    const abilita = selectedCharacterData?.abilita_possedute || [];
    const arch = abilita.find(
      (ab) => isTrattoInnita(ab) && (ab.livello_riferimento === 0 || ab.livello_riferimento === 1)
    );
    const forma = abilita.find((ab) => isTrattoInnita(ab) && ab.livello_riferimento === 2);
    const archLabel = arch ? stripRazzaPrefix(arch.nome) : 'Umano';
    const formaLabel = forma ? stripRazzaPrefix(forma.nome) : null;
    const full = formaLabel ? `${archLabel} ${formaLabel}` : archLabel;
    return { full, canEdit: !!selectedCharacterData?.can_edit_razza };
  }, [selectedCharacterData]);

  useEffect(() => {
    const onOpen = () => {
      if (razzaHeader?.canEdit) setRazzaModalOpen(true);
    };
    window.addEventListener('kor35:open-razza-modal', onOpen);
    return () => window.removeEventListener('kor35:open-razza-modal', onOpen);
  }, [razzaHeader]);

  // CARICAMENTO INIZIALE
  useEffect(() => {
    if (token) fetchPersonaggi();
  }, [token, fetchPersonaggi]);

  const isValidTabId = useCallback((tabId) => {
    if (!tabId) return false;
    if (tabId === 'game' || tabId === 'home' || tabId === 'admin_msg') return true;
    return AVAILABLE_TABS.some(t => t.id === tabId);
  }, []);

  // Legge il tab dalla URL (deep-link): /app?tab=personaggi
  // NB: solo in lettura. Evitiamo sync bidirezionale URL<->state
  // per prevenire loop di navigazione in produzione.
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const urlTab = params.get('tab');
    if (isValidTabId(urlTab)) {
      setActiveTab(urlTab);
    }
  }, [location.search, isValidTabId]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const composeTargetId = params.get('compose_target_id');
    if (!composeTargetId) return;
    const composeTargetName = params.get('compose_target_nome');
    setMessageComposeTarget({
      id: composeTargetId,
      nome: composeTargetName || `PG ${composeTargetId}`,
      isStaff: false,
    });
  }, [location.search]);

  // --- [MODIFICA] POLLING MESSAGGI STAFF (Solo per Staff) ---
  useEffect(() => {
    const revivalActiveNow =
      String(selectedCharacterData?.impostazioni_ui?.rianimazione_state?.status || '').toLowerCase() === 'counting';
    if (!revivalActiveNow) return undefined;
    const timerId = setInterval(() => setNowTs(Date.now()), 1000);
    return () => clearInterval(timerId);
  }, [selectedCharacterData]);

  useEffect(() => {
    let interval;
    if (isCampaignMaster) {
        const checkStaffMessages = async () => {
            try {
                // Recupera messaggi staff e conta quelli non letti (assumendo che l'API restituisca una lista)
                // Se l'API supporta il conteggio diretto è meglio, altrimenti filtriamo lato client
                const msgs = await fetchStaffMessages(onLogout);
                if (Array.isArray(msgs)) {
                    const unread = msgs.filter(m => !m.letto).length;
                    setStaffUnreadCount(unread);
                }
            } catch (e) {
                console.error("Errore check messaggi staff", e);
            }
        };
        
        checkStaffMessages();
        // Controllo ogni 60 secondi
        interval = setInterval(checkStaffMessages, 60000);
    }
    return () => clearInterval(interval);
  }, [isCampaignMaster, onLogout]);

  useEffect(() => {
    let interval;
    if (!selectedCharacterId) {
      setSocialUnreadCount(0);
      return undefined;
    }
    const notificationsSeenKey = `social_notifications_seen_at:${selectedCharacterId}`;
    const checkSocialNotifications = async () => {
      try {
        const since = localStorage.getItem(notificationsSeenKey);
        const data = await socialGetNotifications(selectedCharacterId, onLogout, {
          limit: 30,
          since: since || undefined,
        });
        const unread = Number(data?.unread_count || 0);
        setSocialUnreadCount(Number.isFinite(unread) ? unread : 0);
      } catch (e) {
        console.error('Errore check notifiche social', e);
      }
    };
    checkSocialNotifications();
    interval = setInterval(checkSocialNotifications, 60000);
    return () => clearInterval(interval);
  }, [selectedCharacterId, onLogout]);

  useEffect(() => {
    let mounted = true;
    const loadArcanaPasswordStatus = async () => {
      try {
        const status = await getArcanaPasswordStatus(onLogout);
        if (!mounted) return;
        const shouldShow = !!status?.show_reminder;
        setShowLocalPasswordReminder(shouldShow);
        setForceSetLocalPassword(shouldShow);
      } catch (_err) {
        if (mounted) {
          setShowLocalPasswordReminder(false);
          setForceSetLocalPassword(false);
        }
      }
    };
    loadArcanaPasswordStatus();
    return () => {
      mounted = false;
    };
  }, [token, onLogout]);

  // Nota: non forziamo piu il tab "personaggi" quando manca selectedCharacterId.
  // Il rendering dei tab gestisce gia il fallback "Nessun Personaggio Selezionato"
  // evitando loop di navigazione URL/tab.

  // CARICAMENTO PREFERENZE UI DAL DB
  useEffect(() => {
      if (selectedCharacterData) {
          if (selectedCharacterData.impostazioni_ui?.shortcuts) {
              setUserShortcuts(selectedCharacterData.impostazioni_ui.shortcuts);
          } else {
              setUserShortcuts(DEFAULT_SHORTCUTS);
          }
      }
  }, [selectedCharacterData]);

  // SALVATAGGIO PREFERENZE
  const toggleShortcut = async (tabId) => {
      if (!selectedCharacterId) return;

      const oldShortcuts = [...userShortcuts];
      let newShortcuts;

      if (userShortcuts.includes(tabId)) {
          newShortcuts = userShortcuts.filter(id => id !== tabId);
      } else {
          if (userShortcuts.length >= 4) {
              alert("Puoi fissare al massimo 4 schede nella barra inferiore.");
              return;
          }
          newShortcuts = [...userShortcuts, tabId];
      }

      setUserShortcuts(newShortcuts);

      try {
          await fetchAuthenticated(`/api/personaggi/api/personaggi/${selectedCharacterId}/`, 
            {
              method: 'PATCH',
              headers: {
                  'Content-Type': 'application/json'
              },
              body: JSON.stringify({
                  impostazioni_ui: { 
                      ...(selectedCharacterData.impostazioni_ui || {}),
                      shortcuts: newShortcuts 
                  }
              })
            }, 
            onLogout
          );
      } catch (error) {
          console.error("Errore salvataggio shortcuts", error);
          setUserShortcuts(oldShortcuts);
          alert("Impossibile salvare le preferenze sul server.");
      }
  };

  const handleScanSuccess = useCallback((jsonData) => setQrResultData(jsonData), []);
  const closeQrModal = useCallback(() => setQrResultData(null), []);
  
  const handleMenuNavigation = useCallback((tabName) => {
    setActiveTab(tabName);
    setIsMenuOpen(false);
  }, []);

  // --- [MODIFICA] Funzione per aprire il modal di aiuto ---
  const openWikiHelp = useCallback(() => {
    const wikiSlug = TAB_TO_WIKI_SLUG[activeTab];
    if (wikiSlug) {
      setCurrentWikiSlug(wikiSlug);
      setIsWikiHelpOpen(true);
    }
  }, [activeTab]);

  const closeWikiHelp = useCallback(() => {
    setIsWikiHelpOpen(false);
    setCurrentWikiSlug(null);
  }, []);

  // --- NOTIFICHE (Memoized) ---
  const notificationState = useMemo(() => {
    const hasAdminNotif = isAdmin && adminPendingCount > 0;
    const hasMsgNotif = unreadCount > 0;
    const jobsCount = selectedCharacterData?.lavori_pendenti_count || 0; 
    const hasJobNotif = jobsCount > 0; 
    const hasStaffMsgNotif = isCampaignMaster && staffUnreadCount > 0;
    
    return { hasAdminNotif, hasMsgNotif, hasJobNotif, hasStaffMsgNotif, jobsCount };
  }, [isAdmin, adminPendingCount, unreadCount, selectedCharacterData?.lavori_pendenti_count, isCampaignMaster, staffUnreadCount]);
  
  const { hasAdminNotif, hasMsgNotif, hasJobNotif, hasStaffMsgNotif } = notificationState;
  const comaState = selectedCharacterData?.impostazioni_ui?.coma_state || null;
  const rianimazioneState = selectedCharacterData?.impostazioni_ui?.rianimazione_state || null;
  const isComaLocked = !!selectedCharacterData && ['counting', 'paused'].includes(String(comaState?.status || '').toLowerCase());
  const comaStatus = String(comaState?.status || '').toLowerCase();
  const isRevivalActive = !!selectedCharacterData && String(rianimazioneState?.status || '').toLowerCase() === 'counting';
  const revivalEndMs = rianimazioneState?.end_at ? new Date(rianimazioneState.end_at).getTime() : 0;
  const revivalRemaining = Math.max(0, Math.ceil((revivalEndMs - nowTs) / 1000));
  const revivalMin = String(Math.floor(revivalRemaining / 60)).padStart(2, '0');
  const revivalSec = String(revivalRemaining % 60).padStart(2, '0');

  useEffect(() => {
    if (isComaLocked && activeTab !== 'game') {
      setActiveTab('game');
    }
  }, [isComaLocked, activeTab]);

  useEffect(() => {
    if (!selectedCharacterId && activeTab !== 'personaggi') {
      setActiveTab('personaggi');
    }
  }, [selectedCharacterId, activeTab]);

  useEffect(() => {
    if (activeTab === 'admin_msg' && !isCampaignMaster) {
      setActiveTab('home');
    }
  }, [activeTab, isCampaignMaster]);

  useEffect(() => {
    if (!selectedCharacterId) return undefined;

    const comaEndMs = comaState?.end_at ? new Date(comaState.end_at).getTime() : 0;
    const revivalEndMs = rianimazioneState?.end_at ? new Date(rianimazioneState.end_at).getTime() : 0;
    const now = Date.now();

    // Refresh solo quando serve davvero:
    // - alla fine del coma (per avviare rianimazione o morte)
    // - alla fine della rianimazione (per tornare alla UI normale con PV ripristinati)
    let nextTriggerMs = 0;
    if (isRevivalActive && revivalEndMs > now) {
      nextTriggerMs = revivalEndMs;
    } else if (
      isComaLocked &&
      String(comaState?.status || '').toLowerCase() === 'counting' &&
      comaEndMs > now
    ) {
      nextTriggerMs = comaEndMs;
    }

    if (!nextTriggerMs) return undefined;
    const waitMs = Math.max(300, nextTriggerMs - now + 350);
    const timeoutId = setTimeout(() => {
      refreshCharacterData();
    }, waitMs);
    return () => clearTimeout(timeoutId);
  }, [selectedCharacterId, isComaLocked, isRevivalActive, comaState, rianimazioneState, refreshCharacterData]);

  const renderTabContent = useCallback(() => {
    if (activeTab === 'home') return <HomeTab onLogout={onLogout} />;
    if (activeTab === 'game') return <GameTab onNavigate={handleMenuNavigation} />;
    if (activeTab === 'admin_msg') return <AdminMessageTab onLogout={onLogout} />;

    const tabDef = AVAILABLE_TABS.find(t => t.id === activeTab);
    if (tabDef) {
        const Component = tabDef.component;
        if (tabDef.id === 'personaggi') {
            return <StartPage onLogout={onLogout} onSwitchToMaster={onSwitchToMaster} />;
        }
        
        if (!selectedCharacterId && tabDef.id !== 'personaggi') {
            return (
                <div className="h-full flex flex-col items-center justify-center text-gray-500 gap-4 animate-fadeIn">
                    <Users size={64} className="opacity-20 animate-pulse"/>
                    <p className="text-lg font-bold">Nessun Personaggio Selezionato</p>
                    <button 
                        onClick={() => setActiveTab('personaggi')}
                        className="px-6 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-bold uppercase text-xs transition-all shadow-lg hover:shadow-indigo-500/20 active:scale-95"
                    >
                        Vai alla selezione
                    </button>
                </div>
            );
        }
        if (tabDef.id === 'qr') return <QrTab onScanSuccess={handleScanSuccess} onLogout={onLogout} isStealingOnCooldown={isStealingOnCooldown} cooldownTimer={cooldownTimer} />;
        if (tabDef.id === 'logs' || tabDef.id === 'transazioni') return <div className="p-4 h-full overflow-y-auto animate-fadeIn"><Component charId={selectedCharacterId} onLogout={onLogout} /></div>;
        
        if (tabDef.id === 'messaggi') {
            return (
                <Component
                    onLogout={onLogout}
                    composeTarget={messageComposeTarget}
                    onComposeTargetConsumed={() => setMessageComposeTarget(null)}
                />
            );
        }
        return <Component onLogout={onLogout} />;
    }
    return <HomeTab onLogout={onLogout} />;
  }, [activeTab, selectedCharacterId, isStealingOnCooldown, cooldownTimer, handleMenuNavigation, handleScanSuccess, onLogout]);

  // --- CONTENUTO MENU (render function, evita remount continui della sidebar) ---
  const renderMenuContent = () => (
    <div className="flex flex-col h-full overflow-hidden">
        {/* SELETTORE PERSONAGGIO E TAB */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4 custom-scrollbar">
            
            {/* 1. SELETTORE PERSONAGGIO */}
            <div className="bg-gray-700/30 p-3 rounded-lg border border-gray-700">
                <label className="block text-xs font-bold text-gray-400 uppercase mb-2">Campagna attiva</label>
                {(campaigns || []).length > 1 ? (
                    <select
                        className="w-full bg-gray-900 text-white p-2 rounded border border-gray-600 focus:border-indigo-500 outline-none text-sm mb-3"
                        value={activeCampaign || 'kor35'}
                        onChange={(e) => {
                            changeActiveCampaign(e.target.value);
                            setIsMenuOpen(false);
                        }}
                    >
                        {(campaigns || []).map(c => (
                            <option key={c.slug} value={c.slug}>
                                {c.nome} {c.ruolo === 'MASTER' ? '(Master)' : ''}
                            </option>
                        ))}
                    </select>
                ) : (
                    <div className="w-full bg-gray-900 text-gray-200 p-2 rounded border border-gray-700 text-sm mb-3">
                        {(campaigns && campaigns[0]?.nome) || 'Kor35'}
                    </div>
                )}
                <label className="block text-xs font-bold text-gray-400 uppercase mb-2">Cambia Personaggio</label>
                <select 
                    className="w-full bg-gray-900 text-white p-2 rounded border border-gray-600 focus:border-indigo-500 outline-none text-sm"
                    value={selectedCharacterId || ''}
                    onChange={(e) => {
                        selectCharacter(e.target.value);
                        setIsMenuOpen(false); 
                    }}
                >
                    {personaggiList.map(p => (
                        <option key={p.id} value={p.id}>
                            {p.nome} [{p.campagna_nome || 'Kor35'}] {String(preferredCharacterId || '') === String(p.id) ? '★ Preferito' : ''}
                        </option>
                    ))}
                </select>
                {!!selectedCharacterId && (
                    <label className="mt-2 inline-flex items-center gap-2 text-xs text-gray-300">
                        <input
                            type="checkbox"
                            checked={String(preferredCharacterId || '') === String(selectedCharacterId)}
                            onChange={(e) => {
                                if (e.target.checked) {
                                    setPreferredCharacter(selectedCharacterId);
                                } else {
                                    setPreferredCharacter('');
                                }
                            }}
                            className="w-4 h-4 rounded text-indigo-500 focus:ring-indigo-500"
                        />
                        Usa questo personaggio come preferito
                    </label>
                )}

                {/* 2. ADMIN VIEW ALL TOGGLE */}
                {isAdmin && (
                    <div className="mt-3 flex items-center justify-between pt-3 border-t border-gray-700">
                        <span className="text-sm text-gray-300 flex items-center gap-2">
                            <Filter size={16} /> Vedi tutti i PG
                        </span>
                        <button 
                            onClick={() => { toggleViewAll(); setIsMenuOpen(false); }}
                            className={`w-10 h-5 rounded-full relative transition-colors ${viewAll ? 'bg-green-600' : 'bg-gray-600'}`}
                        >
                            <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${viewAll ? 'left-6' : 'left-1'}`}></div>
                        </button>
                    </div>
                )}
            </div>

            {/* 3. LISTA TAB DI NAVIGAZIONE */}
            <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase font-bold px-1 mb-2 mt-2 flex justify-between items-center">
                    Menu Rapido 
                    <span className="text-[10px] font-normal normal-case opacity-70"><Pin size={10} className="inline"/> fissa in basso</span>
                </p>
                
                {AVAILABLE_TABS.map(tab => {
                    const isPinned = userShortcuts.includes(tab.id);
                    const isActive = activeTab === tab.id;
                    let badgeCount = 0;
                    let badgeColor = 'bg-gray-600';
                    
                    // Logica Badge
                    if (tab.id === 'messaggi') {
                        if (hasStaffMsgNotif) { // Priorità al verde staff
                            badgeCount = staffUnreadCount;
                            badgeColor = 'bg-green-500';
                        } else {
                            badgeCount = unreadCount; 
                            badgeColor = 'bg-purple-600';
                        }
                    }

                    return (
                        <div key={tab.id} className={`flex items-center justify-between p-2 rounded-lg transition-colors group ${isActive ? 'bg-indigo-900/40 border border-indigo-500/30' : 'hover:bg-gray-700/50 border border-transparent'}`}>
                            <button 
                                className="flex items-center gap-3 flex-1 text-left py-1"
                                onClick={() => handleMenuNavigation(tab.id)}
                            >
                                <tab.icon size={20} className={isActive ? "text-indigo-400" : "text-gray-400 group-hover:text-gray-200"} />
                                <span className={`${isActive ? "text-indigo-100 font-bold" : "text-gray-300 group-hover:text-white"}`}>
                                    {tab.label}
                                </span>
                                {badgeCount > 0 && (
                                    <span className={`ml-2 px-1.5 py-0.5 text-[10px] font-bold text-white rounded-full ${badgeColor}`}>
                                        {badgeCount}
                                    </span>
                                )}
                            </button>
                            
                            <button 
                                onClick={(e) => {
                                    e.stopPropagation();
                                    toggleShortcut(tab.id);
                                }}
                                className={`p-2 rounded-full transition-colors ${isPinned ? 'text-amber-400 hover:bg-amber-400/10' : 'text-gray-600 hover:text-gray-400'}`}
                            >
                                {isPinned ? <Pin size={16} fill="currentColor" /> : <PinOff size={16} />}
                            </button>
                        </div>
                    );
                })}

                {/* LINK WIKI PUBBLICA (Style Uniformato) */}
                <div className="h-px bg-gray-700 my-2 mx-1"></div>
                <Link 
                    to="/" 
                    className="flex items-center gap-3 p-3 rounded-lg hover:bg-gray-700/50 text-gray-300 hover:text-white transition-colors border border-transparent hover:border-gray-600"
                    title="Torna al sito pubblico"
                >
                    <Globe size={20} className="text-gray-400"/>
                    <span className="font-bold">Wiki Pubblica</span>
                    <ChevronRight size={14} className="ml-auto opacity-50"/>
                </Link>
                <button
                    type="button"
                    onClick={() => {
                      setIsMenuOpen(false);
                      navigate('/app/social');
                    }}
                    className="w-full flex items-center gap-3 p-3 rounded-lg hover:bg-gray-700/50 text-pink-200 hover:text-pink-100 transition-colors border border-pink-500/30"
                    title="Apri InstaFame"
                >
                    <Sparkles size={20} className="text-pink-300"/>
                    <span className="font-bold">InstaFame</span>
                    {socialUnreadCount > 0 && (
                      <span className="ml-auto px-1.5 py-0.5 text-[10px] font-bold text-white rounded-full bg-pink-600">
                        {socialUnreadCount > 99 ? '99+' : socialUnreadCount}
                      </span>
                    )}
                </button>
            </div>
        </div>

        {/* FOOTER (VERSIONE & UPDATE) */}
        <div className="p-4 border-t border-gray-700 bg-gray-900/80 shrink-0">
            <div className="flex justify-between items-center mb-3">
                <span className="text-xs text-gray-500 font-mono">
                  v{APP_VERSION}
                  {(BUILD_VERSION || BUILD_SHA) && (
                    <>
                      {' '}
                      <span className="opacity-70">
                        (
                        {BUILD_VERSION || (BUILD_SHA ? BUILD_SHA.slice(0, 7) : '')}
                        )
                      </span>
                    </>
                  )}
                </span>
                <button 
                    onClick={() => updateServiceWorker(true)} 
                    className={`flex items-center gap-2 px-3 py-1.5 rounded text-xs font-bold transition-all ${needRefresh ? 'bg-blue-600 text-white animate-pulse shadow-lg shadow-blue-500/20' : 'bg-gray-800 text-gray-400 hover:bg-gray-700'}`}
                >
                    <RefreshCw size={14} className={needRefresh ? "animate-spin" : ""} />
                    {needRefresh ? "AGGIORNA ORA" : "Verifica Agg."}
                </button>
            </div>
            
            {/* PULSANTE PROPOSTE PENDENTI (STAFF) */}
            {isCampaignMaster && adminPendingCount > 0 && (
                    <button
                    onClick={() => {
                        onSwitchToMaster('proposte'); 
                        setIsMenuOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 mb-2 text-orange-400 hover:bg-gray-700 transition-colors border border-orange-500/30 bg-orange-500/10 rounded-lg animate-pulse"
                >
                    <ClipboardCheck size={20} />
                    <span className="font-bold">PROPOSTE DA APPROVARE</span>
                    <span className="ml-auto bg-red-600 text-white text-xs px-2 py-0.5 rounded-full shadow-sm">
                        {adminPendingCount}
                    </span>
                </button>
            )}

            {/* PULSANTE VAI A STAFF DASHBOARD */}
            {isCampaignMaster && (
                <button
                    onClick={() => {
                        onSwitchToMaster(); 
                        setIsMenuOpen(false);
                    }}
                    className="w-full flex items-center gap-3 px-4 py-3 text-emerald-400 hover:bg-gray-700 transition-colors border-b border-gray-700 mb-2"
                >
                    <UserCog size={20} />
                    <span className="font-bold">DASHBOARD STAFF</span>
                </button>
            )}

            {/* --- [MODIFICA] PULSANTE CAMBIO PASSWORD (NEL MENU) --- */}
            <button 
                onClick={() => {
                    setForceSetLocalPassword(false);
                    setIsPasswordModalOpen(true);
                    setIsMenuOpen(false);
                }}
                className="w-full flex items-center gap-3 px-4 py-3 text-gray-300 hover:bg-gray-700 hover:text-white transition-colors border border-gray-700/50 rounded mb-2"
            >
                <Key size={18} />
                <span className="font-bold text-sm">CAMBIA PASSWORD</span>
            </button>

            <button 
                onClick={onLogout} 
                className="w-full flex items-center justify-center gap-2 p-2 rounded bg-red-900/20 text-red-400 hover:bg-red-900/40 border border-red-900/50 transition-colors text-sm font-bold"
            >
                <LogOut size={16} /> Logout
            </button>
        </div>
    </div>
  );

  if (isRevivalActive) {
    return (
      <div className="h-screen w-screen bg-black text-white flex items-center justify-center p-6">
        <div className="w-full max-w-lg text-center border border-emerald-500/50 bg-emerald-950/40 rounded-2xl p-6 shadow-2xl">
          <div className="text-xs uppercase tracking-[0.25em] text-emerald-300 font-black">Rianimazione personaggio</div>
          <div className="mt-2 text-sm text-emerald-200">La web app e temporaneamente sospesa fino al termine della rianimazione.</div>
          <div className="mt-6 text-6xl font-black font-mono text-emerald-100">{revivalMin}:{revivalSec}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-900 text-white overflow-hidden">
      
      {/* --- TIMER OVERLAY --- */}
      <TimerOverlay activeTimers={activeTimers} onRemove={removeTimerState} />

      {selectedCharacterData && auraInnataRecord && (
        <RazzaModal
          isOpen={razzaModalOpen}
          onClose={() => setRazzaModalOpen(false)}
          personaggioId={selectedCharacterData.id}
          abilitaPossedute={selectedCharacterData.abilita_possedute}
          punteggiBase={selectedCharacterData.punteggi_base}
          punteggiList={punteggiList}
          auraInnataRecord={auraInnataRecord}
          onLogout={onLogout}
          onUpdated={refreshCharacterData}
        />
      )}
      
      {/* --- SIDEBAR DESKTOP (FISSA A SINISTRA) --- */}
      <aside className="hidden md:flex flex-col w-72 bg-gray-950 border-r border-gray-800 shadow-2xl z-20">
            <div className="p-4 border-b border-gray-900 flex items-center gap-3 h-16">
                 <div className="bg-indigo-900/50 p-1.5 rounded-lg border border-indigo-500/30">
                    <UserCog size={20} className="text-indigo-400"/>
                 </div>
                 <span className="font-black text-gray-200 italic tracking-widest uppercase text-sm">MENU UTENTE</span>
            </div>
            {/* Riutilizza il contenuto del menu */}
            {renderMenuContent()}
      </aside>

      {/* --- WRAPPER CONTENUTO PRINCIPALE --- */}
      <div className="flex-1 flex flex-col min-w-0 relative">
          
          {/* --- HEADER --- */}
          <header className="relative flex justify-between items-center p-3 shadow-md shrink-0 border-b border-gray-700 z-10 h-16 backdrop-blur-sm bg-gray-800/95">
              <div className="flex items-center gap-3 z-20">
                  <button
                    type="button"
                    onClick={() => navigate('/app/start')}
                    className="flex items-center gap-3"
                    title="Torna alla pagina iniziale"
                  >
                    <img src="/pwa-512x512.png" alt="Logo" className="w-9 h-9 object-contain drop-shadow-lg" />
                    <h1 className="text-xl font-black italic hidden sm:block text-blue-400">KOR-35</h1>
                  </button>
              </div>

              <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full text-center pointer-events-none z-10">
                {selectedCharacterData ? (
                    <div className="flex flex-col items-center justify-center animate-fadeIn">
                        <span className="font-bold text-white text-base tracking-wide drop-shadow-md inline-flex items-center gap-1.5">
                            {selectedCharacterData.nome}
                            {String(preferredCharacterId || '') === String(selectedCharacterId) && (
                                <Star size={14} className="text-amber-400" fill="currentColor" />
                            )}
                        </span>
                        {auraInnataRecord && (
                          <button
                            type="button"
                            onClick={() => razzaHeader.canEdit && setRazzaModalOpen(true)}
                            disabled={!razzaHeader.canEdit}
                            className={`text-xs leading-none mt-0.5 pointer-events-auto ${
                              razzaHeader.canEdit ? 'cursor-pointer' : 'cursor-default opacity-90'
                            }`}
                            title={
                              razzaHeader.canEdit
                                ? 'Clicca per modificare archetipo/forma'
                                : 'Razza bloccata: evento già iniziato'
                            }
                          >
                            <span
                              className={`font-semibold ${
                                razzaHeader.canEdit
                                  ? 'bg-linear-to-r from-amber-200 via-fuchsia-200 to-cyan-200 text-transparent bg-clip-text animate-pulse'
                                  : 'text-white/90'
                              }`}
                            >
                              {razzaHeader.full}
                            </span>
                          </button>
                        )}
                    </div>
                ) : <span className="text-gray-500 italic text-sm animate-pulse">Seleziona Personaggio</span>}
              </div>

              <div className="flex items-center gap-3 z-20">
                  <button
                    type="button"
                    onClick={() => navigate('/app/start')}
                    className="hidden sm:flex items-center gap-2 px-2 py-1 rounded-lg border border-indigo-500/30 hover:bg-indigo-600/10"
                    title="Torna alla splash page"
                  >
                    <img src="/pwa-512x512.png" alt="Logo" className="w-5 h-5 object-contain" />
                    <span className="text-xs font-black italic text-blue-300">KOR35</span>
                  </button>
                  {isLoading && <Loader2 size={20} className="text-indigo-400 animate-spin" />}
                  
                  {/* --- [MODIFICA] PULSANTE AIUTO (?) --- */}
                  {TAB_TO_WIKI_SLUG[activeTab] && (
                    <button
                      onClick={openWikiHelp}
                      className="p-2 rounded-full hover:bg-indigo-600/20 transition-colors text-indigo-400 hover:text-indigo-300 border border-indigo-500/30 hover:border-indigo-400/50"
                      title="Guida e Istruzioni"
                      aria-label="Apri guida"
                    >
                      <HelpCircle size={20} />
                    </button>
                  )}
                  
                  {/* HAMBURGER VISIBILE SOLO SU MOBILE */}
                  <button onClick={() => setIsMenuOpen(true)} className="md:hidden relative p-2 rounded-full hover:bg-gray-700 transition-colors text-gray-200">
                    <Menu size={28} />
                    
                    {/* PALLINI NOTIFICHE HEADER */}
                    <div className="absolute top-1 right-1 flex flex-col gap-0.5 pointer-events-none">
                        {hasAdminNotif && <span className="block h-2.5 w-2.5 rounded-full ring-1 ring-gray-900 bg-red-600 animate-pulse shadow-sm" title="Admin Pending" />}
                        {/* [MODIFICA] Pallino verde se staff msg */}
                        {hasStaffMsgNotif && <span className="block h-2.5 w-2.5 rounded-full ring-1 ring-gray-900 bg-green-500 animate-pulse shadow-sm" title="Staff Msg" />}
                        {(!hasStaffMsgNotif && hasMsgNotif) && <span className="block h-2.5 w-2.5 rounded-full ring-1 ring-gray-900 bg-purple-500 shadow-sm" title="Messaggi" />}
                        {hasJobNotif && <span className="block h-2.5 w-2.5 rounded-full ring-1 ring-gray-900 bg-amber-500 shadow-sm" title="Lavori" />}
                        {needRefresh && <span className="block h-2.5 w-2.5 rounded-full ring-1 ring-gray-900 bg-blue-500 animate-bounce shadow-sm" title="Update" />}
                    </div>
                  </button>
              </div>
          </header>

          {/* --- DRAWER MENU MOBILE (OVERLAY A DESTRA) --- */}
          {/* Renderizzato condizionalmente o via CSS. Qui condizionale per semplicità React */}
          {isMenuOpen && (
            <div className="md:hidden fixed inset-0 z-50 flex justify-end">
                <div className="absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity" onClick={() => setIsMenuOpen(false)}></div>
                
                <div className="relative w-85 max-w-sm bg-gray-800 h-full shadow-2xl flex flex-col border-l border-gray-700 animate-slide-in-right overflow-hidden">
                    <div className="flex justify-between items-center p-4 border-b border-gray-700 bg-gray-900/50 shrink-0 h-16">
                        <h2 className="text-lg font-bold text-gray-100 uppercase tracking-wider flex items-center gap-2">
                            <UserCog size={20} className="text-indigo-400"/> Opzioni
                        </h2>
                        <button onClick={() => setIsMenuOpen(false)} className="text-gray-400 hover:text-white"><X size={24} /></button>
                    </div>
                    {/* Riutilizza il contenuto del menu */}
                    {renderMenuContent()}
                </div>
            </div>
          )}

          {/* --- CONTENT --- */}
          <main className="flex-1 overflow-y-auto relative bg-gray-900 scrollbar-hide">
            {showLocalPasswordReminder && (
              <div className="sticky top-0 z-20 px-3 pt-2">
                <div className="rounded-xl border border-amber-400/60 bg-amber-950/80 backdrop-blur p-3 text-amber-100 shadow-lg flex items-center justify-between gap-3">
                  <div className="text-xs sm:text-sm">
                    Password locale non configurata, per inserirla cliccare qui.
                  </div>
                  <button
                    type="button"
                    onClick={() => {
                      setForceSetLocalPassword(true);
                      setIsPasswordModalOpen(true);
                    }}
                    className="shrink-0 px-3 py-1.5 text-xs font-bold rounded bg-amber-400 text-gray-900 hover:bg-amber-300"
                  >
                    Configura
                  </button>
                </div>
              </div>
            )}
            {isComaLocked && (
              <div className="sticky top-0 z-20 px-3 pt-2">
                <div className="rounded-xl border border-red-500/60 bg-red-950/80 backdrop-blur p-3 text-red-100 shadow-lg">
                  <div className="text-[11px] uppercase tracking-widest font-black">
                    {comaStatus === 'dead'
                      ? 'Personaggio morto'
                      : comaStatus === 'paused'
                        ? 'Coma stabilizzato'
                        : 'Coma in corso'}
                  </div>
                  <div className="text-xs mt-1 text-red-200">
                    Accesso limitato: fino a risoluzione del coma puoi usare solo la scheda `Game`.
                  </div>
                </div>
              </div>
            )}
            {renderTabContent()}
          </main>

          {/* --- BOTTOM NAV --- */}
          <nav className="flex justify-around items-center bg-gray-800 shadow-[0_-4px_6px_-1px_rgba(0,0,0,0.3)] shrink-0 border-t border-gray-700 z-10 h-[60px] pb-safe">
            <TabButton icon={<Gamepad2 size={24} />} label="Game" isActive={activeTab === 'game'} onClick={() => setActiveTab('game')} />
            <TabButton icon={<Home size={24} />} label="Scheda" isActive={activeTab === 'home'} onClick={() => setActiveTab('home')} />
            
            <div className="w-px h-8 bg-gray-700 mx-1 opacity-50"></div>

            {userShortcuts.map(tabId => {
                const tab = AVAILABLE_TABS.find(t => t.id === tabId);
                if (!tab) return null;
                
                let showDot = false;
                let dotColor = 'bg-red-500';
                
                // [MODIFICA] Gestione bollino verde prioritario
                if (tab.id === 'messaggi') {
                    if (hasStaffMsgNotif) {
                        showDot = true;
                        dotColor = 'bg-green-500';
                    } else if (hasMsgNotif) {
                        showDot = true;
                        dotColor = 'bg-purple-500';
                    }
                }
                
                return (
                    <TabButton 
                        key={tabId}
                        icon={<tab.icon size={24} />} 
                        label={tab.label} 
                        isActive={activeTab === tabId} 
                        onClick={() => setActiveTab(tabId)} 
                        notificationDot={showDot}
                        dotColor={dotColor}
                    />
                );
            })}
          </nav>
      </div>

      {qrResultData && (
        <QrResultModal data={qrResultData} onClose={closeQrModal} onLogout={onLogout} onStealSuccess={handleStealSuccess} />
      )}

      {/* --- [MODIFICA] MODALE CAMBIO PASSWORD --- */}
      <PasswordChangeModal 
          isOpen={isPasswordModalOpen} 
          onClose={() => setIsPasswordModalOpen(false)} 
          onLogout={onLogout}
          forceSetMode={forceSetLocalPassword}
          onSuccess={() => {
            setShowLocalPasswordReminder(false);
            setForceSetLocalPassword(false);
          }}
      />

      {/* --- [MODIFICA] MODALE WIKI HELP --- */}
      <WikiHelpModal
          isOpen={isWikiHelpOpen}
          onClose={closeWikiHelp}
          wikiSlug={currentWikiSlug}
      />
    </div>
  );
};

// Componente TabButton (Memoized per performance)
const TabButton = memo(({ icon, label, isActive, onClick, notificationDot, dotColor }) => (
  <button 
    onClick={onClick} 
    className={`flex flex-col items-center justify-center p-1 min-w-14 h-full transition-all duration-200 ${isActive ? 'text-indigo-400' : 'text-gray-500 hover:text-gray-300'} focus:outline-none relative group`}
  >
    <div className={`transition-transform duration-200 ${isActive ? '-translate-y-1 scale-110' : 'group-active:scale-95'}`}>
        {icon}
        {notificationDot && (
            <span className={`absolute -top-1 -right-1 w-2.5 h-2.5 rounded-full border border-gray-800 animate-pulse ${dotColor}`}></span>
        )}
    </div>
    
    <span className={`text-[10px] font-medium tracking-tight mt-0.5 truncate max-w-16 transition-colors ${isActive ? 'text-indigo-400' : 'text-gray-500'}`}>{label}</span>
    
    {isActive && (
        <div className="absolute bottom-0 w-8 h-0.5 bg-indigo-400 rounded-t-full shadow-[0_0_8px_rgba(99,102,241,0.6)] animate-pulse"></div>
    )}
  </button>
));

TabButton.displayName = 'TabButton';

export default memo(MainPage);