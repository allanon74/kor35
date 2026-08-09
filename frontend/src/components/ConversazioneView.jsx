import React, { useState, useRef, useEffect } from 'react';
import { Reply, Send, X, Users, MessageCircle, Shield } from 'lucide-react';
import RichTextDisplay from './RichTextDisplay';
import RichTextEditor from './RichTextEditor';

const ConversazioneView = ({ conversazione, onRispondi, onClose, currentPersonaggioId }) => {
  const [testoRisposta, setTestoRisposta] = useState('');
  const [isReplying, setIsReplying] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const messagesEndRef = useRef(null);

  const titolo =
    conversazione.titolo ||
    (conversazione.partecipanti || []).map((p) => p.nome).filter(Boolean).join(', ') ||
    'Conversazione';

  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [conversazione.messaggi]);

  const handleRispondi = async () => {
    if (!testoRisposta.trim()) return;
    const lastId = conversazione.messaggi?.[conversazione.messaggi.length - 1]?.id;
    if (!lastId) return;

    setIsSending(true);
    try {
      await onRispondi(lastId, testoRisposta);
      setTestoRisposta('');
      setIsReplying(false);
    } catch (error) {
      console.error('Errore invio risposta:', error);
      alert("Errore nell'invio della risposta");
    } finally {
      setIsSending(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/70 p-0 sm:p-4">
      <div className="flex flex-col w-full max-w-3xl h-[92vh] sm:h-[85vh] bg-gray-950 sm:rounded-2xl shadow-2xl overflow-hidden border border-gray-700/80">
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900/90">
          <div className="flex items-center gap-3 min-w-0">
            <div className="rounded-full bg-indigo-600/25 p-2 text-indigo-300 shrink-0">
              {titolo === 'Staff' ? <Shield className="w-5 h-5" /> : <MessageCircle className="w-5 h-5" />}
            </div>
            <div className="min-w-0">
              <h2 className="text-lg font-bold text-white truncate">{titolo}</h2>
              <div className="flex items-center gap-2 mt-0.5 text-xs text-gray-400">
                <Users className="w-3.5 h-3.5 shrink-0" />
                <span className="truncate">
                  {(conversazione.partecipanti || []).map((p) => p.nome).join(', ') || 'Chat'}
                </span>
              </div>
            </div>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 text-gray-400 rounded-full hover:bg-gray-800 hover:text-white transition-colors"
            aria-label="Chiudi"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gradient-to-b from-gray-950 to-gray-900 custom-scrollbar">
          {(conversazione.messaggi || []).map((msg, index) => {
            const isStaff = msg.mittente_is_staff || msg.tipo_messaggio === 'STAFF' || msg.is_staff_message;
            const isMine = Number(msg.mittente_personaggio_id) === Number(currentPersonaggioId);
            const prev = conversazione.messaggi[index - 1];
            const showAvatar =
              index === 0 ||
              Number(prev?.mittente_personaggio_id) !== Number(msg.mittente_personaggio_id);

            return (
              <div key={msg.id} className={`flex w-full ${isMine ? 'justify-end' : 'justify-start'}`}>
                <div className={`relative max-w-[85%] sm:max-w-[75%] flex flex-col gap-1 ${isMine ? 'items-end' : 'items-start'}`}>
                  {showAvatar && (
                    <span
                      className={`text-[11px] font-semibold px-2 ${
                        isStaff ? 'text-red-400' : isMine ? 'text-indigo-300' : 'text-gray-400'
                      }`}
                    >
                      {msg.mittente_personaggio_nome || msg.mittente_nome || (isStaff ? 'Staff' : 'Sconosciuto')}
                    </span>
                  )}
                  <div
                    className={`rounded-2xl px-3.5 py-2.5 shadow-md ${
                      isMine
                        ? 'bg-indigo-600 text-white rounded-tr-md'
                        : isStaff
                          ? 'bg-red-950/70 text-gray-100 rounded-tl-md border border-red-800/50'
                          : 'bg-gray-800 text-gray-100 rounded-tl-md border border-gray-700/60'
                    }`}
                  >
                    {msg.titolo ? <div className="font-semibold text-sm mb-1 opacity-95">{msg.titolo}</div> : null}
                    <div className="text-sm prose prose-invert max-w-none prose-p:my-1">
                      <RichTextDisplay content={msg.testo} />
                    </div>
                    <div className={`text-[10px] mt-1.5 ${isMine ? 'text-indigo-200/80' : 'text-gray-500'}`}>
                      {new Date(msg.data_creazione || msg.data_invio).toLocaleString()}
                    </div>
                  </div>
                </div>
              </div>
            );
          })}
          <div ref={messagesEndRef} />
        </div>

        <div className="border-t border-gray-800 bg-gray-900 p-3 sm:p-4">
          {!isReplying ? (
            <button
              type="button"
              onClick={() => setIsReplying(true)}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-colors"
            >
              <Reply className="w-5 h-5" />
              Rispondi
            </button>
          ) : (
            <div className="space-y-2">
              <div className="bg-gray-950 rounded-xl border border-gray-700 overflow-hidden min-h-[120px]">
                <RichTextEditor
                  value={testoRisposta}
                  onChange={setTestoRisposta}
                  placeholder="Scrivi la tua risposta..."
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleRispondi}
                  disabled={!testoRisposta.trim() || isSending}
                  className="flex-1 py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                >
                  <Send className="w-4 h-4" />
                  {isSending ? 'Invio...' : 'Invia'}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setIsReplying(false);
                    setTestoRisposta('');
                  }}
                  className="px-4 py-2.5 bg-gray-800 hover:bg-gray-700 text-white rounded-xl transition-colors"
                >
                  Annulla
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ConversazioneView;
