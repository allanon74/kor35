import React, { useEffect, useMemo, useState } from 'react';
import { getEventi, socialGetStaffEventReport } from '../../api';

const SocialEventReportTab = ({ onLogout }) => {
  const [eventi, setEventi] = useState([]);
  const [selectedEventoId, setSelectedEventoId] = useState('');
  const [rows, setRows] = useState([]);
  const [totali, setTotali] = useState({ post: 0, commenti: 0 });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let mounted = true;
    const loadEventi = async () => {
      try {
        const data = await getEventi(onLogout);
        if (!mounted) return;
        const normalized = Array.isArray(data) ? data : [];
        setEventi(normalized);
      } catch (err) {
        if (!mounted) return;
        setError(err?.message || 'Errore durante il caricamento eventi.');
      }
    };
    loadEventi();
    return () => {
      mounted = false;
    };
  }, [onLogout]);

  useEffect(() => {
    let mounted = true;
    const loadReport = async () => {
      setLoading(true);
      setError('');
      try {
        const data = await socialGetStaffEventReport(selectedEventoId || null, onLogout);
        if (!mounted) return;
        setRows(Array.isArray(data?.rows) ? data.rows : []);
        setTotali(data?.totali || { post: 0, commenti: 0 });
      } catch (err) {
        if (!mounted) return;
        setError(err?.message || 'Errore durante il caricamento report social.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    loadReport();
    return () => {
      mounted = false;
    };
  }, [selectedEventoId, onLogout]);

  const eventoTitleById = useMemo(() => {
    const map = new Map();
    eventi.forEach((e) => map.set(Number(e.id), e.titolo || `Evento #${e.id}`));
    return map;
  }, [eventi]);

  return (
    <div className="p-6 text-white space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-xl font-black tracking-wide uppercase text-pink-300">Report Social per Evento</h2>
        <select
          className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm"
          value={selectedEventoId}
          onChange={(e) => setSelectedEventoId(e.target.value)}
        >
          <option value="">Tutti gli eventi</option>
          {eventi.map((ev) => (
            <option key={ev.id} value={ev.id}>
              {ev.titolo || `Evento #${ev.id}`}
            </option>
          ))}
        </select>
      </div>

      <div className="bg-gray-800/70 border border-gray-700 rounded-xl p-4 text-sm flex gap-8">
        <div>Post: <span className="font-bold text-pink-200">{totali.post || 0}</span></div>
        <div>Commenti: <span className="font-bold text-pink-200">{totali.commenti || 0}</span></div>
        <div>
          Totale interazioni:{' '}
          <span className="font-bold text-pink-200">{(totali.post || 0) + (totali.commenti || 0)}</span>
        </div>
      </div>

      {error && (
        <div className="bg-red-950/60 border border-red-700 rounded-xl p-3 text-red-200 text-sm">
          {error}
        </div>
      )}

      <div className="overflow-auto border border-gray-800 rounded-xl">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-900 text-gray-300 uppercase tracking-wide text-xs">
            <tr>
              <th className="text-left p-3">Evento</th>
              <th className="text-left p-3">Personaggio</th>
              <th className="text-right p-3">Post</th>
              <th className="text-right p-3">Commenti</th>
              <th className="text-right p-3">Totale</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={5} className="p-4 text-gray-400">Caricamento...</td></tr>
            ) : rows.length === 0 ? (
              <tr><td colSpan={5} className="p-4 text-gray-500">Nessun dato disponibile.</td></tr>
            ) : (
              rows.map((r) => (
                <tr key={`${r.evento_id}-${r.personaggio_id}`} className="border-t border-gray-800">
                  <td className="p-3">{eventoTitleById.get(Number(r.evento_id)) || `Evento #${r.evento_id}`}</td>
                  <td className="p-3">{r.personaggio_nome || `PG #${r.personaggio_id}`}</td>
                  <td className="p-3 text-right">{r.post_count}</td>
                  <td className="p-3 text-right">{r.comment_count}</td>
                  <td className="p-3 text-right font-bold text-pink-200">{r.totale}</td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default SocialEventReportTab;
