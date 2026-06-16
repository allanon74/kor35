import React, { useState } from 'react';
import { Search, QrCode, ExternalLink } from 'lucide-react';
import StaffQrTab from './StaffQrTab';
import MinigiocoQrEditor from './editors/MinigiocoQrEditor';
import MinigiocoBibliotecaPanel from './editors/MinigiocoBibliotecaPanel';
import { staffInspectQrCode, staffQrInventarioScan } from '../api';

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
  const [inventoryMode, setInventoryMode] = useState('totale'); // 'totale' | 'additiva'
  const [inventoryActive, setInventoryActive] = useState(false);
  const [inventoryNeedsReset, setInventoryNeedsReset] = useState(false);
  const [inventoryEvents, setInventoryEvents] = useState([]);
  const [pendingInventoryScan, setPendingInventoryScan] = useState(null);

  const handleLookup = async (id) => {
    if (!id || !id.trim()) {
      setError('Inserisci un ID QR valido');
      return;
    }

    setLoading(true);
    setError('');
    setQrData(null);

    try {
      const data = await staffInspectQrCode(id.trim(), onLogout);
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

  const startInventorySession = () => {
    setError('');
    setQrData(null);
    setInventoryEvents([]);
    setPendingInventoryScan(null);
    setInventoryNeedsReset(inventoryMode === 'totale');
    setInventoryActive(true);
  };

  const stopInventorySession = () => {
    setInventoryActive(false);
    setInventoryNeedsReset(false);
    setPendingInventoryScan(null);
  };

  const handleInventoryScan = async (scannedId, scanMeta = null) => {
    const coloriStimati = scanMeta?.colors || null;
    const conf = Number(coloriStimati?.confidence || 0);
    const codiceDefault = coloriStimati?.codice || '#FFFFFF';
    const sfondoDefault = coloriStimati?.sfondo || '#000000';
    setPendingInventoryScan({
      qrId: scannedId,
      codice: codiceDefault,
      sfondo: sfondoDefault,
      confidence: conf,
    });
  };

  const submitPendingInventoryScan = async () => {
    if (!pendingInventoryScan?.qrId) return;
    setLoading(true);
    setError('');
    try {
      const data = await staffQrInventarioScan(
        {
          qr_id: pendingInventoryScan.qrId,
          modalita: inventoryMode,
          reset_before_scan: inventoryMode === 'totale' && inventoryNeedsReset,
          inventario_colore_codice: pendingInventoryScan.codice || null,
          inventario_colore_sfondo: pendingInventoryScan.sfondo || null,
        },
        onLogout
      );
      setInventoryNeedsReset(false);
      setInventoryEvents((prev) => [
        {
          ts: new Date().toISOString(),
          qrId: data.qr_id,
          ok: true,
          reset: Boolean(data.reset_applicato),
          presenti: data.totale_presenti,
          codice: data.inventario_colore_codice,
          sfondo: data.inventario_colore_sfondo,
          confidence: pendingInventoryScan.confidence,
        },
        ...prev.slice(0, 24),
      ]);
      setPendingInventoryScan(null);
    } catch (err) {
      const unknown = Boolean(err?.data?.qr_sconosciuto) || err?.status === 404;
      setError(unknown ? `QR sconosciuto: ${pendingInventoryScan.qrId}` : (err.message || 'Errore durante inventario QR'));
      setInventoryEvents((prev) => [
        {
          ts: new Date().toISOString(),
          qrId: pendingInventoryScan.qrId,
          ok: false,
          unknown,
        },
        ...prev.slice(0, 24),
      ]);
      setPendingInventoryScan(null);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <div className="mb-6">
        <h2 className="text-2xl font-black text-indigo-400 mb-2 uppercase tracking-wide">QR Debug Tool</h2>
        <p className="text-gray-400 text-sm">Ispeziona le associazioni QR per verificare configurazioni e debug</p>
      </div>

      <MinigiocoBibliotecaPanel onLogout={onLogout} />

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
        <button
          onClick={() => setMode('inventory')}
          className={`flex-1 py-3 px-4 rounded-lg font-bold transition-all ${
            mode === 'inventory'
              ? 'bg-indigo-600 text-white shadow-lg'
              : 'bg-gray-800 text-gray-400 hover:bg-gray-700'
          }`}
        >
          <QrCode className="inline-block mr-2" size={18} />
          Inventario QR
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

      {mode === 'inventory' && (
        <div className="bg-gray-800 rounded-lg p-6 mb-6 space-y-4">
          <div className="space-y-2">
            <p className="text-sm text-gray-300 font-semibold">Modalita inventario</p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              <button
                onClick={() => setInventoryMode('totale')}
                disabled={inventoryActive}
                className={`py-2 px-3 rounded-md font-bold transition-colors ${
                  inventoryMode === 'totale' ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300'
                } ${inventoryActive ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-600'}`}
              >
                Totale (azzera + marca scansionati)
              </button>
              <button
                onClick={() => setInventoryMode('additiva')}
                disabled={inventoryActive}
                className={`py-2 px-3 rounded-md font-bold transition-colors ${
                  inventoryMode === 'additiva' ? 'bg-indigo-600 text-white' : 'bg-gray-700 text-gray-300'
                } ${inventoryActive ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-600'}`}
              >
                Additiva (aggiorna solo scansionati)
              </button>
            </div>
          </div>

          {!inventoryActive ? (
            <button
              onClick={startInventorySession}
              className="w-full py-3 bg-emerald-600 hover:bg-emerald-700 text-white font-bold rounded-lg transition-colors"
            >
              Inizia Inventario QR
            </button>
          ) : (
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <p className="text-xs text-gray-300">
                  Sessione attiva in modalita <span className="font-bold text-indigo-300">{inventoryMode}</span>
                </p>
                <button
                  onClick={stopInventorySession}
                  className="px-3 py-1.5 bg-red-600 hover:bg-red-700 rounded text-sm font-semibold"
                >
                  Termina
                </button>
              </div>
              <StaffQrTab onScanSuccess={handleInventoryScan} onLogout={onLogout} />
            </div>
          )}

          {pendingInventoryScan && (
            <div className="bg-gray-950 border border-indigo-700/50 rounded-lg p-4 space-y-3">
              <p className="text-sm font-bold text-indigo-300">
                QR letto: {pendingInventoryScan.qrId}
              </p>
              <p className="text-xs text-gray-400">
                Confidenza stima colore:{' '}
                <span className={`font-bold ${
                  pendingInventoryScan.confidence >= 0.55
                    ? 'text-emerald-300'
                    : pendingInventoryScan.confidence >= 0.3
                      ? 'text-amber-300'
                      : 'text-red-300'
                }`}>
                  {pendingInventoryScan.confidence >= 0.55
                    ? 'Alta'
                    : pendingInventoryScan.confidence >= 0.3
                      ? 'Media'
                      : 'Bassa'}
                </span>
                {' '}({Math.round((pendingInventoryScan.confidence || 0) * 100)}%)
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <label className="text-xs text-gray-300 space-y-1">
                  <span className="block">Colore codice</span>
                  <input
                    type="color"
                    value={pendingInventoryScan.codice}
                    onChange={(e) =>
                      setPendingInventoryScan((prev) => ({ ...prev, codice: e.target.value.toUpperCase() }))
                    }
                    className="w-full h-10 bg-gray-800 border border-gray-700 rounded"
                  />
                </label>
                <label className="text-xs text-gray-300 space-y-1">
                  <span className="block">Colore sfondo</span>
                  <input
                    type="color"
                    value={pendingInventoryScan.sfondo}
                    onChange={(e) =>
                      setPendingInventoryScan((prev) => ({ ...prev, sfondo: e.target.value.toUpperCase() }))
                    }
                    className="w-full h-10 bg-gray-800 border border-gray-700 rounded"
                  />
                </label>
              </div>

              <div className="flex flex-wrap gap-2">
                <button
                  onClick={() =>
                    setPendingInventoryScan((prev) => ({
                      ...prev,
                      codice: '#FFFFFF',
                      sfondo: '#000000',
                    }))
                  }
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-xs font-bold text-gray-200"
                >
                  Forza B/N
                </button>
                <button
                  onClick={() =>
                    setPendingInventoryScan((prev) => ({
                      ...prev,
                      codice: prev?.sfondo || '#000000',
                      sfondo: prev?.codice || '#FFFFFF',
                    }))
                  }
                  className="px-3 py-1.5 bg-gray-800 hover:bg-gray-700 rounded text-xs font-bold text-gray-200"
                >
                  Inverti colori
                </button>
              </div>

              <div className="flex gap-2">
                <button
                  onClick={submitPendingInventoryScan}
                  disabled={loading}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 rounded font-bold text-sm disabled:opacity-60"
                >
                  Conferma inventario
                </button>
                <button
                  onClick={() => setPendingInventoryScan(null)}
                  disabled={loading}
                  className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded font-bold text-sm disabled:opacity-60"
                >
                  Scarta scansione
                </button>
              </div>
            </div>
          )}

          {inventoryEvents.length > 0 && (
            <div className="bg-gray-900 rounded-lg p-3">
              <p className="text-xs font-bold text-gray-400 uppercase tracking-wide mb-2">Ultime scansioni</p>
              <div className="space-y-1 text-sm">
                {inventoryEvents.map((evt, idx) => (
                  <div key={`${evt.ts}-${evt.qrId}-${idx}`} className={evt.ok ? 'text-emerald-300' : 'text-red-300'}>
                    {evt.ok
                      ? `${evt.qrId} acquisito${evt.reset ? ' (reset totale eseguito)' : ''} - presenti: ${evt.presenti} - codice ${evt.codice} / sfondo ${evt.sfondo} - conf: ${Math.round((evt.confidence || 0) * 100)}%`
                      : `${evt.qrId} - ${evt.unknown ? 'QR sconosciuto' : 'errore scansione'}`}
                  </div>
                ))}
              </div>
            </div>
          )}
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
              Tipo risolto:{' '}
              <span className="text-indigo-400 font-semibold">{qrData.tipo_contenuto || 'Vuoto'}</span>
              {qrData.elemento_id != null && qrData.elemento_id !== '' && (
                <span className="text-gray-500"> · id elemento: {qrData.elemento_id}</span>
              )}
            </p>
            {qrData.nota && (
              <p className="text-amber-400/90 text-sm mt-2">{qrData.nota}</p>
            )}
          </div>

          <div className="space-y-3">
            <h4 className="text-lg font-bold text-indigo-400">Associazione</h4>
            <div className="bg-gray-900 rounded-lg p-4 space-y-2">
              <p className="text-white font-semibold text-lg">{qrData.nome_contenuto || 'Nessuno'}</p>
              <p className="text-gray-400 text-sm">
                Testo raw: <span className="text-indigo-300">{qrData.testo_raw || '—'}</span>
              </p>
              {qrData.dati != null && (
                <p className="text-gray-500 text-xs pt-2 border-t border-gray-800">
                  Dati dell&apos;elemento collegato (staff) sono nel JSON sotto in <code className="text-gray-400">dati</code>.
                </p>
              )}
            </div>
          </div>

          <MinigiocoQrEditor qrId={qrData.id} onLogout={onLogout} />

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
