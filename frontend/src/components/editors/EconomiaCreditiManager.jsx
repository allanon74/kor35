import React, { useCallback, useEffect, useState } from 'react';
import { Wallet } from 'lucide-react';
import {
  fetchEconomiaConfig,
  patchEconomiaConfig,
  staffGetCampagne,
} from '../api';

const CATEGORIE = [
  { id: 'oggetto', label: 'Oggetti' },
  { id: 'materia', label: 'Materia' },
  { id: 'consumabile', label: 'Consumabili' },
  { id: 'negozio', label: 'Negozi / Accademia' },
];

/**
 * Staff tool: config economia duale per campagna.
 */
export default function EconomiaCreditiManager({ onLogout }) {
  const [campagne, setCampagne] = useState([]);
  const [campagnaId, setCampagnaId] = useState('');
  const [config, setConfig] = useState(null);
  const [frazione, setFrazione] = useState('1.00');
  const [fattore, setFattore] = useState('0.90');
  const [categorie, setCategorie] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [okMsg, setOkMsg] = useState('');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const list = await staffGetCampagne(onLogout);
        const rows = Array.isArray(list) ? list : list?.results || [];
        if (cancelled) return;
        setCampagne(rows);
        if (rows.length && !campagnaId) {
          const def = rows.find((c) => c.is_default) || rows[0];
          setCampagnaId(String(def.id));
        }
      } catch (e) {
        if (!cancelled) setError(e.message || 'Errore caricamento campagne');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onLogout]);

  const loadConfig = useCallback(async () => {
    if (!campagnaId) return;
    setBusy(true);
    setError('');
    try {
      const res = await fetchEconomiaConfig(campagnaId, onLogout);
      const cfg = res?.config || {};
      setConfig(cfg);
      setFrazione(String(cfg.frazione_trasferimento_stipendio ?? '1.00'));
      setFattore(String(cfg.fattore_valore_deposito ?? '0.90'));
      setCategorie(Array.isArray(cfg.categorie_spesa_deposito) ? [...cfg.categorie_spesa_deposito] : []);
    } catch (e) {
      setError(e.message || 'Errore caricamento config');
    } finally {
      setBusy(false);
    }
  }, [campagnaId, onLogout]);

  useEffect(() => {
    loadConfig();
  }, [loadConfig]);

  const toggleCat = (id) => {
    setCategorie((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const save = async () => {
    setBusy(true);
    setError('');
    setOkMsg('');
    try {
      const res = await patchEconomiaConfig(
        campagnaId,
        {
          frazione_trasferimento_stipendio: frazione,
          fattore_valore_deposito: fattore,
          categorie_spesa_deposito: categorie,
        },
        onLogout,
      );
      setConfig(res?.config || null);
      setOkMsg('Configurazione salvata.');
    } catch (e) {
      setError(e.message || 'Errore salvataggio');
    } finally {
      setBusy(false);
    }
  };

  const esempioPrezzo = (() => {
    const f = Number(fattore) || 0.9;
    if (f <= 0) return '—';
    return (100 / f).toFixed(2);
  })();

  return (
    <div className="h-full overflow-y-auto bg-gray-900 text-gray-100 p-4 md:p-6">
      <div className="flex items-center gap-3 mb-6">
        <div className="p-2 rounded-lg bg-emerald-900">
          <Wallet className="w-6 h-6 text-emerald-300" />
        </div>
        <div>
          <h2 className="text-xl font-bold">Economia crediti</h2>
          <p className="text-sm text-gray-400">
            Frazione trasferimento deposito→corrente, fattore valore deposito e categorie spesa.
          </p>
        </div>
      </div>

      <label className="block text-sm text-gray-400 mb-1">Campagna</label>
      <select
        className="w-full max-w-md mb-6 bg-gray-800 border border-gray-700 rounded px-3 py-2"
        value={campagnaId}
        onChange={(e) => setCampagnaId(e.target.value)}
      >
        {campagne.map((c) => (
          <option key={c.id} value={c.id}>
            {c.nome}
          </option>
        ))}
      </select>

      {error && <p className="text-red-400 mb-3 text-sm">{error}</p>}
      {okMsg && <p className="text-emerald-400 mb-3 text-sm">{okMsg}</p>}

      <div className="grid gap-4 max-w-xl">
        <div>
          <label className="block text-sm text-gray-400 mb-1">
            Frazione stipendio trasferibile (deposito → corrente)
          </label>
          <input
            type="number"
            step="0.01"
            min="0"
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
            value={frazione}
            onChange={(e) => setFrazione(e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-1">
            Tetto = frazione × stipendio evento (es. 1.50 = fino a 150% dello stipendio).
          </p>
        </div>

        <div>
          <label className="block text-sm text-gray-400 mb-1">Fattore valore deposito (0.01–1.00)</label>
          <input
            type="number"
            step="0.01"
            min="0.01"
            max="1"
            className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2"
            value={fattore}
            onChange={(e) => setFattore(e.target.value)}
          />
          <p className="text-xs text-gray-500 mt-1">
            Bene da 100 CR sul corrente costa {esempioPrezzo} CR dal deposito (prezzo / fattore).
          </p>
        </div>

        <div>
          <p className="text-sm text-gray-400 mb-2">Categorie pagabili con deposito</p>
          <div className="flex flex-wrap gap-3">
            {CATEGORIE.map((c) => (
              <label key={c.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={categorie.includes(c.id)}
                  onChange={() => toggleCat(c.id)}
                />
                {c.label}
              </label>
            ))}
          </div>
        </div>

        <button
          type="button"
          disabled={busy || !campagnaId}
          onClick={save}
          className="mt-2 px-4 py-2 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-50 font-semibold"
        >
          {busy ? 'Salvataggio…' : 'Salva configurazione'}
        </button>

        {config && (
          <pre className="text-xs text-gray-500 bg-gray-950/50 p-3 rounded overflow-x-auto">
            {JSON.stringify(config, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
