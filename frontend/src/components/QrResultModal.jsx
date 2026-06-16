import React, { useState, useEffect, useRef } from 'react';
import { X, Loader, Scan, Eye, Grab, Sparkles, User, FileText, Bot, Timer, ArrowRightLeft } from 'lucide-react';
import { richiediTransazione, rubaOggetto, acquisisciItem, createTransazioneAvanzata } from '../api'; 
import { useCharacter } from './CharacterContext';
import { useTimers } from '../hooks/useTimers';
import PropostaEditorModal from './PropostaEditorModal';

//##################################################################
// ## COMPONENTE HELPER 1: MODALE "VEDI OGGETTO" ##
//##################################################################
const OggettoDetailModal = ({ oggetto, onClose }) => {
  return (
    // Overlay (z-index 60, sopra la modale QR che è z-50)
    <div className="fixed inset-0 z-60 flex items-center justify-center bg-black bg-opacity-80 p-4">
      <div className="flex flex-col w-full max-w-md bg-gray-900 rounded-lg shadow-2xl overflow-hidden border border-indigo-500">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-indigo-400">{oggetto.nome}</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white"
            aria-label="Chiudi"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Contenuto */}
        <div className="p-6 overflow-y-auto text-white space-y-4 max-h-[60vh]">
          <p className="text-gray-300">{oggetto.descrizione || "Nessuna descrizione."}</p>
          
          {/* Mostra tutti i dati grezzi dell'oggetto */}
          <details className="mt-4 bg-gray-950 rounded-lg">
            <summary className="text-sm font-semibold text-gray-500 p-2 cursor-pointer">Mostra Dati Grezzi Oggetto</summary>
            <pre className="p-3 overflow-x-auto text-xs text-yellow-300">
              {JSON.stringify(oggetto, null, 2)}
            </pre>
          </details>
        </div>

      </div>
    </div>
  );
};


//##################################################################
// ## FUNZIONE HELPER 2: LOGICA AURA ##
//##################################################################
const getOggettiVisibili = (oggettiDaFiltrare, personaggioAttivo) => {
  if (!personaggioAttivo || !oggettiDaFiltrare || oggettiDaFiltrare.length === 0) {
    return [];
  }

  // !!! --- ASSUNZIONE AURA 1 --- !!!
  // Assumo che i punteggi di aura del PG ATTIVO (che scansiona) 
  // si trovino in `personaggioAttivo.modificatori_calcolati`.
  const aurePersonaggio = personaggioAttivo.modificatori_calcolati;
  
  if (!aurePersonaggio) {
    console.warn("Dati 'modificatori_calcolati' non trovati nel personaggio attivo. Impossibile filtrare per aura.");
    return [];
  }

  return oggettiDaFiltrare.filter(obj => {
    // !!! --- ASSUNZIONE AURA 2 --- !!!
    // Assumo che ogni OGGETTO scansionato abbia un campo stringa 'aura_richiesta'
    const auraRichiesta = obj.aura_richiesta; 

    if (!auraRichiesta) {
      // Se l'oggetto non ha un'aura_richiesta, è visibile a tutti.
      return true;
    }

    const punteggioAura = aurePersonaggio[auraRichiesta] || 0;
    return punteggioAura >= 1;
  });
};


//##################################################################
// ## VISTE QR: TIPO MANIFESTO / A_VISTA (3a, 3e) - MODIFICATO ##
//##################################################################
const ManifestoView = ({ data }) => {
  const canRead = data.puo_leggere !== false;
  const blockMsg = data.messaggio_accesso;

  // Creiamo un template HTML completo da passare all'iframe.
  // Questo ci permette di controllare STILI e COMPORTAMENTO del testo.
  const htmlContent = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        /* Stile pergamena */
        body {
          background-color: #FFFBEB; /* Colore bg-amber-50 */
          font-family: serif;      /* Font pergamena */
          color: #1f2937;         /* Colore text-gray-800 */
          padding: 1rem;
          font-size: 1.125rem;     /* text-lg */
          margin: 0;               /* Rimuove margini default */
          
          /* --- I FIX PER IL WRAPPING (ora applicati DENTRO l'iframe) --- */
          
          /* 1. Rispetta i <br> e \n E fa il wrap del testo */
          white-space: pre-wrap;
          
          /* 2. Forza l'interruzione di parole molto lunghe */
          overflow-wrap: break-word;
          word-break: break-word;
        }
        
        /* Regola "martello" per forzare il wrapping anche
           dentro tag <p> o <pre> che arrivano dal DB.
        */
        * {
          white-space: pre-wrap !important;
          overflow-wrap: break-word !important;
          word-break: break-word !important;
        }
      </style>
    </head>
    <body>
      ${canRead ? (data.testo || '<i>Nessun testo per questo manifesto.</i>') : '<p><i>Contenuto non disponibile per il tuo personaggio.</i></p>'}
    </body>
    </html>
  `;

  return (
    <div>
      {/* Titolo */}
      <h3 className="text-2xl font-bold mb-4 text-amber-200 text-center">
        {data.nome || 'Manifesto'}
      </h3>
      {!canRead && blockMsg && (
        <p className="text-center text-amber-100/90 mb-3 text-sm border border-amber-700/50 rounded-md p-2 bg-amber-950/40">
          {blockMsg}
        </p>
      )}
      
      {/* Usiamo un iframe per isolare completamente lo stile 
        dell'HTML del manifesto dal resto dell'app.
      */}
      {canRead ? (
      <iframe
        srcDoc={htmlContent}
        title={data.nome || 'Manifesto'}
        // Applichiamo bordo e ombra all'iframe stesso
        className="w-full rounded-md shadow-inner"
        style={{
          height: '60vh', // Altezza fissa per l'area di scroll
          border: '4px solid rgba(120, 53, 15, 0.3)', // Bordo pergamena (amber-900/30)
          backgroundColor: '#FFFBEB' // Sfondo se l'iframe è lento
        }}
        // Sandbox per sicurezza
        sandbox="allow-same-origin" 
      />
      ) : (
        <p className="text-center text-gray-400 py-12">Manifesto non leggibile con questo personaggio.</p>
      )}
    </div>
  );
};

//##################################################################
// ## VISTA QR: INVENTARIO — ATTESA SECONDA SCANSIONE (30s) ##
//##################################################################
const InventarioAttesaConfermaView = ({ data }) => {
  const [secLeft, setSecLeft] = useState(0);
  useEffect(() => {
    const tick = () => {
      const t = data.pronto_dopo ? new Date(data.pronto_dopo).getTime() : 0;
      setSecLeft(Math.max(0, Math.ceil((t - Date.now()) / 1000)));
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, [data.pronto_dopo]);

  return (
    <div className="text-center space-y-4 py-4">
      <Timer className="mx-auto text-amber-500 mb-2" size={48} />
      <h3 className="text-xl font-bold text-amber-200">{data.nome || 'Inventario'}</h3>
      <p className="text-gray-300 px-2">
        Attendi ancora{' '}
        <span className="font-mono text-amber-400 text-3xl font-black">{secLeft}</span> s,
        poi <strong className="text-white">scansiona di nuovo lo stesso QR</strong> per aprire l&apos;inventario.
      </p>
    </div>
  );
};

//##################################################################
// ## VISTA QR: TIPO INVENTARIO (3b) ##
//##################################################################
const InventarioView = ({ data, onLogout }) => {
  const [cooldownEnd, setCooldownEnd] = useState(0); 
  const [cooldownTimer, setCooldownTimer] = useState(0);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [viewingOggetto, setViewingOggetto] = useState(null);
  
  const { selectedCharacterData } = useCharacter();
  const isInCooldown = Date.now() < cooldownEnd;

  useEffect(() => {
    if (isInCooldown) {
      const updateTimer = () => {
        const secondsLeft = Math.ceil((cooldownEnd - Date.now()) / 1000);
        setCooldownTimer(secondsLeft > 0 ? secondsLeft : 0);
      };
      updateTimer();
      const interval = setInterval(updateTimer, 1000);
      return () => clearInterval(interval);
    } else {
      setCooldownTimer(0);
    }
  }, [cooldownEnd, isInCooldown]);

  const handlePrendi = async (oggettoId, oggettoNome) => {
    if (isInCooldown) return;
    
    setMessage('Elaborazione...');
    setError('');
    setCooldownEnd(Date.now() + 10000); // Avvia cooldown 10s

    try {
      const response = await richiediTransazione(oggettoId, data.id, onLogout);
      setMessage(`Richiesta per '${oggettoNome}' inviata! Attendi conferma.`);
    } catch (err) {
      setError(err.message || 'Errore imprevisto.');
      setMessage('');
      setCooldownEnd(0); // Resetta cooldown in caso di errore
    }
  };

  const handleSottrai = async (obj) => {
    if (isInCooldown) return;
    setMessage('Elaborazione sottrazione...');
    setError('');
    setCooldownEnd(Date.now() + 10000);
    try {
      const response = await richiediTransazione(obj.id, data.id, onLogout);
      setMessage(response?.success || `Sottrazione richiesta per '${obj.nome}'.`);
    } catch (err) {
      setError(err.message || 'Errore imprevisto.');
      setMessage('');
      setCooldownEnd(0);
    }
  };

  const oggettiLista = (data.oggetti || []).filter((o) => o.visibile_inventario_qr !== false);

  return (
    <div>
      {viewingOggetto && (
        <OggettoDetailModal 
          oggetto={viewingOggetto} 
          onClose={() => setViewingOggetto(null)} 
        />
      )}

      <h3 className="text-2xl font-bold mb-4">{data.nome || 'Inventario'}</h3>
      {data.inventario_qr_confermato && (
        <p className="text-xs text-emerald-400/90 mb-2">Accesso inventario confermato (doppia scansione).</p>
      )}
      {error && <p className="text-red-400 mb-4 bg-red-900 bg-opacity-30 p-2 rounded">{error}</p>}
      {message && <p className="text-green-400 mb-4 bg-green-900 bg-opacity-30 p-2 rounded">{message}</p>}
      {isInCooldown && (
         <p className="text-yellow-400 mb-4 flex items-center">
           <Timer size={16} className="mr-2" />
           Cooldown "Prendi" attivo: {cooldownTimer}s
         </p>
      )}
      
      {oggettiLista.length === 0 && (
        <p className="text-gray-500 italic">Nessun oggetto visibile in questo inventario.</p>
      )}

      <ul className="space-y-3">
        {oggettiLista.map(obj => (
          <li key={obj.id} className="flex flex-col gap-2 p-3 bg-gray-700 rounded-md">
            <div className="flex justify-between items-center w-full">
              <span className="font-semibold">{obj.nome}</span>
              <div className="space-x-2">
                <button 
                  onClick={() => setViewingOggetto(obj)}
                  className="p-2 bg-blue-600 rounded hover:bg-blue-700" 
                  title="Vedi Dettagli"
                >
                  <Eye size={18} />
                </button>
                <button 
                  onClick={() => handlePrendi(obj.id, obj.nome)}
                  disabled={isInCooldown || obj.puo_prendere === false}
                  className={`p-2 bg-green-600 rounded hover:bg-green-700 ${isInCooldown || obj.puo_prendere === false ? 'opacity-50 cursor-not-allowed' : ''}`}
                  title={obj.puo_prendere === false ? 'Non puoi prendere questo oggetto' : 'Prendi'}
                >
                  <Grab size={18} />
                </button>
                {(obj.puo_smonta_materia || obj.puo_smonta_mod) && (
                  <button
                    onClick={() => handleSottrai(obj)}
                    disabled={isInCooldown}
                    className={`p-2 bg-amber-700 rounded hover:bg-amber-800 ${isInCooldown ? 'opacity-50 cursor-not-allowed' : ''}`}
                    title="Smonta/sottrai"
                  >
                    <Timer size={18} />
                  </button>
                )}
              </div>
            </div>
            {(obj.puo_smonta_materia || obj.puo_smonta_mod) && (
              <p className="text-[10px] text-gray-400">
                {obj.puo_smonta_materia && <span className="mr-2 text-amber-300">Smontabile come Materia (AMS)</span>}
                {obj.puo_smonta_mod && <span className="text-cyan-300">Smontabile come Mod (ATE)</span>}
                <span className="block text-gray-500 mt-1">Puoi usare il pulsante ambra per richiedere la sottrazione via inventario QR.</span>
              </p>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
};

//##################################################################
// ## VISTA QR: TIPO PERSONAGGIO (3c) ##
//##################################################################
const PersonaggioView = ({ data, onLogout, onStealSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [viewingOggetto, setViewingOggetto] = useState(null);
  const [showScambioModal, setShowScambioModal] = useState(false);
  const [selectedOggetto, setSelectedOggetto] = useState(null);

  const { selectedCharacterData } = useCharacter();
  
  const handleRuba = async (oggettoId, oggettoNome) => {
     if (isLoading) return;
     setIsLoading(true);
     setMessage('Tentativo di furto in corso...');
     setError('');

     try {
       const response = await rubaOggetto(oggettoId, data.id, onLogout, selectedCharacterId);
       setMessage(response.success || `Oggetto '${oggettoNome}' rubato!`);
       onStealSuccess(); 
     } catch (err) {
       setError(err.message || 'Errore imprevisto.');
       setMessage('');
     } finally {
       setIsLoading(false);
     }
  }

  const handleScambio = (oggetto) => {
    if (!data.id) {
      alert("Impossibile determinare il personaggio destinatario.");
      return;
    }
    setSelectedOggetto(oggetto);
    setShowScambioModal(true);
  };

  const handleSaveScambio = async (propostaData) => {
    if (!data.id) {
      throw new Error("Destinatario non specificato");
    }

    // Aggiungi l'oggetto selezionato agli oggetti da ricevere se non è già presente
    const oggettiDaRicevere = propostaData.oggetti_da_ricevere || [];
    if (selectedOggetto && !oggettiDaRicevere.includes(selectedOggetto.id)) {
      oggettiDaRicevere.push(selectedOggetto.id);
    }

    const propostaCompleta = {
      ...propostaData,
      oggetti_da_ricevere: oggettiDaRicevere
    };

    try {
      await createTransazioneAvanzata(data.id, propostaCompleta, onLogout);
      setMessage(`Scambio proposto! ${data.nome} riceverà la tua proposta.`);
      setShowScambioModal(false);
      setSelectedOggetto(null);
    } catch (error) {
      throw error;
    }
  };

  const oggettiVisibili = getOggettiVisibili(data.oggetti, selectedCharacterData);

  return (
    <div>
      {viewingOggetto && (
        <OggettoDetailModal 
          oggetto={viewingOggetto} 
          onClose={() => setViewingOggetto(null)} 
        />
      )}

      <h3 className="text-2xl font-bold mb-4 flex items-center"><User className="mr-2"/> {data.nome || 'Personaggio'}</h3>
      {error && <p className="text-red-400 mb-4 bg-red-900 bg-opacity-30 p-2 rounded">{error}</p>}
      {message && <p className="text-green-400 mb-4 bg-green-900 bg-opacity-30 p-2 rounded">{message}</p>}
      
      {oggettiVisibili.length === 0 && (
        <p className="text-gray-500 italic">Nessun oggetto visibile su questo personaggio.</p>
      )}

      <ul className="space-y-3">
        {oggettiVisibili.map(obj => (
          <li key={obj.id} className="flex justify-between items-center p-3 bg-gray-700 rounded-md">
            <span className="font-semibold">{obj.nome}</span>
            <div className="space-x-2">
              <button 
                onClick={() => setViewingOggetto(obj)}
                className="p-2 bg-blue-600 rounded hover:bg-blue-700" 
                title="Vedi Dettagli"
              >
                <Eye size={18} />
              </button>
              <button 
                onClick={() => handleRuba(obj.id, obj.nome)}
                disabled={isLoading}
                className={`p-2 bg-red-600 rounded hover:bg-red-700 ${isLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                title="Ruba"
              >
                {isLoading ? <Loader size={18} className="animate-spin" /> : <Bot size={18} />}
              </button>
              <button 
                onClick={() => handleScambio(obj)}
                disabled={isLoading || selectedCharacterId === data.id}
                className={`p-2 bg-indigo-600 rounded hover:bg-indigo-700 ${isLoading || selectedCharacterId === data.id ? 'opacity-50 cursor-not-allowed' : ''}`}
                title="Proponi Scambio"
              >
                <ArrowRightLeft size={18} />
              </button>
            </div>
          </li>
        ))}
      </ul>

      {/* Modal Scambio */}
      {showScambioModal && selectedOggetto && data.id && (
        <PropostaEditorModal
          transazione={null} // Nuova transazione
          onClose={() => {
            setShowScambioModal(false);
            setSelectedOggetto(null);
          }}
          onSave={handleSaveScambio}
          onLogout={onLogout}
        />
      )}
    </div>
  );
};

//##################################################################
// ## VISTA QR: TIPO OGGETTO / ATTIVATA (3d) ##
//##################################################################
const TecnicaAcquisizioneView = ({ qrId, tipo, data, onLogout, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { selectedCharacterId } = useCharacter();
  const canUse = data.tecnica_usabile !== false;
  const greyed = !canUse || data.gia_posseduta;

  const handleAcquisisci = async () => {
    if (!qrId) {
      setError("Errore: ID del QrCode non trovato per l'acquisizione.");
      return;
    }
    setIsLoading(true);
    setError('');
    try {
      const response = await acquisisciItem(qrId, onLogout, selectedCharacterId);
      setMessage(response.success || 'Tecnica aggiunta alle tue possedute!');
      setTimeout(() => onClose(), 2000);
    } catch (err) {
      setError(err.message || 'Errore imprevisto.');
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h3 className="text-2xl font-bold mb-4 flex items-center">
        <Sparkles className="mr-2" />
        {data.nome || 'Tecnica'}
        <span className="ml-2 text-xs uppercase text-gray-500">({tipo})</span>
      </h3>
      {greyed && (
        <p className="text-sm text-amber-200/90 mb-3 border border-amber-800/50 rounded p-2 bg-amber-950/30">
          {data.gia_posseduta
            ? 'Già nelle tue tecniche possedute. Puoi comunque consumare il QR se non l&apos;hai ancora fatto.'
            : (data.tecnica_usabilita_messaggio || 'Requisiti non soddisfatti: la tecnica resterà inattiva in scheda.')}
        </p>
      )}
      {data.TestoFormattato && (
        <div
          className="prose prose-invert prose-sm max-w-none mb-4 max-h-[40vh] overflow-y-auto border border-gray-700 rounded p-3 bg-gray-900/50"
          dangerouslySetInnerHTML={{ __html: data.TestoFormattato }}
        />
      )}
      {error && <p className="text-red-400 mb-4 bg-red-900 bg-opacity-30 p-2 rounded">{error}</p>}
      {message && <p className="text-green-400 mb-4 bg-green-900 bg-opacity-30 p-2 rounded">{message}</p>}
      {!message && (
        <button
          onClick={handleAcquisisci}
          disabled={isLoading}
          className={`w-full mt-4 px-4 py-3 text-white text-lg font-bold rounded-md shadow-lg disabled:opacity-50 ${
            greyed ? 'bg-gray-600 hover:bg-gray-600' : 'bg-purple-600 hover:bg-purple-700'
          }`}
        >
          {isLoading ? <Loader className="animate-spin mx-auto" /> : data.gia_posseduta ? 'Consuma QR (già posseduta)' : 'Aggiungi alle tecniche possedute'}
        </button>
      )}
    </div>
  );
};

const AcquisizioneView = ({ qrId, data, tipo, onLogout, onClose }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const { selectedCharacterId } = useCharacter();
  const canAcquireOggetto = tipo !== 'oggetto' || data.puo_acquisire_da_qr !== false;

  const handleAcquisisci = async () => {
    if (!qrId) {
        setError("Errore: ID del QrCode non trovato per l'acquisizione.");
        return;
    }
    setIsLoading(true);
    setError('');
    try {
      const response = await acquisisciItem(qrId, onLogout, selectedCharacterId);
      setMessage(response.success || "Oggetto acquisito!");
      setTimeout(() => {
        onClose();
      }, 2000);
    } catch (err) {
      setError(err.message || 'Errore imprevisto.');
      setIsLoading(false);
    }
  };

  return (
    <div>
      <h3 className="text-2xl font-bold mb-4 flex items-center">
        {tipo === 'oggetto' ? <Shield className="mr-2" /> : <Sparkles className="mr-2" />}
        {data.nome || 'Oggetto Raro'}
      </h3>
      {error && <p className="text-red-400 mb-4 bg-red-900 bg-opacity-30 p-2 rounded">{error}</p>}
      {message && <p className="text-green-400 mb-4 bg-green-900 bg-opacity-30 p-2 rounded">{message}</p>}
      
      <p className="text-gray-300 mb-4">{data.descrizione || 'Nessuna descrizione.'}</p>
      
      <details className="mt-4 bg-gray-900 rounded-lg">
        <summary className="text-sm font-semibold text-gray-500 p-2 cursor-pointer">Mostra Dati Grezzi</summary>
        <pre className="p-3 overflow-x-auto text-xs text-yellow-300">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
      
      {!message && ( // Nascondi il pulsante dopo l'acquisizione
        <button 
          onClick={handleAcquisisci}
          disabled={isLoading || !canAcquireOggetto}
          className="w-full mt-6 px-4 py-3 bg-purple-600 text-white text-lg font-bold rounded-md shadow-lg hover:bg-purple-700 disabled:opacity-50"
        >
          {isLoading ? <Loader className="animate-spin mx-auto" /> : 'Acquisisci'}
        </button>
      )}
      {tipo === 'oggetto' && data.puo_acquisire_da_qr === false && data.messaggio_acquisizione_qr && (
        <p className="text-amber-200 text-sm mt-2">{data.messaggio_acquisizione_qr}</p>
      )}
    </div>
  );
};


//##################################################################
// ## COMPONENTE MODALE PRINCIPALE (EXPORT) ##
//##################################################################
const QrResultModal = ({ data, onClose, onLogout, onStealSuccess }) => {
  
  const { addTimer } = useTimers(); // <--- Accediamo alla logica dei timer
  const lastProcessedQr = useRef(null); // Per evitare che il timer scatti multipli in caso di re-render

  useEffect(() => {
    if (!data) return;

    // Identifichiamo i dati del timer in base alla struttura del backend
    let timerToActivate = null;

    // CASO A: Il QR è di tipo timer puro (tipo_modello: "timer_attivato")
    if (data.tipo_modello === 'timer_attivato' && data.dati) {
      timerToActivate = {
        nome: data.dati.nome,
        endsAt: data.dati.scadenza, // Backend manda "scadenza" ISO
        alert_suono: true, // Fallback se non definiti
        notifica_push: true,
        messaggio_in_app: true
      };
    }
    if (data.tipo_modello === 'timer_innesco' && data.dati) {
      timerToActivate = {
        nome: data.dati.nome,
        endsAt: data.dati.scadenza,
        alert_suono: true,
        notifica_push: true,
        messaggio_in_app: true,
      };
    } 
    // CASO B: Il QR ha un timer associato come extra (es. Manifesto + Timer)
    else if (data.timer || data.dati?.timer_config) {
      const config = data.timer || data.dati.timer_config;
      timerToActivate = {
        nome: config.nome,
        duration: config.durata_secondi, // Qui il backend usa durata_secondi
        alert_suono: config.alert_suono,
        notifica_push: config.notifica_push,
        messaggio_in_app: config.messaggio_in_app
      };
    }

    const qrId = data.qrcode_id || data.dati?.qr_code_id || (data.tipo_modello === 'timer_attivato' ? data.dati?.nome : null);

    if (timerToActivate && qrId && lastProcessedQr.current !== qrId) {
      try {
        addTimer(timerToActivate);
        lastProcessedQr.current = qrId;
        console.log("⏱️ Timer innescato con successo");
      } catch (e) {
        console.error("Errore nell'innesco del timer:", e);
      }
    }
  }, [data, addTimer]);

  const renderContent = () => {
    if (!data) {
      return (
        <div className="flex justify-center items-center h-full">
          <Loader className="animate-spin text-indigo-400" size={48} />
        </div>
      );
    }
    
    const qrId = data.dati?.qr_code_id || data.qrcode_id; 

    switch (data.tipo_modello) {
      case 'negozio_mercante': {
        const NegozioMercanteModal = React.lazy(() => import('./NegozioMercanteModal'));
        return (
          <React.Suspense fallback={<Loader className="animate-spin mx-auto" />}>
            <NegozioMercanteModal
              negozioId={data.dati?.negozio_id}
              listinoIniziale={data.dati}
              onClose={onClose}
              onLogout={onLogout}
            />
          </React.Suspense>
        );
      }

      case 'manifesto':
      case 'a_vista':
        return <ManifestoView data={data.dati} />;

      case 'inventario_attesa_conferma':
        return <InventarioAttesaConfermaView data={data.dati} />;
      
      case 'inventario':
        return <InventarioView data={data.dati} onLogout={onLogout} />;

      case 'infusione':
      case 'tessitura':
      case 'cerimoniale':
        if (!qrId) {
          return <p className="text-red-400">Errore: Manca l&apos;ID del QrCode per l&apos;acquisizione.</p>;
        }
        return (
          <TecnicaAcquisizioneView
            qrId={qrId}
            tipo={data.tipo_modello}
            data={data.dati}
            onLogout={onLogout}
            onClose={onClose}
          />
        );
        
      case 'personaggio':
        return <PersonaggioView data={data.dati} onLogout={onLogout} onStealSuccess={onStealSuccess} />;

      case 'oggetto':
        if (!qrId) { 
            return <p className="text-red-400">Errore: Manca l'ID del QrCode per l'acquisizione.</p>
        }
        return <AcquisizioneView qrId={qrId} data={data.dati} tipo="oggetto" onLogout={onLogout} onClose={onClose} />;
      
      case 'attivata':
        if (!qrId) { 
            return <p className="text-red-400">Errore: Manca l'ID del QrCode per l'acquisizione.</p>
        }
        return <AcquisizioneView qrId={qrId} data={data.dati} tipo="attivata" onLogout={onLogout} onClose={onClose} />;

      // AGGIUNTO IL CASO MANCANTE PER IL TIMER PURO
      case 'timer_attivato':
      case 'timer_innesco':
        return (
          <div className="text-center py-10">
            <Timer size={80} className="mx-auto text-amber-500 mb-6 animate-pulse" />
            <h3 className="text-3xl font-black text-amber-400 uppercase tracking-tighter mb-4">{data.dati?.nome}</h3>
            <p className="text-gray-300 text-lg italic">{data.messaggio}</p>
            <div className="mt-8 pt-6 border-t border-white/10 text-[10px] text-gray-500 uppercase font-bold tracking-widest">
                Sincronizzazione Cronometro Eseguita
            </div>
          </div>
        );

      case 'nodo':
        return (
          <div className="text-center py-8">
            <Sparkles size={56} className="mx-auto text-cyan-400 mb-4" />
            <h3 className="text-2xl font-black text-cyan-300 uppercase tracking-tight">{data.dati?.nome || 'Nodo'}</h3>
            <p className="text-gray-300 mt-2">{data.messaggio}</p>
            {!!data.dati?.reward?.pool && (
              <p className="text-sm text-emerald-300 mt-4">
                +{data.dati.reward.pool.delta} {data.dati.reward.pool.sigla}
              </p>
            )}
            {!!data.dati?.reward?.crediti && (
              <p className="text-sm text-emerald-300 mt-4">+{data.dati.reward.crediti} crediti</p>
            )}
            {data.dati?.cooldown_until && (
              <p className="text-xs text-gray-500 mt-4">Cooldown fino a: {new Date(data.dati.cooldown_until).toLocaleString()}</p>
            )}
            {data.dati?.remaining_seconds > 0 && (
              <p className="text-xs text-amber-300 mt-3">Tempo residuo: {data.dati.remaining_seconds}s</p>
            )}
          </div>
        );

      case 'qrcode_scollegato':
        return (
          <div className="text-center">
            <Scan size={48} className="mx-auto text-yellow-400 mb-4" />
            <h3 className="text-2xl font-bold mb-2">QR Code non collegato</h3>
            <p className="text-gray-300">{data.messaggio}</p>
            <p className="text-xs text-gray-500 mt-2">ID: {data.qrcode_id}</p>
          </div>
        );

      case 'minigioco_bloccato':
        return (
          <div className="text-center py-8">
            <X size={56} className="mx-auto text-red-500 mb-4" />
            <h3 className="text-2xl font-bold text-red-400 mb-2">Accesso negato</h3>
            <p className="text-gray-300">{data.messaggio || 'Questo QR non è più disponibile per il tuo personaggio.'}</p>
          </div>
        );

      case 'errore':
        return (
          <div className="text-center py-8">
            <h3 className="text-2xl font-bold text-red-400 mb-2">Errore</h3>
            <p className="text-gray-300">{data.messaggio || data.error || 'Operazione non riuscita.'}</p>
          </div>
        );

      default:
        return (
          <div className="text-center">
            <h3 className="text-2xl font-bold mb-2 text-red-400">Errore</h3>
            <p className="text-gray-300">Tipo di QR Code non riconosciuto: {data.tipo_modello}</p>
            <pre className="text-xs text-left bg-gray-900 p-2 rounded-md mt-4 overflow-auto">
              {JSON.stringify(data, null, 2)}
            </pre>
          </div>
        );
    }
  };

  return (
    // Overlay (z-index 50)
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
      <div className="flex flex-col w-full h-full max-w-lg max-h-[90dvh] bg-gray-800 rounded-lg shadow-2xl overflow-hidden">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Risultato Scansione</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white"
            aria-label="Chiudi"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Contenuto Dinamico */}
        <div className="grow p-6 overflow-y-auto text-white">
          {renderContent()}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 text-center shrink-0">
           <button
            onClick={onClose}
            className="px-6 py-2 font-bold text-white bg-indigo-600 rounded-md shadow-lg hover:bg-indigo-700"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
};

export default QrResultModal;