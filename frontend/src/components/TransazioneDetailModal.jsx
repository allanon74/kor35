import React, { useState, useEffect } from 'react';
import { Dialog } from '@headlessui/react';
import { X, Check, XCircle, MessageSquare, Send, Loader2 } from 'lucide-react';
import { getTransazioneDetail, confermaTransazione, addPropostaTransazione } from '../api';
import { useCharacter } from './CharacterContext';
import PropostaEditorModal from './PropostaEditorModal';

const TransazioneDetailModal = ({ transazioneId, onClose, onLogout, onUpdate }) => {
  const { selectedCharacterData, selectedCharacterId } = useCharacter();
  const [transazione, setTransazione] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showPropostaEditor, setShowPropostaEditor] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);

  useEffect(() => {
    loadTransazione();
  }, [transazioneId]);

  const loadTransazione = async () => {
    setLoading(true);
    try {
      const data = await getTransazioneDetail(transazioneId, onLogout);
      setTransazione(data);
    } catch (error) {
      alert("Errore caricamento transazione: " + error.message);
      onClose();
    } finally {
      setLoading(false);
    }
  };

  const handleAccetta = async () => {
    if (!window.confirm("Sei sicuro di voler accettare questa transazione? Gli scambi verranno eseguiti immediatamente.")) {
      return;
    }
    setActionLoading(true);
    try {
      await confermaTransazione(transazioneId, 'accetta', onLogout);
      alert("Transazione accettata! Gli scambi sono stati eseguiti.");
      if (onUpdate) onUpdate();
      onClose();
    } catch (error) {
      alert("Errore: " + error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRifiuta = async () => {
    if (!window.confirm("Sei sicuro di voler rifiutare questa transazione?")) {
      return;
    }
    setActionLoading(true);
    try {
      await confermaTransazione(transazioneId, 'rifiuta', onLogout);
      alert("Transazione rifiutata.");
      if (onUpdate) onUpdate();
      onClose();
    } catch (error) {
      alert("Errore: " + error.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleProposta = async (propostaData) => {
    try {
      await addPropostaTransazione(transazioneId, propostaData, onLogout);
      await loadTransazione(); // Ricarica per vedere la nuova proposta
      if (onUpdate) onUpdate();
    } catch (error) {
      throw error;
    }
  };

  const isMioTurno = () => {
    if (!transazione || !selectedCharacterId) return false;
    const sonoIniziatore = transazione.iniziatore?.id === selectedCharacterId || transazione.iniziatore === selectedCharacterId;
    const sonoDestinatario = transazione.destinatario?.id === selectedCharacterId || transazione.destinatario === selectedCharacterId;
    
    if (!transazione.ultima_proposta_iniziatore) return sonoIniziatore;
    if (!transazione.ultima_proposta_destinatario) return sonoDestinatario;
    
    // Se entrambe hanno proposte, è il turno di chi ha fatto l'ultima proposta
    const ultimaProposta = transazione.proposte?.[0];
    if (ultimaProposta) {
      const autoreId = ultimaProposta.autore?.id || ultimaProposta.autore;
      return autoreId !== selectedCharacterId;
    }
    return false;
  };

  const canAccetta = () => {
    if (!transazione || transazione.stato !== 'IN_ATTESA') return false;
    // Può accettare solo se entrambe le parti hanno una proposta attiva
    if (transazione.ultima_proposta_iniziatore && transazione.ultima_proposta_destinatario) {
      // Verifica che l'utente sia parte della transazione
      const sonoIniziatore = transazione.iniziatore?.id === selectedCharacterId || transazione.iniziatore === selectedCharacterId;
      const sonoDestinatario = transazione.destinatario?.id === selectedCharacterId || transazione.destinatario === selectedCharacterId;
      return sonoIniziatore || sonoDestinatario;
    }
    return false;
  };

  if (loading) {
    return (
      <Dialog open={true} onClose={onClose} className="relative z-50">
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
        <div className="fixed inset-0 flex items-center justify-center">
          <Loader2 className="animate-spin text-indigo-500" size={48} />
        </div>
      </Dialog>
    );
  }

  if (!transazione) return null;

  return (
    <>
      <Dialog open={true} onClose={onClose} className="relative z-50">
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
        
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <Dialog.Panel className="w-full max-w-4xl bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="flex justify-between items-center p-4 border-b border-gray-700 bg-gray-800/50 rounded-t-xl">
              <Dialog.Title className="text-xl font-bold text-white">
                Transazione #{transazione.id}
              </Dialog.Title>
              <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                <X size={24} />
              </button>
            </div>

            {/* Content */}
            <div className="p-6 overflow-y-auto grow custom-scrollbar space-y-6">
              {/* Info Transazione */}
              <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div className="flex justify-between items-center mb-2">
                  <div>
                    <span className="text-sm text-gray-400">Da: </span>
                    <span className="text-white font-bold">{transazione.iniziatore_nome || transazione.richiedente}</span>
                  </div>
                  <div>
                    <span className="text-sm text-gray-400">A: </span>
                    <span className="text-white font-bold">{transazione.destinatario_nome || transazione.mittente}</span>
                  </div>
                  <div className={`px-3 py-1 rounded text-xs font-bold ${
                    transazione.stato === 'IN_ATTESA' ? 'bg-yellow-900 text-yellow-200' :
                    transazione.stato === 'ACCETTATA' ? 'bg-green-900 text-green-200' :
                    'bg-red-900 text-red-200'
                  }`}>
                    {transazione.stato.replace('_', ' ')}
                  </div>
                </div>
              </div>

              {/* Proposte Attive */}
              <div className="grid grid-cols-2 gap-4">
                {/* Proposta Iniziatore */}
                {transazione.ultima_proposta_iniziatore && (
                  <div className="bg-indigo-900/20 border border-indigo-700/30 rounded-lg p-4">
                    <h3 className="font-bold text-indigo-300 mb-3">
                      Proposta di {transazione.iniziatore_nome}
                    </h3>
                    <div className="space-y-2 text-sm">
                      {transazione.ultima_proposta_iniziatore.crediti_da_dare > 0 && (
                        <div>
                          <span className="text-gray-400">Dà: </span>
                          <span className="text-green-400 font-bold">
                            {transazione.ultima_proposta_iniziatore.crediti_da_dare} CR
                          </span>
                        </div>
                      )}
                      {transazione.ultima_proposta_iniziatore.crediti_da_ricevere > 0 && (
                        <div>
                          <span className="text-gray-400">Riceve: </span>
                          <span className="text-yellow-400 font-bold">
                            {transazione.ultima_proposta_iniziatore.crediti_da_ricevere} CR
                          </span>
                        </div>
                      )}
                      {transazione.ultima_proposta_iniziatore.messaggio && (
                        <div className="mt-3 pt-3 border-t border-indigo-700/30">
                          <p className="text-gray-300 italic">{transazione.ultima_proposta_iniziatore.messaggio}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Proposta Destinatario */}
                {transazione.ultima_proposta_destinatario && (
                  <div className="bg-cyan-900/20 border border-cyan-700/30 rounded-lg p-4">
                    <h3 className="font-bold text-cyan-300 mb-3">
                      Proposta di {transazione.destinatario_nome}
                    </h3>
                    <div className="space-y-2 text-sm">
                      {transazione.ultima_proposta_destinatario.crediti_da_dare > 0 && (
                        <div>
                          <span className="text-gray-400">Dà: </span>
                          <span className="text-green-400 font-bold">
                            {transazione.ultima_proposta_destinatario.crediti_da_dare} CR
                          </span>
                        </div>
                      )}
                      {transazione.ultima_proposta_destinatario.crediti_da_ricevere > 0 && (
                        <div>
                          <span className="text-gray-400">Riceve: </span>
                          <span className="text-yellow-400 font-bold">
                            {transazione.ultima_proposta_destinatario.crediti_da_ricevere} CR
                          </span>
                        </div>
                      )}
                      {transazione.ultima_proposta_destinatario.messaggio && (
                        <div className="mt-3 pt-3 border-t border-cyan-700/30">
                          <p className="text-gray-300 italic">{transazione.ultima_proposta_destinatario.messaggio}</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Storico Proposte */}
              {transazione.proposte && transazione.proposte.length > 2 && (
                <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                  <h3 className="font-bold text-gray-300 mb-3">Storico Proposte</h3>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {transazione.proposte.slice(2).map((proposta, idx) => (
                      <div key={proposta.id} className="text-xs text-gray-400 border-l-2 border-gray-700 pl-2">
                        {proposta.autore_nome}: {proposta.crediti_da_dare} CR → {proposta.crediti_da_ricevere} CR
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Footer - Azioni */}
            {transazione.stato === 'IN_ATTESA' && (
              <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
                {canAccetta() && (
                  <button
                    onClick={handleAccetta}
                    disabled={actionLoading}
                    className="px-4 py-2 bg-green-600 hover:bg-green-500 rounded-lg text-white font-bold text-sm flex items-center gap-2 disabled:opacity-50"
                  >
                    {actionLoading ? (
                      <Loader2 className="animate-spin" size={16} />
                    ) : (
                      <Check size={16} />
                    )}
                    Accetta
                  </button>
                )}
                {isMioTurno() && (
                  <button
                    onClick={() => setShowPropostaEditor(true)}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white font-bold text-sm flex items-center gap-2"
                  >
                    <Send size={16} />
                    {transazione.ultima_proposta_destinatario ? 'Rilancio' : 'Controproponi'}
                  </button>
                )}
                <button
                  onClick={handleRifiuta}
                  disabled={actionLoading}
                  className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-white font-bold text-sm flex items-center gap-2 disabled:opacity-50"
                >
                  {actionLoading ? (
                    <Loader2 className="animate-spin" size={16} />
                  ) : (
                    <XCircle size={16} />
                  )}
                  Rifiuta
                </button>
              </div>
            )}
          </Dialog.Panel>
        </div>
      </Dialog>

      {showPropostaEditor && (
        <PropostaEditorModal
          transazione={transazione}
          onClose={() => setShowPropostaEditor(false)}
          onSave={handleProposta}
          onLogout={onLogout}
        />
      )}
    </>
  );
};

export default TransazioneDetailModal;
