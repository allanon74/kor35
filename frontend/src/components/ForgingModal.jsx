import React, { useState, useEffect } from 'react';
import { X, Hammer, ShieldAlert, Check, Loader2, Send, Coins } from 'lucide-react';
import { confirmCloseIfDirty } from '../hooks/useDirtyModalClose';
import { useCharacter } from './CharacterContext';
import { forgiaOggetto, getCapableArtisans, createForgingRequest, validateForging } from '../api';

const ForgingModal = ({ infusione, onClose, onRefresh }) => {
  const { selectedCharacterData } = useCharacter();
  
  const [canForgeSelf, setCanForgeSelf] = useState(false);
  const [validationMsg, setValidationMsg] = useState('');
  const [capableArtisans, setCapableArtisans] = useState([]);
  const [isLoadingInfo, setIsLoadingInfo] = useState(true);
  
  const [selectedTarget, setSelectedTarget] = useState(''); // ''=Self (if allowed), or ArtisanID/ACADEMY
  const [offerCredits, setOfferCredits] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [msg, setMsg] = useState({ type: '', text: '' });

  // INITIAL CHECK
  useEffect(() => {
    const loadData = async () => {
      setIsLoadingInfo(true);
      try {
        // 1. Controlla se IO ho i requisiti
        const valData = await validateForging(selectedCharacterData.id, infusione.id);
        
        if (valData.can_forge) {
            // CASO A: Ho i requisiti -> Posso forgiare solo io.
            setCanForgeSelf(true);
        } else {
            // CASO B: Non ho i requisiti -> Devo chiedere aiuto.
            setCanForgeSelf(false);
            setValidationMsg(valData.reason || "Requisiti mancanti.");
            
            // Carica gli artigiani solo se serve aiuto
            const artisans = await getCapableArtisans(selectedCharacterData.id, null, null, infusione.id);
            setCapableArtisans(artisans || []);
        }
      } catch (e) {
        console.error(e);
        setMsg({ type: 'error', text: "Errore di comunicazione col server." });
      } finally {
        setIsLoadingInfo(false);
      }
    };
    loadData();
  }, [infusione, selectedCharacterData]);

  const handleExecute = async () => {
    setIsProcessing(true);
    setMsg({});
    
    try {
      if (canForgeSelf) {
         // FAI DA TE (Timer standard)
         await forgiaOggetto(infusione.id, selectedCharacterData.id, false);
         setMsg({ type: 'success', text: 'Forgiatura avviata! Controlla la coda.' });
      } else {
         // AIUTO ESTERNO
         if (selectedTarget) {
             // Artigiano
             const art = capableArtisans.find(a => a.id == selectedTarget);
             const validOffer = parseInt(offerCredits) || 0;
             if (validOffer < 0) {
                 throw new Error("L'offerta deve essere un valore positivo.");
             }
             await createForgingRequest(selectedCharacterData.id, infusione.id, art.nome, validOffer);
             setMsg({ type: 'success', text: `Richiesta inviata a ${art.nome}!` });
         } else {
             throw new Error("Seleziona un metodo.");
         }
      }
      
      setTimeout(() => { onRefresh(); onClose(); }, 2000);
    } catch (err) {
      setMsg({ type: 'error', text: err.message || "Operazione fallita" });
    } finally {
      setIsProcessing(false);
    }
  };

  const requestClose = () =>
    confirmCloseIfDirty(
      (Boolean(selectedTarget) || Number(offerCredits) > 0) && !isProcessing,
      onClose,
      'La forgiatura non è stata completata. Chiudere comunque?'
    );

  return (
    <div
      className="fixed inset-0 bg-black/80 flex items-end sm:items-center justify-center p-0 sm:p-4 z-50"
      onClick={requestClose}
    >
       <div
         className="bg-gray-800 rounded-t-2xl sm:rounded-xl max-w-md w-full max-h-[92vh] overflow-y-auto p-4 sm:p-6 border border-gray-600 shadow-xl animate-fadeIn min-w-0"
         onClick={(e) => e.stopPropagation()}
       >
          
          <div className="flex justify-between items-start gap-3 mb-4 border-b border-gray-700 pb-2">
              <h3 className="text-lg sm:text-xl font-bold text-white flex gap-2 items-start min-w-0">
                  <Hammer className="text-amber-500 shrink-0 mt-0.5" size={20}/> 
                  <span className="break-words">Forgia: {infusione.nome}</span>
              </h3>
              <button
                type="button"
                onClick={requestClose}
                className="min-h-11 min-w-11 shrink-0 flex items-center justify-center text-gray-400 hover:text-white rounded-lg"
                aria-label="Chiudi"
              >
                <X/>
              </button>
          </div>

          {isLoadingInfo ? (
              <div className="py-8 text-center text-gray-400"><Loader2 className="animate-spin inline mr-2"/> Analisi requisiti...</div>
          ) : (
              <div className="space-y-5">
                  
                  {/* FEEDBACK REQUISITI */}
                  {canForgeSelf ? (
                      <div className="bg-emerald-900/20 border border-emerald-700/50 p-3 rounded flex gap-3 items-center">
                          <Check className="text-emerald-500 shrink-0" size={24}/>
                          <div className="min-w-0">
                              <h4 className="font-bold text-emerald-400 text-sm">Autosufficiente</h4>
                              <p className="text-emerald-200/70 text-xs">Hai tutti i requisiti. Procedi con la forgiatura.</p>
                          </div>
                      </div>
                  ) : (
                      <div className="bg-amber-900/20 border border-amber-700/50 p-3 rounded flex gap-3 items-center">
                          <ShieldAlert className="text-amber-500 shrink-0" size={24}/>
                          <div className="min-w-0">
                              <h4 className="font-bold text-amber-400 text-sm">Requisiti Mancanti</h4>
                              <p className="text-amber-200/70 text-xs break-words">{validationMsg}</p>
                          </div>
                      </div>
                  )}

                  {/* SELETTORE METODO (Solo se NON autosufficiente) */}
                  {!canForgeSelf && (
                      <div>
                          <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Chiedi Aiuto</label>
                          <select 
                              className="w-full min-h-11 bg-gray-900 border border-gray-600 text-white rounded p-2 focus:border-indigo-500 outline-none"
                              value={selectedTarget} 
                              onChange={e => setSelectedTarget(e.target.value)}
                          >
                              <option value="">-- Seleziona Chi Esegue --</option>
                              {capableArtisans.length > 0 && (
                                  <optgroup label="Artigiani Disponibili">
                                      {capableArtisans.map(a => (
                                          <option key={a.id} value={a.id}>{a.nome}</option>
                                      ))}
                                  </optgroup>
                              )}
                          </select>
                      </div>
                  )}

                  {/* INPUT OFFERTA (Solo se Artigiano selezionato) */}
                  {selectedTarget && selectedTarget !== 'ACADEMY' && !canForgeSelf && (
                      <div className="animate-fadeIn">
                          <label className="block text-xs font-bold text-gray-400 mb-1">Offerta all&apos;Artigiano (CR)</label>
                          <div className="relative">
                              <Coins className="absolute left-3 top-1/2 -translate-y-1/2 text-yellow-500" size={16}/>
                              <input 
                                  type="number" 
                                  min="0"
                                  className="w-full min-h-11 bg-gray-900 border border-gray-600 text-white rounded p-2 pl-10 focus:border-yellow-500 outline-none"
                                  value={offerCredits} 
                                  onChange={e=>setOfferCredits(parseInt(e.target.value) || 0)} 
                                  placeholder="0"
                              />
                          </div>
                      </div>
                  )}
                  
                  {/* MESSAGGI STATO */}
                  {msg.text && (
                      <div className={`p-3 rounded text-sm border flex items-center gap-2 ${msg.type === 'error' ? 'bg-red-900/20 border-red-800 text-red-300' : 'bg-emerald-900/20 border-emerald-800 text-emerald-300'}`}>
                          {msg.type === 'error' ? <ShieldAlert size={16}/> : <Check size={16}/>}
                          <span className="break-words">{msg.text}</span>
                      </div>
                  )}

                  {/* BOTTONE AZIONE */}
                  <button 
                      type="button"
                      onClick={handleExecute} 
                      disabled={isProcessing || (!canForgeSelf && !selectedTarget)}
                      className={`
                          w-full min-h-11 py-2.5 rounded-lg font-bold flex justify-center items-center gap-2 transition-all touch-manipulation
                          disabled:opacity-50 disabled:cursor-not-allowed
                          bg-emerald-600 hover:bg-emerald-500 text-white
                      `}
                  >
                      {isProcessing ? <Loader2 className="animate-spin"/> : (
                          canForgeSelf ? <Hammer size={18}/> : <Send size={18}/>
                      )}
                      
                      {canForgeSelf 
                          ? 'Inizia Forgiatura (Fai da te)' 
                          : 'Invia Richiesta'}
                  </button>
              </div>
          )}
       </div>
    </div>
  );
};

export default ForgingModal;
