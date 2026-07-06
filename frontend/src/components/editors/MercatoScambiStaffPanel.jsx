import React, { useCallback, useEffect, useState } from 'react';
import { Loader2, RefreshCw, Store } from 'lucide-react';
import { staffGetCarteScambi } from '../../api';
import { CARTA_RARITA_LABEL } from '../../carte/carteConstants';

const STATO_OPTIONS = [
  { value: '', label: 'Tutti gli stati' },
  { value: 'APR', label: 'Aperte' },
  { value: 'ACC', label: 'Accettate' },
  { value: 'ANN', label: 'Annullate' },
  { value: 'SCD', label: 'Scadute' },
];

const STATO_BADGE = {
  APR: 'bg-amber-900 text-amber-100',
  ACC: 'bg-emerald-900 text-emerald-100',
  ANN: 'bg-gray-700 text-gray-300',
  SCD: 'bg-gray-800 text-gray-400',
};

export default function MercatoScambiStaffPanel({ onLogout }) {
  const [loading, setLoading] = useState(true);
  const [stato, setStato] = useState('');
  const [data, setData] = useState({ summary: {}, offerte: [] });
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setMsg('');
    try {
      const payload = await staffGetCarteScambi(onLogout, { stato, limit: 150 });
      setData(payload);
    } catch (e) {
      setMsg(e?.message || 'Caricamento scambi fallito.');
    } finally {
      setLoading(false);
    }
  }, [onLogout, stato]);

  useEffect(() => {
    load();
  }, [load]);

  const { summary, offerte } = data;

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="flex items-center gap-2 text-sm font-bold text-emerald-300">
          <Store size={16} /> Mercato — riepilogo scambi
        </h3>
        <div className="flex flex-wrap items-center gap-2">
          <select
            className="rounded bg-gray-900 px-2 py-1 text-xs text-white"
            value={stato}
            onChange={(e) => setStato(e.target.value)}
          >
            {STATO_OPTIONS.map((opt) => (
              <option key={opt.value || 'all'} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <button type="button" className="rounded bg-gray-800 p-1.5" onClick={load} title="Aggiorna">
            <RefreshCw size={14} />
          </button>
        </div>
      </div>

      {msg && <p className="text-sm text-red-300">{msg}</p>}

      <div className="grid grid-cols-3 gap-2 text-center text-xs">
        <div className="rounded border border-amber-900/50 bg-amber-950/30 p-2">
          <p className="text-lg font-bold text-amber-200">{summary.aperte ?? 0}</p>
          <p className="text-gray-500">Aperte</p>
        </div>
        <div className="rounded border border-emerald-900/50 bg-emerald-950/30 p-2">
          <p className="text-lg font-bold text-emerald-200">{summary.accettate ?? 0}</p>
          <p className="text-gray-500">Completate</p>
        </div>
        <div className="rounded border border-gray-700 bg-gray-900/40 p-2">
          <p className="text-lg font-bold text-gray-300">{summary.annullate ?? 0}</p>
          <p className="text-gray-500">Annullate</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-8 text-gray-400">
          <Loader2 className="animate-spin" size={24} />
        </div>
      ) : (
        <div className="overflow-x-auto rounded border border-gray-700">
          <table className="w-full min-w-[640px] text-left text-xs">
            <thead className="bg-gray-900 text-gray-400">
              <tr>
                <th className="px-2 py-2">Stato</th>
                <th className="px-2 py-2">Offerente</th>
                <th className="px-2 py-2">Accettante</th>
                <th className="px-2 py-2">Offerta</th>
                <th className="px-2 py-2">Richiesta</th>
                <th className="px-2 py-2">Contropartita</th>
                <th className="px-2 py-2">CR</th>
                <th className="px-2 py-2">Data</th>
              </tr>
            </thead>
            <tbody>
              {(offerte || []).map((o) => (
                <tr key={o.id} className="border-t border-gray-800 hover:bg-gray-900/50">
                  <td className="px-2 py-2">
                    <span className={`rounded px-1.5 py-0.5 font-bold ${STATO_BADGE[o.stato] || 'bg-gray-800'}`}>
                      {o.stato}
                    </span>
                  </td>
                  <td className="px-2 py-2">{o.offerente?.nome}</td>
                  <td className="px-2 py-2">{o.accettante?.nome || '—'}</td>
                  <td className="px-2 py-2">
                    {o.carta_offerta?.carta?.nome}
                    <span className="text-gray-500"> ({o.carta_offerta?.carta?.codice})</span>
                  </td>
                  <td className="px-2 py-2">
                    {o.richiesta_carta ? (
                      <>
                        {o.richiesta_carta.nome}
                        <span className="text-gray-500">
                          {' '}
                          ({CARTA_RARITA_LABEL[o.richiesta_carta.rarita] || o.richiesta_carta.rarita})
                        </span>
                      </>
                    ) : null}
                    {o.richiesta_crediti ? (
                      <span>{o.richiesta_carta ? ' + ' : ''}{o.richiesta_crediti} CR</span>
                    ) : null}
                  </td>
                  <td className="px-2 py-2">
                    {o.carta_contropartita?.carta?.nome || '—'}
                  </td>
                  <td className="px-2 py-2">
                    {o.crediti_trasferiti != null ? (
                      <>
                        {o.crediti_trasferiti}
                        {o.commissione_crediti ? (
                          <span className="text-gray-500"> (−{o.commissione_crediti})</span>
                        ) : null}
                      </>
                    ) : '—'}
                  </td>
                  <td className="px-2 py-2 whitespace-nowrap text-gray-500">
                    {(o.accettata_at || o.updated_at || '').slice(0, 16).replace('T', ' ')}
                  </td>
                </tr>
              ))}
              {(offerte || []).length === 0 && (
                <tr>
                  <td colSpan={8} className="px-2 py-6 text-center text-gray-500">
                    Nessuno scambio con i filtri correnti.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
