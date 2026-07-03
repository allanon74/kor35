import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, Trophy } from 'lucide-react';
import {
  staffGetPersonaggioRiservaScommesse,
  staffAdjustPersonaggioRiservaScommesse,
} from '../../api';

const statoClass = (stato) => {
  if (stato === 'VINTA') return 'text-emerald-300';
  if (stato === 'PERSA') return 'text-red-300';
  if (stato === 'PENDING') return 'text-amber-300';
  return 'text-gray-300';
};

const StaffRiservaScommesseTab = ({ personaggioId, onLogout, onDetailUpdated }) => {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState({ riserva: '0', crediti: 0, puntate: [] });
  const [form, setForm] = useState({
    mode: 'delta',
    delta: '',
    valore: '',
    motivo: 'Intervento staff riserva scommesse',
  });

  const load = useCallback(async () => {
    if (!personaggioId) return;
    setLoading(true);
    setError('');
    try {
      const res = await staffGetPersonaggioRiservaScommesse(personaggioId, onLogout);
      setData({
        riserva: res?.riserva ?? '0',
        crediti: res?.crediti ?? 0,
        puntate: Array.isArray(res?.puntate) ? res.puntate : [],
      });
    } catch (e) {
      setError(e.message || 'Errore caricamento riserva.');
      setData({ riserva: '0', crediti: 0, puntate: [] });
    } finally {
      setLoading(false);
    }
  }, [personaggioId, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const handleApply = async () => {
    if (!personaggioId) return;
    setSaving(true);
    setError('');
    try {
      const payload =
        form.mode === 'set'
          ? { mode: 'set', valore: form.valore, motivo: form.motivo }
          : { mode: 'delta', delta: form.delta, motivo: form.motivo };
      const res = await staffAdjustPersonaggioRiservaScommesse(personaggioId, payload, onLogout);
      if (res?.detail && onDetailUpdated) {
        onDetailUpdated(res.detail);
      }
      await load();
      if (form.mode === 'delta') {
        setForm((f) => ({ ...f, delta: '' }));
      }
    } catch (e) {
      setError(e.message || 'Errore aggiornamento riserva.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex justify-center py-12 text-gray-400">
        <Loader2 className="animate-spin mr-2" size={22} />
        Caricamento riserva…
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {error && (
        <div className="text-sm text-red-300 bg-red-950/40 border border-red-800/50 rounded p-2">{error}</div>
      )}

      <div className="grid grid-cols-2 gap-4 text-sm">
        <div className="bg-amber-950/30 border border-amber-800/50 rounded-lg p-4">
          <span className="text-amber-200/80 text-xs uppercase tracking-wide">Riserva scommesse</span>
          <p className="text-3xl font-black text-amber-300 mt-1">{Number(data.riserva).toFixed(2)} CR</p>
          <p className="text-xs text-amber-100/60 mt-2">
            Spendibile solo per puntate; ritiro in contanti solo in evento (giocatore).
          </p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <span className="text-gray-400 text-xs uppercase tracking-wide">Crediti liberi</span>
          <p className="text-2xl font-bold text-gray-100 mt-1">{data.crediti ?? '—'}</p>
        </div>
      </div>

      <div className="bg-gray-800/80 border border-gray-700 rounded-lg p-4 space-y-3">
        <h4 className="text-sm font-bold text-gray-200 flex items-center gap-2">
          <Trophy size={16} className="text-amber-400" />
          Modifica riserva
        </h4>
        <div className="flex flex-wrap gap-2">
          <select
            className="bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm"
            value={form.mode}
            onChange={(e) => setForm((f) => ({ ...f, mode: e.target.value }))}
          >
            <option value="delta">Variazione (+/−)</option>
            <option value="set">Imposta valore assoluto</option>
          </select>
          {form.mode === 'delta' ? (
            <input
              type="number"
              step="0.01"
              placeholder="Δ es. 25 o -10"
              className="bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm w-32"
              value={form.delta}
              onChange={(e) => setForm((f) => ({ ...f, delta: e.target.value }))}
            />
          ) : (
            <input
              type="number"
              min="0"
              step="0.01"
              placeholder="Nuovo saldo"
              className="bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm w-32"
              value={form.valore}
              onChange={(e) => setForm((f) => ({ ...f, valore: e.target.value }))}
            />
          )}
          <input
            className="bg-gray-900 border border-gray-600 rounded px-2 py-1.5 text-sm flex-1 min-w-[160px]"
            placeholder="Motivo (log PG)"
            value={form.motivo}
            onChange={(e) => setForm((f) => ({ ...f, motivo: e.target.value }))}
          />
          <button
            type="button"
            disabled={saving}
            onClick={handleApply}
            className="px-3 py-1.5 bg-amber-700 hover:bg-amber-600 rounded text-sm font-bold disabled:opacity-50"
          >
            {saving ? 'Salvo…' : 'Applica'}
          </button>
        </div>
      </div>

      <div>
        <h4 className="text-sm font-bold text-gray-300 mb-2">Ultime puntate ({data.puntate.length})</h4>
        {data.puntate.length === 0 ? (
          <p className="text-sm text-gray-500 italic">Nessuna puntata registrata.</p>
        ) : (
          <div className="overflow-x-auto border border-gray-700 rounded-lg">
            <table className="w-full text-xs text-left">
              <thead className="bg-gray-900 text-gray-400 uppercase">
                <tr>
                  <th className="p-2">Calendario</th>
                  <th className="p-2">Importo</th>
                  <th className="p-2">Da riserva</th>
                  <th className="p-2">Stato</th>
                  <th className="p-2">Vincita</th>
                  <th className="p-2">Versata riserva</th>
                  <th className="p-2">Ritirata contanti</th>
                </tr>
              </thead>
              <tbody>
                {data.puntate.map((p) => (
                  <tr key={p.id} className="border-t border-gray-800 hover:bg-gray-800/50">
                    <td className="p-2 text-gray-200">{p.calendario_titolo || p.calendario}</td>
                    <td className="p-2">{p.importo} CR</td>
                    <td className="p-2">{p.importo_riserva || '0.00'} CR</td>
                    <td className={`p-2 font-bold ${statoClass(p.stato)}`}>{p.stato}</td>
                    <td className="p-2">{p.vincita != null ? `${p.vincita} CR` : '—'}</td>
                    <td className="p-2">{p.vincita_versata_riserva ?? '—'}</td>
                    <td className="p-2">{p.vincita_ritirata ?? '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default StaffRiservaScommesseTab;
