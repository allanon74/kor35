import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { getQrCodeData } from '../api'; // IMPORTA LA NUOVA FUNZIONE API
import { normalizeScannedQrId } from '../utils/qrScan';
import { useCharacter } from './CharacterContext'; // Importa per sapere chi sta scansionando
import { QrCode, Timer } from 'lucide-react'; // Icona Timer
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { UiErrorState, UiLoadingState } from './ui/AsyncState';
import { useOnlineStatus } from '../hooks/useOnlineStatus';
import {
  enqueueOfflineAction,
  listOfflineActions,
  removeOfflineAction,
  OFFLINE_ACTION_QR_SCAN,
} from '../lib/offlineActionQueue';

const QrTab = ({ onScanSuccess, onLogout, isStealingOnCooldown, cooldownTimer, onStealSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [info, setInfo] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  const [queuedCount, setQueuedCount] = useState(0);
  
  const html5QrCodeRef = useRef(null);
  const qrReaderId = "qr-reader-element";
  const isOnline = useOnlineStatus();
  
  // Prendi il personaggio attivo dal context
  const { selectedCharacterId, azioniLiveAbilitate, bypassEventoGate } = useCharacter();

  const refreshQueueCount = useCallback(async () => {
    try {
      const items = await listOfflineActions(OFFLINE_ACTION_QR_SCAN);
      setQueuedCount(items.length);
    } catch {
      setQueuedCount(0);
    }
  }, []);

  const flushQueuedScans = useCallback(async () => {
    if (!selectedCharacterId || !navigator.onLine) return;
    const items = await listOfflineActions(OFFLINE_ACTION_QR_SCAN);
    if (!items.length) {
      setQueuedCount(0);
      return;
    }
    setIsLoading(true);
    setInfo('');
    setError('');
    try {
      for (const item of items) {
        const qrId = item.payload?.qr_id;
        const pgId = item.payload?.personaggio_id || selectedCharacterId;
        if (!qrId) {
          await removeOfflineAction(item.id);
          continue;
        }
        try {
          const jsonData = await getQrCodeData(qrId, onLogout, pgId);
          await removeOfflineAction(item.id);
          onScanSuccess(jsonData);
          setInfo('Ripresa scansione dalla coda offline.');
          break; // una alla volta: l'utente chiude la modale prima della successiva
        } catch (err) {
          setError(err.message || 'Replay coda QR fallito.');
          break;
        }
      }
    } finally {
      setIsLoading(false);
      await refreshQueueCount();
    }
  }, [selectedCharacterId, onLogout, onScanSuccess, refreshQueueCount]);

  useEffect(() => {
    refreshQueueCount();
  }, [refreshQueueCount]);

  useEffect(() => {
    if (isOnline) flushQueuedScans();
  }, [isOnline, flushQueuedScans]);

  const handleScanData = async (decodedText) => {
    // Controlla se un personaggio è selezionato
    if (!selectedCharacterId) {
      setError("Per favore, seleziona un personaggio prima di scansionare.");
      stopWebcamScan(); // Ferma lo scanner
      return;
    }

    // Controllo cooldown globale
    if (isStealingOnCooldown) {
        setError(`Devi attendere la fine del cooldown (furto) prima di scansionare.`);
        stopWebcamScan();
        return;
    }

    setIsScanning(false);
    setIsLoading(true);
    setError('');
    setInfo('');

    try {
      await stopWebcamScan();

      const qrId = normalizeScannedQrId(decodedText);

      // Offline: metti in coda solo la lettura QR (no furto/scambio — quelle restano online-only).
      if (!navigator.onLine) {
        await enqueueOfflineAction({
          kind: OFFLINE_ACTION_QR_SCAN,
          payload: { qr_id: qrId, personaggio_id: selectedCharacterId },
        });
        await refreshQueueCount();
        setInfo(
          'Offline: scansione messa in coda. Verrà ripresa automaticamente quando torna la rete (solo consultazione QR; furto e scambi restano bloccati offline).'
        );
        return;
      }

      const jsonData = await getQrCodeData(qrId, onLogout, selectedCharacterId);
      
      onScanSuccess(jsonData); // Passa il JSON alla modale
      
    } catch (err) {
      // Rete assente o timeout: prova coda
      if (!navigator.onLine || /network|failed to fetch|offline/i.test(String(err?.message || ''))) {
        try {
          const qrId = normalizeScannedQrId(decodedText);
          await enqueueOfflineAction({
            kind: OFFLINE_ACTION_QR_SCAN,
            payload: { qr_id: qrId, personaggio_id: selectedCharacterId },
          });
          await refreshQueueCount();
          setInfo('Rete assente: scansione messa in coda per il ripristino.');
          return;
        } catch {
          /* fall through */
        }
      }
      setError(err.message || 'Impossibile caricare i dati QR.');
    } finally {
      setIsLoading(false);
    }
  };

  /*
    CORREZIONE 2: Problema "Quadrato Grigio"
    Dobbiamo assicurarci che il div #qr-reader-element sia VISIBILE
    nel DOM *prima* di provare ad avviare Html5Qrcode.
    Usiamo un setTimeout per ritardare l'avvio dello scanner
    di un attimo, dando a React il tempo di aggiornare il DOM.
  */
  const startWebcamScan = () => {
    setError('');
    setIsScanning(true); // 1. Dice a React di mostrare il div

    // 2. Aspetta un attimo che il DOM si aggiorni
    setTimeout(() => {
      // Controlla se l'istanza esiste già e se è in scansione
      if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
        console.log("Scanner già attivo.");
        return;
      }

      try {
        // 3. Ora il div #qr-reader-element è visibile
        if (!html5QrCodeRef.current) {
          html5QrCodeRef.current = new Html5Qrcode(qrReaderId);
        }
        
        const config = { fps: 10, qrbox: { width: 250, height: 250 } };
        
        html5QrCodeRef.current.start(
          { facingMode: "environment" }, // Prova prima la fotocamera posteriore
          config,
          (decodedText, decodedResult) => {
            // Successo
            handleScanData(decodedText);
          },
          (errorMessage) => {
            // Errore durante la scansione (es. non trova QR), non fatale
            // console.warn(`Errore scansione QR: ${errorMessage}`);
          }
        ).catch((err) => {
          // Errore grave (es. permessi negati)
          console.error("Errore avvio webcam:", err);
          setError("Impossibile avviare la webcam. Assicurati di aver dato i permessi.");
          setIsScanning(false);
        });

      } catch (e) {
        console.error("Eccezione Html5Qrcode:", e);
        setError("Errore inizializzazione scanner.");
        setIsScanning(false);
      }
    }, 100); // 100ms di ritardo dovrebbero bastare
  };


  const stopWebcamScan = async () => {
    if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
      try {
        await html5QrCodeRef.current.stop();
        console.log("Scanner fermato.");
      } catch (err) {
        console.error("Errore nel fermare lo scanner:", err);
      }
    }
    setIsScanning(false);
  };

  const handleFileScan = async (event) => {
    const file = event.target.files[0];
    if (!file) {
      return;
    }

    setIsLoading(true);
    setError('');

    try {
      // Crea un'istanza "usa e getta" per la scansione file
      const fileScanner = new Html5Qrcode(qrReaderId, /* verbose= */ false);
      const decodedText = await fileScanner.scanFile(file, /* showImage= */ false);
      handleScanData(decodedText);
    } catch (err) {
      console.error("Errore scansione file:", err);
      setError("Impossibile leggere il QR code dal file. Prova un'altra immagine.");
    } finally {
      setIsLoading(false);
      // Pulisce il valore dell'input file per permettere di ricaricare lo stesso file
      event.target.value = null; 
    }
  };

  // Cleanup effect per fermare lo scanner quando il componente viene smontato
  useEffect(() => {
    // Ritorna una funzione di cleanup
    return () => {
      stopWebcamScan();
    };
  }, []); // Esegui solo al mount e unmount

  return (
    <PlayerTabShell width="narrow" animate className="flex flex-col items-center">
      <PlayerTabHeader icon={<QrCode size={22} />} title="Scansione QR Code" />

      {!azioniLiveAbilitate && !bypassEventoGate && (
        <div className="w-full max-w-md p-3 mb-4 text-sm text-amber-200/90 bg-amber-950/40 border border-amber-800/50 rounded-lg">
          Scansione nodi, furti e scambi da QR personaggio sono attivi solo durante un evento aperto.
        </div>
      )}

      {!isOnline && (
        <div className="w-full max-w-md p-3 mb-4 text-sm text-amber-100 bg-amber-950/50 border border-amber-700/50 rounded-lg">
          Offline: puoi mettere in coda una scansione QR. Furto, scambi e mutazioni restano disabilitati
          finché non c&apos;è conferma dal server.
          {queuedCount > 0 ? ` In coda: ${queuedCount}.` : ''}
        </div>
      )}

      {isOnline && queuedCount > 0 && (
        <div className="w-full max-w-md p-3 mb-4 text-sm text-emerald-100 bg-emerald-950/40 border border-emerald-800/40 rounded-lg flex items-center justify-between gap-2">
          <span>{queuedCount} scansione/i in coda offline.</span>
          <button
            type="button"
            onClick={flushQueuedScans}
            className="shrink-0 px-2 py-1 rounded bg-emerald-700 hover:bg-emerald-600 text-xs font-bold"
          >
            Riprendi
          </button>
        </div>
      )}

      {info && (
        <div className="w-full max-w-md p-3 mb-4 text-sm text-sky-100 bg-sky-950/40 border border-sky-800/40 rounded-lg">
          {info}
        </div>
      )}

      {/* --- NUOVO BLOCCO COOLDOWN --- */}
      {isStealingOnCooldown && (
        <div className="w-full max-w-md p-4 mb-6 text-center bg-red-900 bg-opacity-70 rounded-lg shadow-lg">
          <div className="flex items-center justify-center">
             <Timer className="text-red-300 mr-2" />
             <h3 className="text-lg font-bold text-red-200">Cooldown Furto Attivo</h3>
          </div>
          <p className="text-2xl font-bold text-white mt-2">{cooldownTimer}s</p>
          <p className="text-red-300">Non puoi scansionare personaggi in questo stato.</p>
        </div>
      )}
    
      {isLoading && <UiLoadingState label="Caricamento dati…" className="py-6" />}

      {error && <UiErrorState message={error} className="w-full max-w-md mb-4" />}

      <div className="w-full max-w-md mt-4 space-y-4">
        {!isScanning && !isLoading && (
          <>
            <button
              onClick={startWebcamScan}
              className="w-full px-4 py-3 bg-indigo-600 text-white text-lg font-bold rounded-md shadow-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              Avvia Scansione Webcam
            </button>
            
           <label className={`block w-full px-4 py-3 bg-gray-700 text-white text-lg text-center font-bold rounded-md shadow-lg hover:bg-gray-600 cursor-pointer
              ${isStealingOnCooldown ? 'opacity-50 cursor-not-allowed' : ''}`}>
              <span>Carica Immagine QR</span>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileScan}
                className="hidden"
                disabled={isLoading || isStealingOnCooldown} // Disabilitato durante il caricamento o cooldown} 
              />
            </label>
          </>
        )}
      </div>

      {/* Questo è il riquadro dove apparirà lo scanner */}
      {isScanning && (
        <div className="mt-4 flex flex-col items-center w-full">
          {/* L'altezza h-80 è corretta */}
          <div 
            id={qrReaderId} 
            className="w-full max-w-sm h-80 rounded-lg overflow-hidden shadow-lg bg-gray-700"
          >
            {/* Il video della webcam verrà iniettato qui dalla libreria */}
          </div>
          
          <button
            onClick={stopWebcamScan}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md shadow-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            Ferma Scansione
          </button>
        </div>
      )}

      {/* Questo div è necessario per la scansione da file, 
        ma non deve essere visibile. Lo nascondiamo.
      */}
      {!isScanning && <div id={qrReaderId} className="hidden"></div>}

    </PlayerTabShell>
  );
};

export default QrTab;

