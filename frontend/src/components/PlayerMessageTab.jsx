import React, { useMemo, useState, useEffect, useRef, useCallback } from 'react';
import { useCharacter } from './CharacterContext';
import { Trash2, Mail, Eye, EyeOff, MessageCircle, Megaphone, Shield, ChevronRight, Coins, Package } from 'lucide-react';
import ComposeMessageModal from './ComposeMessageModal';
import ConversazioneView from './ConversazioneView';
import RichTextDisplay from './RichTextDisplay';
import MessageAttachmentsLine from './MessageAttachmentsLine';
import { getMessageAttachmentsSummary } from './messageAttachments';
import { importiDaMessaggio } from '../utils/creditiCessione';
import { getConversazioni, rispondiMessaggio, markMessageAsRead } from '../api';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import { OfflineConsultBanner } from './OfflineConsultBanner';

const PlayerMessageTab = ({ onLogout, composeTarget, onComposeTargetConsumed, scrollToFirstUnreadNonce = 0 }) => {
  const {
    selectedCharacterData: char,
    userMessages,
    fetchUserMessages,
    selectedCharacterId,
    personaggiList,
    isCampaignStaffer,
    handleToggleRead,
    handleDeleteMessage: contextDeleteMessage,
  } = useCharacter();
  const isOnline = useOnlineStatus();

  const [isComposeOpen, setIsComposeOpen] = useState(false);
  const [replyToRecipient, setReplyToRecipient] = useState(null);
  const [expandedMessages, setExpandedMessages] = useState({});
  const [viewMode, setViewMode] = useState('chat'); // 'chat' | 'annunci'
  const [conversazioni, setConversazioni] = useState([]);
  const [activeConversazione, setActiveConversazione] = useState(null);
  const [loadingConv, setLoadingConv] = useState(false);
  const messagesEndRef = useRef(null);
  const firstUnreadRef = useRef(null);

  const transferableItems = (char?.oggetti || []).filter(
    (item) => item && item.id && item.tipo_oggetto === 'FIS' && !item.is_equipaggiato
  );

  const messageSenderName = (msg) =>
    msg.mittente_personaggio_nome || msg.mittente_nome || (msg.mittente_is_staff ? 'Staff' : 'Sistema');

  const systemMessages = useMemo(() => {
    return (userMessages || []).filter(
      (m) => m.tipo_messaggio === 'BROAD' || m.tipo_messaggio === 'GROUP'
    );
  }, [userMessages]);

  const firstUnreadId = useMemo(() => {
    const pool = viewMode === 'annunci' ? systemMessages : userMessages || [];
    const m = pool.find((x) => x && x.letto === false);
    return m ? m.id : null;
  }, [userMessages, systemMessages, viewMode]);

  const refreshConversazioni = useCallback(async () => {
    if (!selectedCharacterId || !isOnline) return [];
    const data = await getConversazioni(selectedCharacterId, onLogout);
    const list = Array.isArray(data) ? data : [];
    setConversazioni(list);
    return list;
  }, [selectedCharacterId, isOnline, onLogout]);

  const markIncomingAsRead = useCallback(
    async (conv) => {
      if (!conv || !selectedCharacterId) return conv;
      const incomingUnread = (conv.messaggi || []).filter(
        (m) =>
          !m.letto &&
          Number(m.mittente_personaggio_id) !== Number(selectedCharacterId)
      );
      if (!incomingUnread.length) return conv;

      const unreadIds = new Set(incomingUnread.map((m) => m.id));
      const markedConv = {
        ...conv,
        non_letti: 0,
        messaggi: (conv.messaggi || []).map((m) =>
          unreadIds.has(m.id) ? { ...m, letto: true } : m
        ),
      };

      // UI immediata (lista + thread)
      setActiveConversazione((prev) =>
        prev && prev.conversazione_id === conv.conversazione_id ? markedConv : prev
      );
      setConversazioni((list) =>
        list.map((c) => (c.conversazione_id === conv.conversazione_id ? markedConv : c))
      );

      // Persistenza con endpoint "leggi" (affidabile, non toggle)
      await Promise.all(
        incomingUnread.map(async (m) => {
          try {
            await markMessageAsRead(m.id, selectedCharacterId, onLogout);
          } catch {
            /* ignore singolo */
          }
        })
      );

      try {
        await fetchUserMessages(selectedCharacterId);
      } catch {
        /* ignore */
      }

      try {
        const list = await refreshConversazioni();
        const updated = list.find((c) => c.conversazione_id === conv.conversazione_id);
        if (updated) {
          setActiveConversazione((prev) =>
            prev && prev.conversazione_id === conv.conversazione_id ? updated : prev
          );
          return updated;
        }
      } catch {
        /* ignore */
      }
      return markedConv;
    },
    [selectedCharacterId, onLogout, fetchUserMessages, refreshConversazioni]
  );

  const loadConversazioni = useCallback(async () => {
    if (!selectedCharacterId || !isOnline) return;
    setLoadingConv(true);
    try {
      await refreshConversazioni();
    } catch (e) {
      console.error(e);
      setConversazioni([]);
    } finally {
      setLoadingConv(false);
    }
  }, [selectedCharacterId, isOnline, refreshConversazioni]);

  useEffect(() => {
    loadConversazioni();
  }, [loadConversazioni, userMessages]);

  useEffect(() => {
    if (firstUnreadRef.current) {
      firstUnreadRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
      return;
    }
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [scrollToFirstUnreadNonce, firstUnreadId, viewMode]);

  useEffect(() => {
    if (!composeTarget) return;
    if (!isOnline) {
      if (onComposeTargetConsumed) onComposeTargetConsumed();
      return;
    }
    setReplyToRecipient(composeTarget);
    setIsComposeOpen(true);
    if (onComposeTargetConsumed) onComposeTargetConsumed();
  }, [composeTarget, onComposeTargetConsumed, isOnline]);

  const toggleMessageExpansion = (msgId) => {
    setExpandedMessages((prev) => ({
      ...prev,
      [msgId]: !prev[msgId],
    }));
  };

  const handleOpenConversazione = async (conv) => {
    setActiveConversazione(conv);
    // All'apertura: segna subito come letti i messaggi in arrivo
    await markIncomingAsRead(conv);
  };

  const handleRispondiThread = async (messaggioId, testo) => {
    await rispondiMessaggio(messaggioId, selectedCharacterId, testo, '', onLogout);
    await fetchUserMessages(selectedCharacterId);
    const list = await refreshConversazioni();
    const key = activeConversazione?.conversazione_id;
    setActiveConversazione(list.find((c) => c.conversazione_id === key) || null);
  };

  if (!char) return <div className="text-gray-400 text-center mt-4">Seleziona un personaggio</div>;

  const formatTime = (iso) => {
    if (!iso) return '';
    try {
      return new Date(iso).toLocaleString(undefined, {
        day: '2-digit',
        month: 'short',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <div className="flex flex-col h-[calc(100dvh-200px)] min-h-[420px] relative">
      {!isOnline && (
        <div className="px-2 mb-2">
          <OfflineConsultBanner />
          <p className="mt-1 text-[11px] text-center text-amber-200/80">
            Inbox in cache se disponibile. Nuovi messaggi e risposte sono bloccati offline.
          </p>
        </div>
      )}

      <div className="flex gap-1 p-1 mb-3 rounded-xl bg-gray-900/80 border border-gray-800">
        <button
          type="button"
          onClick={() => setViewMode('chat')}
          className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-colors ${
            viewMode === 'chat' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          <MessageCircle size={16} />
          Chat
          {conversazioni.some((c) => Number(c.non_letti) > 0) && (
            <span className="min-w-5 h-5 px-1 rounded-full bg-red-600 text-[10px] leading-5 text-center">
              {conversazioni.reduce((a, c) => a + Number(c.non_letti || 0), 0)}
            </span>
          )}
        </button>
        <button
          type="button"
          onClick={() => setViewMode('annunci')}
          className={`flex-1 flex items-center justify-center gap-2 rounded-lg py-2 text-sm font-semibold transition-colors ${
            viewMode === 'annunci' ? 'bg-indigo-600 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800'
          }`}
        >
          <Megaphone size={16} />
          Annunci
          {systemMessages.some((m) => !m.letto) && (
            <span className="min-w-5 h-5 px-1 rounded-full bg-amber-600 text-[10px] leading-5 text-center">
              {systemMessages.filter((m) => !m.letto).length}
            </span>
          )}
        </button>
      </div>

      {viewMode === 'chat' ? (
        <div className="flex-1 overflow-y-auto custom-scrollbar mb-16 space-y-2 px-1">
          {loadingConv && conversazioni.length === 0 ? (
            <div className="text-center text-gray-500 py-10">Caricamento conversazioni…</div>
          ) : conversazioni.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-70 py-12">
              <MessageCircle size={40} className="mb-3 opacity-40" />
              <p className="font-medium">Nessuna conversazione</p>
              <p className="text-xs mt-1">Scrivi un messaggio o contatta lo staff.</p>
            </div>
          ) : (
            conversazioni.map((conv) => {
              const unread = Number(conv.non_letti || 0);
              const isStaffThread = conv.conversazione_id === 'staff' || conv.titolo === 'Staff';
              const lastMsg = (conv.messaggi || [])[(conv.messaggi || []).length - 1];
              const allegatiSummary = getMessageAttachmentsSummary(lastMsg);
              return (
                <button
                  key={conv.conversazione_id}
                  type="button"
                  onClick={() => handleOpenConversazione(conv)}
                  className={`w-full text-left rounded-xl border p-3 transition-all flex items-center gap-3 ${
                    unread > 0
                      ? 'bg-indigo-950/50 border-indigo-500/40 hover:bg-indigo-900/40'
                      : 'bg-gray-900/70 border-gray-800 hover:bg-gray-800/80'
                  }`}
                >
                  <div
                    className={`rounded-full p-2.5 shrink-0 ${
                      isStaffThread ? 'bg-red-900/50 text-red-300' : 'bg-indigo-900/50 text-indigo-300'
                    }`}
                  >
                    {isStaffThread ? <Shield size={18} /> : <MessageCircle size={18} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-semibold text-white truncate">{conv.titolo || 'Chat'}</span>
                      <span className="text-[10px] text-gray-500 shrink-0">
                        {formatTime(conv.ultimo_messaggio)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-400 truncate mt-0.5">{conv.anteprima || '—'}</p>
                    {allegatiSummary ? (
                      <p className="mt-1 text-[11px] text-amber-200/90 truncate inline-flex items-center gap-1 max-w-full">
                        {importiDaMessaggio(lastMsg).corrente > 0 || importiDaMessaggio(lastMsg).deposito > 0 ? (
                          <Coins size={12} className="shrink-0" />
                        ) : null}
                        {(lastMsg?.oggetti_allegati_snapshot || []).length > 0 ? (
                          <Package size={12} className="shrink-0" />
                        ) : null}
                        <span className="truncate">Allegati: {allegatiSummary}</span>
                      </p>
                    ) : null}
                  </div>
                  {unread > 0 ? (
                    <span className="min-w-6 h-6 px-1.5 rounded-full bg-red-600 text-white text-xs leading-6 text-center shrink-0">
                      {unread > 99 ? '99+' : unread}
                    </span>
                  ) : (
                    <ChevronRight size={16} className="text-gray-600 shrink-0" />
                  )}
                </button>
              );
            })
          )}
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-2 space-y-4 custom-scrollbar mb-16">
          {systemMessages.length > 0 ? (
            systemMessages.map((msg) => {
              const isExpanded = expandedMessages[msg.id];
              const isRead = msg.letto;

              return (
                <div
                  key={msg.id}
                  ref={firstUnreadId && msg.id === firstUnreadId ? firstUnreadRef : null}
                  className="flex w-full justify-start"
                >
                  <div
                    className={`relative max-w-[95%] rounded-xl p-3 shadow-md transition-all border-l-4 ${
                      isRead
                        ? 'bg-gray-800/80 opacity-80 border-amber-700/50'
                        : 'bg-gray-800 border-amber-400'
                    } text-gray-100`}
                  >
                    <div className="flex justify-between items-start mb-2 border-b border-white/10 pb-1 gap-4">
                      <div className="flex items-center gap-2">
                        <Megaphone size={14} className={isRead ? 'opacity-50' : 'text-amber-400'} />
                        <span className="text-xs font-bold uppercase tracking-wider text-amber-200">
                          {msg.tipo_messaggio === 'GROUP' ? 'Gruppo' : 'Broadcast'}
                          {' · '}
                          {messageSenderName(msg)}
                        </span>
                        {!isRead && (
                          <span className="text-[9px] bg-yellow-600 text-white px-1.5 py-0.5 rounded-full font-bold uppercase">
                            Nuovo
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2">
                        <span className="text-[10px] text-gray-400">
                          {new Date(msg.data_creazione || msg.data_invio).toLocaleString()}
                        </span>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            handleToggleRead(msg.id);
                          }}
                          className={`transition-colors p-0.5 rounded ${isRead ? 'text-gray-500 hover:text-blue-400' : 'text-blue-400'}`}
                          title={isRead ? 'Segna come non letto' : 'Segna come letto'}
                        >
                          {isRead ? <EyeOff size={14} /> : <Eye size={14} />}
                        </button>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            contextDeleteMessage(msg.id);
                          }}
                          className="text-gray-400 hover:text-red-400 transition-colors p-0.5 rounded"
                          title="Cancella"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                    </div>
                    {msg.titolo && (
                      <div
                        className="font-bold text-sm mb-1 cursor-pointer"
                        onClick={() => toggleMessageExpansion(msg.id)}
                      >
                        {msg.titolo}
                      </div>
                    )}
                    <div
                      className={`text-sm prose prose-invert max-w-none wrap-break-words relative transition-all duration-300 cursor-pointer ${!isExpanded ? 'max-h-24 overflow-hidden' : ''}`}
                      onClick={() => toggleMessageExpansion(msg.id)}
                    >
                      <RichTextDisplay content={msg.testo} />
                      {!isExpanded && (
                        <div className="absolute bottom-0 left-0 w-full h-8 bg-linear-to-t from-gray-800/90 to-transparent pointer-events-none" />
                      )}
                    </div>
                    <MessageAttachmentsLine msg={msg} />
                  </div>
                </div>
              );
            })
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-60">
              <p>Nessun annuncio.</p>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      <div className="absolute bottom-4 right-4 z-10">
        <button
          type="button"
          onClick={() => {
            if (!isOnline) return;
            setReplyToRecipient(null);
            setIsComposeOpen(true);
          }}
          disabled={!isOnline}
          className={`bg-indigo-600 hover:bg-indigo-500 text-white rounded-full p-4 shadow-xl flex items-center gap-2 transition-transform hover:scale-105 ${
            !isOnline ? 'opacity-40 cursor-not-allowed hover:scale-100' : ''
          }`}
          title={isOnline ? 'Nuovo messaggio' : 'Offline: compose disabilitato'}
        >
          <Mail size={24} />
          <span className="font-bold hidden sm:inline">Nuovo</span>
        </button>
      </div>

      <ComposeMessageModal
        isOpen={isComposeOpen && isOnline}
        onClose={() => {
          setIsComposeOpen(false);
          setReplyToRecipient(null);
        }}
        currentCharacterId={selectedCharacterId}
        availableCharacters={personaggiList}
        isCampaignStaffer={isCampaignStaffer}
        replyToRecipient={replyToRecipient}
        onMessageSent={() => {
          fetchUserMessages(selectedCharacterId);
          loadConversazioni();
        }}
        onLogout={onLogout}
        availableTransferItems={transferableItems}
        currentCredits={char?.crediti || 0}
      />

      {activeConversazione && (
        <ConversazioneView
          conversazione={activeConversazione}
          currentPersonaggioId={selectedCharacterId}
          onClose={() => setActiveConversazione(null)}
          onRispondi={handleRispondiThread}
          onMarkIncomingRead={async () => {
            if (activeConversazione) await markIncomingAsRead(activeConversazione);
          }}
        />
      )}
    </div>
  );
};

export default PlayerMessageTab;
