import React, { useCallback, useEffect, useState } from 'react';
import { Phone, PhoneIncoming, RefreshCw } from 'lucide-react';
import { getCodaChiamateStaff } from '../../api';
import { useCharacter } from '../CharacterContext';
import { useChiamataVocale } from '../ChiamataVocaleProvider';

const ChiamateVocaliStaffTab = () => {
  const { onLogout } = useCharacter();
  const { call, acceptCall } = useChiamataVocale();
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getCodaChiamateStaff(onLogout);
      setRows(data?.results || []);
    } catch (err) {
      setError(err?.detail || 'Impossibile caricare la coda.');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
    const id = window.setInterval(load, 4000);
    const onVoce = (ev) => {
      const action = ev.detail?.action;
      if (action && String(action).startsWith('VOCE_')) load();
    };
    window.addEventListener('kor35:voce', onVoce);
    return () => {
      window.clearInterval(id);
      window.removeEventListener('kor35:voce', onVoce);
    };
  }, [load]);

  return (
    <div className="h-full overflow-y-auto p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <Phone className="text-emerald-400" size={20} />
            Centralino
          </h2>
          <p className="text-sm text-gray-400 mt-1">
            Chiamate vocali dei personaggi verso lo staff. Tieni questa scheda aperta per rispondere.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          className="inline-flex items-center gap-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 px-3 py-2 text-xs font-semibold text-gray-200"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Aggiorna
        </button>
      </div>

      {error ? <p className="text-sm text-red-400">{error}</p> : null}

      {call?.verso_staff && call.stato === 'ringing' && call.ruolo === 'callee' ? (
        <div className="rounded-xl border border-amber-500/40 bg-amber-950/40 p-4 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-amber-100">
            <PhoneIncoming size={18} />
            <span className="font-semibold">{call.chiamante?.nome} sta chiamando lo staff</span>
          </div>
          <button
            type="button"
            onClick={acceptCall}
            className="rounded-lg bg-emerald-600 hover:bg-emerald-500 px-3 py-2 text-xs font-bold text-white"
          >
            Rispondi
          </button>
        </div>
      ) : null}

      <ul className="space-y-2">
        {rows.length === 0 && !loading ? (
          <li className="text-sm text-gray-500">Nessuna chiamata in attesa.</li>
        ) : null}
        {rows.map((row) => (
          <li
            key={row.id}
            className="rounded-xl border border-gray-800 bg-gray-900/70 p-3 flex items-center justify-between gap-3"
          >
            <div>
              <p className="font-semibold text-white">{row.chiamante?.nome || 'Personaggio'}</p>
              <p className="text-xs text-gray-500">In squillo</p>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
};

export default ChiamateVocaliStaffTab;
