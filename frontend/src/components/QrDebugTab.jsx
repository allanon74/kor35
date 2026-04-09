import React, { useState } from 'react';
import { Search, QrCode, ExternalLink } from 'lucide-react';
import StaffQrTab from './StaffQrTab';
import { getQrCodeData } from '../api';

/**
 * Tab di debug per ispezionare le associazioni QR.
 * Permette di scansionare o inserire un ID QR per vedere a cosa è associato.
 */
const QrDebugTab = ({ onLogout }) => {
  const [mode, setMode] = useState('manual'); // 'manual' | 'scan'
  const [qrId, setQrId] = useState('');
  const [qrData, setQrData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleLookup = async (id) => {
    if (!id || !id.trim()) {
      setError('Inserisci un ID QR valido');
      return;
    }

    setLoading(true);
    setError('');
    setQrData(null);

    try {
      const data = await getQrCodeData(id.trim(), onLogout);
      setQrData(data);
    } catch (err) {
      setError(err.message || 'Impossibile recuperare i dati del QR');
      console.error('Errore lookup QR:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleManualSubmit = (e) => {
    e.preventDefault();
    handleLookup(qrId);
  };

  const handleScan = async (scannedId) => {
    setQrId(scannedId);
    await handleLookup(scannedId);
    setMode('manual'); // Torna alla modalità manuale dopo la scansione
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-indigo-400 mb-2 uppercase tracking-wide">QR Debug Tool</h2>
        <p className="text-gray-400 text-sm">Ispeziona le associazioni QR per verificare configurazioni e debug</p>
      </div>

      {/* Mode Selector */}
      <div className="flex gap-2 mb-6">
        <button
          onClick={() => setMode('manual')}
          className={`flex-1 py-3 px-4 rounded-lg font-bold transition-all ${
            mode === 'manual'
              ? 'bg-indigo-600 text-white shadow-lg'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <Search className="inline-block mr-2" size={18} />
          Inserimento Manuale
        </button>
        <button
          onClick={() => setMode('scan')}
          className={`flex-1 py-3 px-4 rounded-lg font-bold transition-all ${
            mode === 'scan'
              ? 'bg-indigo-600 text-white shadow-lg'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <QrCode className="inline-block mr-2" size={18} />
          Scansiona QR
        </button>
      </div>

      {/* Manual Mode */}
      {mode === 'manual' && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <form onSubmit={handleManualSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-bold text-gray-300 mb-2">
                ID QR Code
              </label>
              <input
                type="text"
                value={qrId}
                onChange={(e) => setQrId(e.target.value)}
                placeholder="es. 123 o ABC123"
                className="w-full px-4 py-3 bg-gray-900 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:border-indigo-500 focus:outline-none"
              />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Caricamento...' : 'Cerca QR'}
            </button>
          </form>
        </div>
      )}

      {/* Scan Mode */}
      {mode === 'scan' && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6">
          <StaffQrTab onScanSuccess={handleScan} onLogout={onLogout} />
        </div>
      )}

      {/* Error Display */}
      {error && (
        <div className="bg-red-900/50 border border-red-700 rounded-lg p-4 mb-6">
          <p className="text-red-300 font-semibold">{error}</p>
        </div>
      )}

      {/* Results Display */}
      {qrData && (
        <div className="bg-gray-800 rounded-lg p-6 space-y-6">
          <div className="border-b border-gray-700 pb-4">
            <h3 className="text-xl font-bold text-white mb-2">
              QR Code: {qrData.id}
            </h3>
            <p className="text-gray-400 text-sm">
              Tipo: <span className="text-indigo-400 font-semibold">{qrData.tipo}</span>
            </p>
          </div>

          {/* Display different sections based on tipo */}
          {qrData.tipo === 'personaggio' && qrData.personaggio && (
            <div className="space-y-3">
              <h4 className="text-lg font-bold text-indigo-400">Personaggio</h4>
              <div className="bg-gray-900 rounded-lg p-4">
                <p className="text-white font-semibold text-lg">{qrData.personaggio.nome}</p>
                <p className="text-gray-400 text-sm">ID: {qrData.personaggio.id}</p>
              </div>
            </div>
          )}

          {qrData.tipo === 'manifesto' && qrData.manifesto && (
            <div className="space-y-3">
              <h4 className="text-lg font-bold text-indigo-400">Vista Manifesto</h4>
              <div className="bg-gray-900 rounded-lg p-4">
                <p className="text-white font-semibold">{qrData.manifesto.nome}</p>
                <p className="text-gray-400 text-sm">Quest: {qrData.manifesto.quest_nome}</p>
              </div>
            </div>
          )}

          {qrData.tipo === 'a_vista' && qrData.dettagli_elemento && (
            <div className="space-y-3">
              <h4 className="text-lg font-bold text-indigo-400">Elemento A_Vista</h4>
              <div className="bg-gray-900 rounded-lg p-4 space-y-2">
                <p className="text-white font-semibold text-lg">{qrData.dettagli_elemento.nome}</p>
                <p className="text-gray-400 text-sm">
                  Tipo: <span className="text-indigo-300">{qrData.dettagli_elemento.tipo_elemento}</span>
                </p>
                {qrData.dettagli_elemento.descrizione && (
                  <p className="text-gray-400 text-sm mt-2">{qrData.dettagli_elemento.descrizione}</p>
                )}
              </div>
            </div>
          )}

          {/* Raw JSON Data (Collapsible) */}
          <details className="bg-gray-900 rounded-lg overflow-hidden">
            <summary className="px-4 py-3 cursor-pointer text-gray-400 hover:text-white font-semibold text-sm uppercase tracking-wide">
              <ExternalLink className="inline-block mr-2" size={14} />
              Mostra Dati Grezzi (JSON)
            </summary>
            <div className="px-4 pb-4">
              <pre className="text-xs text-yellow-300 overflow-x-auto p-4 bg-gray-950 rounded">
                {JSON.stringify(qrData, null, 2)}
              </pre>
            </div>
          </details>
        </div>
      )}

      {/* Empty State */}
      {!qrData && !loading && !error && (
        <div className="text-center py-12 text-gray-500">
          <QrCode size={64} className="mx-auto mb-4 opacity-30" />
          <p className="font-semibold">Inserisci o scansiona un QR per iniziare</p>
        </div>
      )}
    </div>
  );
};

export default QrDebugTab;
