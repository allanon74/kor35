import React, { useState, useEffect } from 'react';
import { Dialog } from '@headlessui/react';
import { X, Send, Loader2, Plus } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { getOggettoDetail } from '../api';

const PropostaEditorModal = ({ transazione, onClose, onSave, onLogout }) => {
  const { selectedCharacterData, selectedCharacterId } = useCharacter();
  const [loading, setLoading] = useState(false);
  const [loadingOggetti, setLoadingOggetti] = useState({});
  const [oggettiAltroPersonaggio, setOggettiAltroPersonaggio] = useState([]);
  const [manualOggettoId, setManualOggettoId] = useState('');
  const [formData, setFormData] = useState({
    crediti_da_dare: 0,
    crediti_da_ricevere: 0,
    oggetti_da_dare: [],
    oggetti_da_ricevere: [],
    messaggio: ''
  });

  // Ottieni oggetti disponibili dall'inventario
  const oggettiDisponibili = selectedCharacterData?.oggetti || [];

  // Determina chi è l'altro personaggio
  const altroPersonaggioId = transazione?.iniziatore === selectedCharacterId 
    ? transazione?.destinatario 
    : transazione?.iniziatore;

  // Carica oggetti dall'altra proposta se esiste
  useEffect(() => {
    if (!transazione || !selectedCharacterId) return;
    
    const loadOggettiAltro = async () => {
      // Determina se sono l'iniziatore o il destinatario
      const sonoIniziatore = transazione.iniziatore?.id === selectedCharacterId || transazione.iniziatore === selectedCharacterId;
      
      // Se c'è già una proposta dall'altro, estrai i loro oggetti proposti
      const altraProposta = sonoIniziatore
        ? transazione.ultima_proposta_destinatario
        : transazione.ultima_proposta_iniziatore;
      
      if (altraProposta?.oggetti_da_dare && altraProposta.oggetti_da_dare.length > 0) {
        // Questi sono gli oggetti che l'altro ha proposto di dare (quindi io li riceverei)
        const oggettiIds = altraProposta.oggetti_da_dare;
        const nuoviOggetti = [];
        
        // Carica i dettagli per ogni oggetto se sono solo ID
        for (const oggettoId of oggettiIds) {
          const id = typeof oggettoId === 'object' ? oggettoId.id : oggettoId;
          if (typeof oggettoId === 'object') {
            // Già un oggetto completo
            nuoviOggetti.push(oggettoId);
          } else {
            // Solo ID, recupera i dettagli
            try {
              const dettagli = await getOggettoDetail(id, onLogout);
              if (dettagli) {
                nuoviOggetti.push(dettagli);
              } else {
                // Se fallisce, aggiungi comunque l'ID come fallback
                nuoviOggetti.push(id);
              }
            } catch (error) {
              console.warn(`Impossibile recuperare dettagli oggetto ${id}:`, error);
              // Aggiungi comunque l'ID come fallback
              nuoviOggetti.push(id);
            }
          }
        }
        
        setOggettiAltroPersonaggio(nuoviOggetti);
      }
    };
    
    loadOggettiAltro();
  }, [transazione, selectedCharacterId, onLogout]);

  // Funzione per recuperare dettagli oggetto tramite ID
  const fetchOggettoById = async (oggettoId) => {
    if (!oggettoId) return null;
    
    const id = parseInt(oggettoId);
    if (isNaN(id)) {
      alert("ID oggetto non valido!");
      return null;
    }

    // Verifica se l'oggetto è già nella lista
    if (oggettiAltroPersonaggio.find(o => (typeof o === 'object' ? o.id : o) === id)) {
      alert("Questo oggetto è già nella lista!");
      setManualOggettoId('');
      return null;
    }

    setLoadingOggetti(prev => ({ ...prev, [id]: true }));
    try {
      // Recupera l'oggetto dall'endpoint API
      const response = await getOggettoDetail(id, onLogout);
      
      if (response) {
        setOggettiAltroPersonaggio(prev => [...prev, response]);
        setManualOggettoId('');
      }
      return response;
    } catch (error) {
      console.error("Errore recupero oggetto:", error);
      alert("Impossibile recuperare l'oggetto. Verifica che l'ID sia corretto e che tu abbia i permessi per visualizzarlo.");
      return null;
    } finally {
      setLoadingOggetti(prev => ({ ...prev, [id]: false }));
    }
  };

  const handleAddOggettoManuale = () => {
    if (!manualOggettoId.trim()) return;
    fetchOggettoById(manualOggettoId.trim());
  };

  const handleSave = async () => {
    if (formData.crediti_da_dare < 0 || formData.crediti_da_ricevere < 0) {
      alert("I crediti non possono essere negativi!");
      return;
    }

    if (formData.crediti_da_dare > selectedCharacterData?.crediti) {
      alert("Non hai abbastanza crediti!");
      return;
    }

    setLoading(true);
    try {
      await onSave(formData);
      onClose();
    } catch (error) {
      alert("Errore: " + error.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleOggetto = (oggettoId, tipo) => {
    const field = tipo === 'dare' ? 'oggetti_da_dare' : 'oggetti_da_ricevere';
    setFormData(prev => ({
      ...prev,
      [field]: prev[field].includes(oggettoId)
        ? prev[field].filter(id => id !== oggettoId)
        : [...prev[field], oggettoId]
    }));
  };

  return (
    <Dialog open={true} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-3xl bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-h-[90vh] flex flex-col">
          {/* Header */}
          <div className="flex justify-between items-center p-4 border-b border-gray-700 bg-gray-800/50 rounded-t-xl">
            <Dialog.Title className="text-xl font-bold text-white">
              {transazione?.ultima_proposta_iniziatore && transazione?.ultima_proposta_destinatario
                ? 'Rilancio Proposta'
                : 'Controproposta'}
            </Dialog.Title>
            <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
              <X size={24} />
            </button>
          </div>

          {/* Content */}
          <div className="p-6 overflow-y-auto grow custom-scrollbar space-y-6">
            {/* Crediti */}
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-bold text-gray-400 mb-2">
                  Crediti che DAI
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.crediti_da_dare}
                  onChange={e => setFormData({...formData, crediti_da_dare: parseFloat(e.target.value) || 0})}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="0.00"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Disponibili: {selectedCharacterData?.crediti || 0} CR
                </p>
              </div>
              <div>
                <label className="block text-sm font-bold text-gray-400 mb-2">
                  Crediti che RICEVI
                </label>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  value={formData.crediti_da_ricevere}
                  onChange={e => setFormData({...formData, crediti_da_ricevere: parseFloat(e.target.value) || 0})}
                  className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white"
                  placeholder="0.00"
                />
              </div>
            </div>

            {/* Oggetti da Dare */}
            <div>
              <label className="block text-sm font-bold text-gray-400 mb-2">
                Oggetti che DAI
              </label>
              <div className="bg-gray-800 rounded-lg p-3 max-h-40 overflow-y-auto space-y-2">
                {oggettiDisponibili.length === 0 ? (
                  <p className="text-xs text-gray-500 italic">Nessun oggetto disponibile</p>
                ) : (
                  oggettiDisponibili.map(oggetto => (
                    <label key={oggetto.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-700 p-2 rounded">
                      <input
                        type="checkbox"
                        checked={formData.oggetti_da_dare.includes(oggetto.id)}
                        onChange={() => toggleOggetto(oggetto.id, 'dare')}
                        className="rounded"
                      />
                      <span className="text-sm text-white">{oggetto.nome}</span>
                    </label>
                  ))
                )}
              </div>
            </div>

            {/* Oggetti da Ricevere */}
            <div>
              <label className="block text-sm font-bold text-gray-400 mb-2">
                Oggetti che RICEVI
              </label>
              
              {/* Input per aggiungere oggetto manualmente tramite ID */}
              <div className="mb-2 flex gap-2">
                <input
                  type="number"
                  value={manualOggettoId}
                  onChange={e => setManualOggettoId(e.target.value)}
                  onKeyPress={e => e.key === 'Enter' && handleAddOggettoManuale()}
                  placeholder="Inserisci ID oggetto..."
                  className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
                />
                <button
                  onClick={handleAddOggettoManuale}
                  disabled={!manualOggettoId.trim() || loadingOggetti[parseInt(manualOggettoId)]}
                  className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white text-sm font-bold disabled:opacity-50 flex items-center gap-1"
                >
                  {loadingOggetti[parseInt(manualOggettoId)] ? (
                    <Loader2 className="animate-spin" size={14} />
                  ) : (
                    <Plus size={14} />
                  )}
                  Aggiungi
                </button>
              </div>

              {/* Lista oggetti disponibili da ricevere */}
              <div className="bg-gray-800 rounded-lg p-3 max-h-40 overflow-y-auto space-y-2">
                {oggettiAltroPersonaggio.length === 0 ? (
                  <p className="text-xs text-gray-500 italic">
                    {transazione?.ultima_proposta_iniziatore || transazione?.ultima_proposta_destinatario
                      ? "Nessun oggetto proposto dall'altro personaggio. Inserisci manualmente gli ID degli oggetti che vuoi ricevere."
                      : "Inserisci gli ID degli oggetti che vuoi ricevere"}
                  </p>
                ) : (
                  oggettiAltroPersonaggio.map(oggetto => {
                    const oggettoId = typeof oggetto === 'object' ? oggetto.id : oggetto;
                    const oggettoNome = typeof oggetto === 'object' ? oggetto.nome : `Oggetto #${oggettoId}`;
                    return (
                      <label key={oggettoId} className="flex items-center gap-2 cursor-pointer hover:bg-gray-700 p-2 rounded">
                        <input
                          type="checkbox"
                          checked={formData.oggetti_da_ricevere.includes(oggettoId)}
                          onChange={() => toggleOggetto(oggettoId, 'ricevere')}
                          className="rounded"
                        />
                        <span className="text-sm text-white">{oggettoNome}</span>
                        {typeof oggetto === 'object' && oggetto.descrizione && (
                          <span className="text-xs text-gray-500 ml-auto">({oggetto.descrizione.substring(0, 30)}...)</span>
                        )}
                      </label>
                    );
                  })
                )}
              </div>
            </div>

            {/* Messaggio */}
            <div>
              <label className="block text-sm font-bold text-gray-400 mb-2">
                Messaggio (opzionale)
              </label>
              <textarea
                value={formData.messaggio}
                onChange={e => setFormData({...formData, messaggio: e.target.value})}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white min-h-[100px]"
                placeholder="Aggiungi un messaggio alla proposta..."
              />
            </div>
          </div>

          {/* Footer */}
          <div className="p-4 border-t border-gray-700 flex justify-end gap-3">
            <button
              onClick={onClose}
              className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-white font-bold text-sm"
            >
              Annulla
            </button>
            <button
              onClick={handleSave}
              disabled={loading}
              className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white font-bold text-sm flex items-center gap-2 disabled:opacity-50"
            >
              {loading ? (
                <>
                  <Loader2 className="animate-spin" size={16} />
                  Invio...
                </>
              ) : (
                <>
                  <Send size={16} />
                  Invia Proposta
                </>
              )}
            </button>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default PropostaEditorModal;
