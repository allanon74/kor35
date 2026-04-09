import React, { useState, useEffect } from 'react';
import { X, Hammer, ShieldAlert, Check, Loader2, Coins, Send, Clock } from 'lucide-react';
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
         if (selectedTarget === 'ACADEMY') {
             // Accademia
             await forgiaOggetto(infusione.id, selectedCharacterData.id, true);
             setMsg({ type: 'success', text: 'Forgiatura Accademia avviata!' });
         } else if (selectedTarget) {
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

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center p-4 z-50">
       <div className="bg-gray-800 rounded-xl max-w-md w-full p-6 border border-gray-600 shadow-xl animate-fadeIn">
          
          <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
              <h3 className="text-xl font-bold text-white flex gap-2 items-center">
                  <Hammer className="text-amber-500" size={20}/> 
                  Forgia: {infusione.nome}
              </h3>
              <button onClick={onClose} className="text-gray-400 hover:text-white"><X/></button>
          </div>

          {isLoadingInfo ? (
              <div className="py-8 text-center text-gray-400"><Loader2 className="animate-spin inline mr-2"/> Analisi requisiti...</div>
          ) : (
              <div className="space-y-5">
                  
                  {/* FEEDBACK REQUISITI */}
                  {canForgeSelf ? (
                      <div className="bg-emerald-900/20 border border-emerald-700/50 p-3 rounded flex gap-3 items-center">
                          <Check className="text-emerald-500" size={24}/>
                          <div>
                              <h4 className="font-bold text-emerald-400 text-sm">Autosufficiente</h4>
                              <p className="text-emerald-200/70 text-xs">Hai tutti i requisiti. Procedi con la forgiatura.</p>
                          </div>
                      </div>
                  ) : (
                      <div className="bg-amber-900/20 border border-amber-700/50 p-3 rounded flex gap-3 items-center">
                          <ShieldAlert className="text-amber-500" size={24}/>
                          <div>
                              <h4 className="font-bold text-amber-400 text-sm">Requisiti Mancanti</h4>
                              <p className="text-amber-200/70 text-xs">{validationMsg}</p>
                          </div>
                      </div>
                  )}

                  {/* SELETTORE METODO (Solo se NON autosufficiente) */}
                  {!canForgeSelf && (
                      <div>
                          <label className="block text-xs font-bold text-gray-400 uppercase mb-1">Chiedi Aiuto</label>
                          <select 
                              className="w-full bg-gray-900 border-gray-600 text-white rounded p-2 focus:border-indigo-500 outline-none"
                              value={selectedTarget} 
                              onChange={e => setSelectedTarget(e.target.value)}
                          >
                              <option value="">-- Seleziona Chi Esegue --</option>
                              <option value="ACADEMY">🏛️ Accademia (200 CR)</option>
                              {capableArtisans.length > 0 && (
                                  <optgroup label="Artigiani Disponibili">
                                      {capableArtisans.map(a => (
                                          <option key={a.id} value={a.id}>👤 {a.nome}</option>
                                      ))}
                                  </optgroup>
                              )}
                          </select>
                      </div>
                  )}

                  {/* INPUT OFFERTA (Solo se Artigiano selezionato) */}
                  {selectedTarget && selectedTarget !== 'ACADEMY' && !canForgeSelf && (
                      <div className="animate-fadeIn">
                          <label className="block text-xs font-bold text-gray-400 mb-1">Offerta all'Artigiano (CR)</label>
                          <div className="relative">
                              <Coins className="absolute left-3 top-2.5 text-yellow-500" size={16}/>
                              <input 
                                  type="number" 
                                  min="0"
                                  className="w-full bg-gray-900 border-gray-600 text-white rounded p-2 pl-10 focus:border-yellow-500 outline-none"
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
                          {msg.text}
                      </div>
                  )}

                  {/* BOTTONE AZIONE */}
                  <button 
                      onClick={handleExecute} 
                      disabled={isProcessing || (!canForgeSelf && !selectedTarget)}
                      className={`
                          w-full py-2.5 rounded-lg font-bold flex justify-center items-center gap-2 transition-all
                          disabled:opacity-50 disabled:cursor-not-allowed
                          ${selectedTarget === 'ACADEMY' 
                              ? 'bg-yellow-600 hover:bg-yellow-500 text-white' 
                              : 'bg-emerald-600 hover:bg-emerald-500 text-white'}
                      `}
                  >
                      {isProcessing ? <Loader2 className="animate-spin"/> : (
                          selectedTarget === 'ACADEMY' ? <Coins size={18}/> : 
                          (canForgeSelf ? <Hammer size={18}/> : <Send size={18}/>)
                      )}
                      
                      {canForgeSelf 
                          ? 'Inizia Forgiatura (Fai da te)' 
                          : (selectedTarget === 'ACADEMY' ? 'Paga 200 CR e Avvia' : 'Invia Richiesta')}
                  </button>
              </div>
          )}
       </div>
    </div>
  );
};

export default ForgingModal;