import React, { useCallback, useEffect, useState } from 'react';
import { Wallet } from 'lucide-react';
import {
  staffAddResourcesToPersonaggio,
  staffGetPersonaggioEconomia,
  staffTrasferisciDepositoPersonaggio,
} from '../../api';

/**
 * Tab staff personaggio: saldi economia duale, add risorse, trasferimento forzato, log.
 */
export default function StaffEconomiaTab({ personaggioId, onLogout, onUpdated }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [importoTrasf, setImportoTrasf] = useState('');
  const [addAmount, setAddAmount] = useState('10');
  const [addConto, setAddConto] = useState('DEPOSITO');
  const [addReason, setAddReason] = useState('Intervento staff');
  const [logRows, setLogRows] = useState(null);

  const load = useCallback(async () => {
    if (!personaggioId) return;
    setBusy(true);
    setError('');
    try {
      const res = await staffGetPersonaggioEconomia(personaggioId, onLogout);
      setData(res);
    } catch (e) {
      setError(e.message || 'Errore caricamento economia');
      setData(null);
    } finally {
      setBusy(false);
    }
  }, [personaggioId, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const addCr = async () => {
    setBusy(true);
    setError('');
    try {
      await staffAddResourcesToPersonaggio(
        personaggioId,
        'crediti',
        Number(addAmount),
        addReason,
        onLogout,
        { conto: addConto },
      );
      await load();
      if (onUpdated) onUpdated();
    } catch (e) {
      setError(e.message || 'Errore add risorse');
    } finally {
      setBusy(false);
    }
  };

  const trasferisci = async () => {
    setBusy(true);
    setError('');
    try {
      await staffTrasferisciDepositoPersonaggio(
        personaggioId,
        { azione: 'trasferisci', importo: importoTrasf, motivo: 'Trasferimento staff' },
        onLogout,
      );
      setImportoTrasf('');
      await load();
      if (onUpdated) onUpdated();
    } catch (e) {
      setError(e.message || 'Errore trasferimento');
    } finally {
      setBusy(false);
    }
  };

  const loadLog = async () => {
    setLogRows(data?.movimenti_recenti || []);
  };

  if (!data && busy) {
    return <p className="text-sm text-gray-400 p-4">Caricamento economia…</p>;
  }

  return (
    <div className="space-y-4 p-2">
      <div className="flex items-center gap-2 text-emerald-300">
        <Wallet className="w-5 h-5" />
        <h3 className="font-semibold">Economia (corrente / deposito)</h3>
      </div>
      {error && <p className="text-red-400 text-sm">{error}</p>}

      <div className="grid grid-cols-3 gap-3">
        <div className="bg-gray-800 rounded p-3">
          <p className="text-xs text-gray-400">Corrente</p>
          <p className="text-xl font-bold text-emerald-300">{data?.crediti_corrente ?? '—'}</p>
        </div>
        <div className="bg-gray-800 rounded p-3">
          <p className="text-xs text-gray-400">Deposito</p>
          <p className="text-xl font-bold text-amber-300">{data?.crediti_deposito ?? '—'}</p>
        </div>
        <div className="bg-gray-800 rounded p-3">
          <p className="text-xs text-gray-400">PC</p>
          <p className="text-xl font-bold text-sky-300">{data?.punti_caratteristica ?? '—'}</p>
        </div>
      </div>

      <div className="border border-gray-700 rounded p-3 space-y-2">
        <p className="text-sm font-medium">Aggiungi / togli crediti</p>
        <div className="flex flex-wrap gap-2 items-end">
          <input
            type="number"
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 w-24"
            value={addAmount}
            onChange={(e) => setAddAmount(e.target.value)}
          />
          <select
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1"
            value={addConto}
            onChange={(e) => setAddConto(e.target.value)}
          >
            <option value="DEPOSITO">Deposito</option>
            <option value="CORRENTE">Corrente</option>
          </select>
          <input
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 flex-1 min-w-[8rem]"
            value={addReason}
            onChange={(e) => setAddReason(e.target.value)}
          />
          <button
            type="button"
            disabled={busy}
            onClick={addCr}
            className="px-3 py-1 rounded bg-emerald-700 text-sm"
          >
            Applica
          </button>
        </div>
      </div>

      <div className="border border-gray-700 rounded p-3 space-y-2">
        <p className="text-sm font-medium">Trasferimento forzato deposito → corrente</p>
        {data?.trasferimento && (
          <p className="text-xs text-gray-400">
            Tetto evento: {data.trasferimento.tetto} (già fatto: {String(data.trasferimento.gia_effettuato)})
          </p>
        )}
        <div className="flex gap-2 items-end">
          <input
            type="number"
            step="0.01"
            className="bg-gray-900 border border-gray-700 rounded px-2 py-1 w-28"
            value={importoTrasf}
            onChange={(e) => setImportoTrasf(e.target.value)}
            placeholder="Importo"
          />
          <button
            type="button"
            disabled={busy || !importoTrasf}
            onClick={trasferisci}
            className="px-3 py-1 rounded bg-amber-700 text-sm"
          >
            Trasferisci
          </button>
        </div>
      </div>

      <div>
        <button
          type="button"
          onClick={loadLog}
          className="text-sm px-3 py-1 rounded bg-gray-800 border border-gray-600"
        >
          Carica log crediti (se accessibile)
        </button>
        {logRows && (
          <ul className="mt-2 text-xs max-h-48 overflow-y-auto space-y-1">
            {logRows.length === 0 && <li className="text-gray-500">Nessun movimento / non accessibile</li>}
            {logRows.map((r, i) => (
              <li key={r.id || i} className="text-gray-300">
                {r.data ? new Date(r.data).toLocaleString() : ''} · {r.importo} · {r.conto} · {r.descrizione}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
