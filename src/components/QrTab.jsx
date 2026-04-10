import React, { useState, useRef, useEffect } from 'react';
import { Html5Qrcode } from 'html5-qrcode';
import { getQrCodeData } from '../api'; // IMPORTA LA NUOVA FUNZIONE API
import { useCharacter } from './CharacterContext'; // Importa per sapere chi sta scansionando
import { Timer } from 'lucide-react'; // Icona Timer

const QrTab = ({ onScanSuccess, onLogout, isStealingOnCooldown, cooldownTimer, onStealSuccess }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  
  const html5QrCodeRef = useRef(null);
  const qrReaderId = "qr-reader-element";
  
  // Prendi il personaggio attivo dal context
  const { selectedCharacterId } = useCharacter();

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

    try {
      await stopWebcamScan();

      // USA LA NUOVA FUNZIONE API
      const jsonData = await getQrCodeData(decodedText, onLogout);
      
      onScanSuccess(jsonData); // Passa il JSON alla modale
      
    } catch (err) {
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
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-6 text-indigo-400">Scansione QR Code</h2>

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
    
      {isLoading && (
        <div className="text-center text-lg text-gray-300">
          <p>Caricamento dati...</p>
        </div>
      )}

      {error && (
        <div className="text-center text-red-400 bg-red-900 bg-opacity-50 p-3 rounded-md">
          <p>{error}</p>
        </div>
      )}

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

    </div>
  );
};

export default QrTab;

