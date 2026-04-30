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

  const rgbToHex = (r, g, b) => {
    const clamp = (v) => Math.max(0, Math.min(255, Math.round(v)));
    return `#${[clamp(r), clamp(g), clamp(b)].map((x) => x.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
  };

  const estimateColorsFromImageData = (imageData) => {
    if (!imageData?.data || imageData.data.length < 4) return null;
    const pixels = [];
    const data = imageData.data;
    let sumR = 0;
    let sumG = 0;
    let sumB = 0;
    let count = 0;

    for (let i = 0; i < data.length; i += 4) {
      const a = data[i + 3];
      if (a < 16) continue;
      sumR += data[i];
      sumG += data[i + 1];
      sumB += data[i + 2];
      count += 1;
    }

    if (count < 60) return null;

    // Gray-world white balance per compensare dominanti colore da illuminazione.
    const meanR = sumR / count;
    const meanG = sumG / count;
    const meanB = sumB / count;
    const meanGray = (meanR + meanG + meanB) / 3 || 1;
    const gainR = meanGray / (meanR || 1);
    const gainG = meanGray / (meanG || 1);
    const gainB = meanGray / (meanB || 1);
    const clamp = (v) => Math.max(0, Math.min(255, v));

    for (let i = 0; i < data.length; i += 4) {
      const a = data[i + 3];
      if (a < 16) continue;
      const r = clamp(data[i] * gainR);
      const g = clamp(data[i + 1] * gainG);
      const b = clamp(data[i + 2] * gainB);
      const l = 0.2126 * r + 0.7152 * g + 0.0722 * b;
      pixels.push({ r, g, b, l });
    }

    if (pixels.length < 60) return null;

    pixels.sort((a, b) => a.l - b.l);
    const bucketSize = Math.max(20, Math.floor(pixels.length * 0.18));
    const dark = pixels.slice(0, bucketSize);
    const light = pixels.slice(-bucketSize);
    const midStart = Math.floor(pixels.length * 0.4);
    const midEnd = Math.floor(pixels.length * 0.6);
    const mid = pixels.slice(midStart, Math.max(midStart + 1, midEnd));

    const avg = (arr, key) => arr.reduce((acc, p) => acc + p[key], 0) / arr.length;
    const darkRgb = { r: avg(dark, 'r'), g: avg(dark, 'g'), b: avg(dark, 'b'), l: avg(dark, 'l') };
    const lightRgb = { r: avg(light, 'r'), g: avg(light, 'g'), b: avg(light, 'b'), l: avg(light, 'l') };
    const midL = avg(mid, 'l');

    const luminanceGap = lightRgb.l - darkRgb.l;
    const midContrast = Math.abs(midL - (darkRgb.l + lightRgb.l) / 2);
    const confidence = Math.max(
      0,
      Math.min(1, luminanceGap / 220 - midContrast / 160)
    );

    // In casi ambigui (controluce/blur), non forziamo colore "reale".
    if (confidence < 0.2 || luminanceGap < 35) {
      return {
        codice: '#FFFFFF',
        sfondo: '#000000',
        confidence: 0,
      };
    }

    return {
      codice: rgbToHex(darkRgb.r, darkRgb.g, darkRgb.b),
      sfondo: rgbToHex(lightRgb.r, lightRgb.g, lightRgb.b),
      confidence,
    };
  };

  const estimateColorsFromVideo = () => {
    try {
      const root = document.getElementById(qrReaderId);
      const video = root?.querySelector?.('video');
      if (!video || !video.videoWidth || !video.videoHeight) return null;

      const canvas = document.createElement('canvas');
      const width = Math.min(320, video.videoWidth);
      const height = Math.min(320, video.videoHeight);
      canvas.width = width;
      canvas.height = height;
      const ctx = canvas.getContext('2d', { willReadFrequently: true });
      if (!ctx) return null;

      ctx.drawImage(video, 0, 0, width, height);
      const sampleW = Math.floor(width * 0.6);
      const sampleH = Math.floor(height * 0.6);
      const sx = Math.floor((width - sampleW) / 2);
      const sy = Math.floor((height - sampleH) / 2);
      const imageDataCenter = ctx.getImageData(sx, sy, sampleW, sampleH);
      const centerColors = estimateColorsFromImageData(imageDataCenter);

      // Fallback su area più ampia se il centro è poco affidabile.
      if (!centerColors || centerColors.confidence < 0.25) {
        const broadW = Math.floor(width * 0.85);
        const broadH = Math.floor(height * 0.85);
        const bx = Math.floor((width - broadW) / 2);
        const by = Math.floor((height - broadH) / 2);
        const imageDataBroad = ctx.getImageData(bx, by, broadW, broadH);
        const broadColors = estimateColorsFromImageData(imageDataBroad);
        if (!centerColors) return broadColors;
        if (!broadColors) return centerColors;
        return broadColors.confidence > centerColors.confidence ? broadColors : centerColors;
      }
      return centerColors;
    } catch (err) {
      console.warn('Stima colori QR da video fallita:', err);
      return null;
    }
  };

  const handleScanData = async (decodedText, scanMeta = null) => {
    setIsScanning(false);
    setIsLoading(true);
    setError('');

    try {
      await stopWebcamScan();
      
      // Per uso staff, passiamo ID e metadata opzionali (es. colori stimati)
      onScanSuccess(decodedText, scanMeta);
      
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
            const colors = estimateColorsFromVideo();
            handleScanData(decodedText, { colors, decodedResult });
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
      handleScanData(decodedText, { colors: null });
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
