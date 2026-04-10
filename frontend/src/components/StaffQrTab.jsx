import React, { useState, useRef, useEffect } from 'react';
import { Html5Qrcode } from 'html5-qrcode';

/**
 * Componente semplificato per scansione QR lato staff.
 * A differenza di QrTab normale, questo restituisce solo l'ID del QR scansionato,
 * senza chiamare getQrCodeData() che richiederebbe un personaggio selezionato.
 */
const StaffQrTab = ({ onScanSuccess, onLogout }) => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [isScanning, setIsScanning] = useState(false);
  
  const html5QrCodeRef = useRef(null);
  const qrReaderId = "staff-qr-reader-element";

  const handleScanData = async (decodedText) => {
    setIsScanning(false);
    setIsLoading(true);
    setError('');

    try {
      await stopWebcamScan();
      
      // Per uso staff, passiamo direttamente l'ID scansionato
      onScanSuccess(decodedText);
      
    } catch (err) {
      setError(err.message || 'Impossibile elaborare il QR.');
    } finally {
      setIsLoading(false);
    }
  };

  const startWebcamScan = () => {
    setError('');
    setIsScanning(true);

    setTimeout(() => {
      if (html5QrCodeRef.current && html5QrCodeRef.current.isScanning) {
        console.log("Scanner già attivo.");
        return;
      }

      try {
        if (!html5QrCodeRef.current) {
          html5QrCodeRef.current = new Html5Qrcode(qrReaderId);
        }
        
        const config = { fps: 10, qrbox: { width: 250, height: 250 } };
        
        html5QrCodeRef.current.start(
          { facingMode: "environment" },
          config,
          (decodedText, decodedResult) => {
            handleScanData(decodedText);
          },
          (errorMessage) => {
            // Errore durante la scansione (es. non trova QR), non fatale
          }
        ).catch((err) => {
          console.error("Errore avvio webcam:", err);
          setError("Impossibile avviare la webcam. Assicurati di aver dato i permessi.");
          setIsScanning(false);
        });

      } catch (e) {
        console.error("Eccezione Html5Qrcode:", e);
        setError("Errore inizializzazione scanner.");
        setIsScanning(false);
      }
    }, 100);
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
      const fileScanner = new Html5Qrcode(qrReaderId, /* verbose= */ false);
      const decodedText = await fileScanner.scanFile(file, /* showImage= */ false);
      handleScanData(decodedText);
    } catch (err) {
      console.error("Errore scansione file:", err);
      setError("Impossibile leggere il QR code dal file. Prova un'altra immagine.");
    } finally {
      setIsLoading(false);
      event.target.value = null;
    }
  };

  useEffect(() => {
    return () => {
      stopWebcamScan();
    };
  }, []);

  return (
    <div className="flex flex-col items-center p-4">
      <h2 className="text-2xl font-bold mb-6 text-indigo-400">Scansione QR Code (Staff)</h2>

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
            
            <label className="block w-full px-4 py-3 bg-gray-700 text-white text-lg text-center font-bold rounded-md shadow-lg hover:bg-gray-600 cursor-pointer">
              <span>Carica Immagine QR</span>
              <input
                type="file"
                accept="image/*"
                onChange={handleFileScan}
                className="hidden"
                disabled={isLoading}
              />
            </label>
          </>
        )}
      </div>

      {isScanning && (
        <div className="mt-4 flex flex-col items-center w-full">
          <div 
            id={qrReaderId} 
            className="w-full max-w-sm h-80 rounded-lg overflow-hidden shadow-lg bg-gray-700"
          >
          </div>
          
          <button
            onClick={stopWebcamScan}
            className="mt-4 px-4 py-2 bg-red-600 text-white rounded-md shadow-md hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            Ferma Scansione
          </button>
        </div>
      )}

      {!isScanning && <div id={qrReaderId} className="hidden"></div>}
    </div>
  );
};

export default StaffQrTab;
