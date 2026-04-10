import React, { useState, useEffect } from 'react';
import { getAssemblyRequests, acceptAssemblyRequest, rejectAssemblyRequest } from '../api';
import { Check, X, Hammer, Loader2, User, Box } from 'lucide-react';

const JobRequestsWidget = ({ characterId }) => {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [processingId, setProcessingId] = useState(null); // Traccia quale richiesta stiamo gestendo

  // --- CARICAMENTO RICHIESTE ---
  const fetchRequests = async () => {
    try {
      const data = await getAssemblyRequests();
      // Filtra le richieste:
      // 1. Dove IO sono l'artigiano (artigiano === characterId)
      // 2. Che sono ancora IN ATTESA (stato === 'PEND')
      // Nota: Adatta 'PEND' se il tuo backend usa un codice diverso (es. 'IN_ATTESA')
      const myJobs = data.filter(r => 
        (r.artigiano === characterId || r.artigiano?.id === characterId) && 
        r.stato === 'PEND' 
      );
      setRequests(myJobs);
    } catch (error) {
      console.error("Errore caricamento richieste lavoro:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (characterId) fetchRequests();
    // Opzionale: Polling ogni 30 secondi per nuovi lavori
    const interval = setInterval(() => { if(characterId) fetchRequests(); }, 30000);
    return () => clearInterval(interval);
  }, [characterId]);

  // --- GESTIONE ACCETTAZIONE ---
  const handleAccept = async (reqId) => {
    setProcessingId(reqId);
    try {
      await acceptAssemblyRequest(reqId);
      // Rimuovi la richiesta dalla lista locale con animazione (simulata)
      setRequests(prev => prev.filter(r => r.id !== reqId));
      // Feedback utente (puoi sostituire con un toast notification)
      alert("Lavoro completato! I crediti sono stati trasferiti."); 
    } catch (error) {
      alert("Errore durante l'accettazione: " + error.message);
    } finally {
      setProcessingId(null);
    }
  };

  // --- GESTIONE RIFIUTO ---
  const handleReject = async (reqId) => {
    if(!confirm("Sei sicuro di voler rifiutare questo lavoro?")) return;
    
    setProcessingId(reqId);
    try {
      await rejectAssemblyRequest(reqId);
      setRequests(prev => prev.filter(r => r.id !== reqId));
    } catch (error) {
      alert("Errore durante il rifiuto: " + error.message);
    } finally {
      setProcessingId(null);
    }
  };

  // Se sta caricando o non ci sono richieste, non mostrare nulla (o mostra spinner)
  if (loading && requests.length === 0) return null;
  if (requests.length === 0) return null;

  return (
    <div className="mb-6 bg-gray-800 border border-amber-500/50 rounded-lg overflow-hidden shadow-lg animate-fadeIn ring-1 ring-amber-500/20">
      {/* Header Widget */}
      <div className="bg-amber-900/40 px-4 py-3 border-b border-amber-500/30 flex items-center justify-between">
        <div className="flex items-center gap-2">
            <Hammer className="text-amber-500" size={20} />
            <h3 className="font-bold text-amber-100 text-sm uppercase tracking-wider">
                Richieste di Lavoro ({requests.length})
            </h3>
        </div>
        <span className="flex h-2 w-2 relative">
            <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
            <span className="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
        </span>
      </div>
      
      {/* Lista Richieste */}
      <div className="divide-y divide-gray-700">
        {requests.map(req => (
          <div key={req.id} className="p-4 flex flex-col md:flex-row justify-between items-start md:items-center gap-4 hover:bg-gray-700/30 transition-colors">
            
            {/* Dettagli Lavoro */}
            <div className="space-y-1 w-full">
              <div className="flex items-center gap-2 text-sm text-gray-300">
                <User size={14} className="text-indigo-400"/>
                <span className="font-bold text-white">{req.committente_nome || "Cliente"}</span> 
                <span>
                  {req.tipo_operazione === 'FORG' && 'richiede forgiatura:'}
                  {req.tipo_operazione === 'INST' && 'richiede installazione:'}
                  {req.tipo_operazione === 'RIMO' && 'richiede rimozione:'}
                  {req.tipo_operazione === 'GRAF' && 'propone operazione chirurgica:'}
                  {!req.tipo_operazione && 'richiede installazione:'}
                </span>
              </div>
              
              {/* Per FORG: mostra solo infusione */}
              {req.tipo_operazione === 'FORG' && (
                <div className="flex items-center gap-2 bg-gray-900/50 p-2 rounded border border-gray-600/50">
                  <Box size={16} className="text-purple-400" />
                  <span className="text-purple-200 font-mono text-sm">{req.infusione_nome || "Infusione"}</span>
                </div>
              )}
              
              {/* Per GRAF: mostra infusione e slot */}
              {req.tipo_operazione === 'GRAF' && (
                <div className="flex items-center gap-2 bg-gray-900/50 p-2 rounded border border-gray-600/50">
                  <Box size={16} className="text-red-400" />
                  <span className="text-red-200 font-mono text-sm">{req.infusione_nome || req.forgiatura_nome || "Innesto"}</span>
                  {req.slot_destinazione && (
                    <>
                      <span className="text-gray-500">➔</span>
                      <span className="text-orange-200 font-mono text-sm">Slot {req.slot_destinazione}</span>
                    </>
                  )}
                </div>
              )}
              
              {/* Per INST/RIMO: mostra componente e host */}
              {(!req.tipo_operazione || req.tipo_operazione === 'INST' || req.tipo_operazione === 'RIMO') && (
                <div className="flex items-center gap-2 bg-gray-900/50 p-2 rounded border border-gray-600/50">
                  <Box size={16} className="text-cyan-400" />
                  <span className="text-cyan-200 font-mono text-sm">{req.componente_nome}</span>
                  <span className="text-gray-500">{req.tipo_operazione === 'RIMO' ? '←' : '➔'}</span>
                  <span className="text-emerald-200 font-mono text-sm">{req.host_nome}</span>
                </div>
              )}

              <div className="flex items-center gap-2 text-xs mt-1">
                 <span className="text-yellow-500 font-bold bg-yellow-500/10 px-2 py-0.5 rounded">
                    Offerta: {req.offerta_crediti} CR
                 </span>
                 <span className="text-gray-500">
                    {new Date(req.data_creazione).toLocaleDateString()}
                 </span>
              </div>
            </div>

            {/* Pulsanti Azione */}
            <div className="flex gap-2 w-full md:w-auto shrink-0">
              <button 
                onClick={() => handleAccept(req.id)}
                disabled={!!processingId}
                className="flex-1 md:flex-none bg-emerald-600 hover:bg-emerald-500 text-white px-4 py-2 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 disabled:cursor-not-allowed font-medium text-sm shadow-lg shadow-emerald-900/20"
              >
                {processingId === req.id ? <Loader2 className="animate-spin" size={16}/> : <Check size={16} />}
                Accetta
              </button>
              
              <button 
                onClick={() => handleReject(req.id)}
                disabled={!!processingId}
                className="flex-1 md:flex-none bg-red-900/30 hover:bg-red-900/60 text-red-300 border border-red-800/50 px-3 py-2 rounded-lg flex items-center justify-center gap-2 transition-all active:scale-95 disabled:opacity-50 text-sm"
              >
                <X size={16} />
                Rifiuta
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default JobRequestsWidget;