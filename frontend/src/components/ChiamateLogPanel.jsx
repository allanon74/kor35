import React, { useCallback, useEffect, useState } from 'react';
import { Phone, PhoneIncoming, PhoneMissed, PhoneOff, PhoneOutgoing, RefreshCw } from 'lucide-react';
import { getStoricoChiamateVocali } from '../api';

function formatWhen(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('it-IT', {
      day: '2-digit',
      month: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return '';
  }
}

function esitoLabel(esito, direzione) {
  switch (esito) {
    case 'persa':
      return direzione === 'ricevuta' ? 'Persa' : 'Non risposta';
    case 'rifiutata':
      return 'Rifiutata';
    case 'annullata':
      return 'Annullata';
    case 'completata':
      return 'Completata';
    case 'in_corso':
      return 'In corso';
    case 'in_squillo':
      return 'In squillo';
    default:
      return esito || '—';
  }
}

function RowIcon({ direzione, esito }) {
  if (esito === 'persa' && direzione === 'ricevuta') {
    return <PhoneMissed size={16} className="text-amber-400 shrink-0" />;
  }
  if (esito === 'rifiutata' || esito === 'annullata') {
    return <PhoneOff size={16} className="text-red-400 shrink-0" />;
  }
  if (direzione === 'inviata') {
    return <PhoneOutgoing size={16} className="text-sky-400 shrink-0" />;
  }
  return <PhoneIncoming size={16} className="text-emerald-400 shrink-0" />;
}

/** Registro chiamate vocali (inviate / ricevute / perse) nell'area messaggi. */
export default function ChiamateLogPanel({ personaggioId, onLogout, enabled = true }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [open, setOpen] = useState(true);

  const load = useCallback(async () => {
    if (!personaggioId || !enabled) return;
    setLoading(true);
    setError('');
    try {
      const data = await getStoricoChiamateVocali(personaggioId, onLogout, { limit: 40 });
      setRows(Array.isArray(data?.results) ? data.results : []);
    } catch (e) {
      setError(e?.detail || e?.message || 'Impossibile caricare lo storico chiamate.');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [enabled, onLogout, personaggioId]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const onVoce = (ev) => {
      const action = ev?.detail?.action;
      if (
        action === 'VOCE_PERSA' ||
        action === 'VOCE_CHIUSA' ||
        action === 'VOCE_RIFIUTATA' ||
        action === 'VOCE_ACCETTATA'
      ) {
        load();
      }
    };
    window.addEventListener('kor35:voce', onVoce);
    return () => window.removeEventListener('kor35:voce', onVoce);
  }, [load]);

  if (!enabled || !personaggioId) return null;

  const perse = rows.filter((r) => r.esito === 'persa' && r.direzione === 'ricevuta').length;

  return (
    <div className="mb-3 rounded-xl border border-gray-800 bg-gray-950/70 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center justify-between gap-2 px-3 py-2.5 text-left hover:bg-white/5"
      >
        <span className="inline-flex items-center gap-2 text-sm font-semibold text-white">
          <Phone size={16} className="text-emerald-400" />
          Registro chiamate
          {perse > 0 ? (
            <span className="min-w-5 h-5 px-1.5 rounded-full bg-amber-600 text-[10px] leading-5 text-center text-white">
              {perse} pers{perse === 1 ? 'a' : 'e'}
            </span>
          ) : null}
        </span>
        <span className="text-[11px] text-gray-500">{open ? 'Nascondi' : 'Mostra'}</span>
      </button>
      {open ? (
        <div className="border-t border-gray-800 px-2 pb-2">
          <div className="flex justify-end py-1">
            <button
              type="button"
              onClick={load}
              disabled={loading}
              className="inline-flex items-center gap-1 text-[11px] text-gray-400 hover:text-white disabled:opacity-50"
            >
              <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
              Aggiorna
            </button>
          </div>
          {error ? <p className="px-2 pb-2 text-xs text-red-400">{error}</p> : null}
          {loading && rows.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-gray-500">Caricamento…</p>
          ) : rows.length === 0 ? (
            <p className="px-2 py-4 text-center text-xs text-gray-500">Nessuna chiamata recente.</p>
          ) : (
            <ul className="max-h-56 overflow-y-auto space-y-1 custom-scrollbar">
              {rows.map((row) => (
                <li
                  key={row.id}
                  className={`flex items-center gap-2 rounded-lg px-2 py-2 text-xs ${
                    row.esito === 'persa' && row.direzione === 'ricevuta'
                      ? 'bg-amber-950/40 border border-amber-700/30'
                      : 'bg-gray-900/60 border border-transparent'
                  }`}
                >
                  <RowIcon direzione={row.direzione} esito={row.esito} />
                  <div className="min-w-0 flex-1">
                    <p className="text-white truncate font-medium">
                      {row.direzione === 'inviata' ? 'A' : 'Da'} {row.peer_nome || '—'}
                    </p>
                    <p className="text-gray-500 truncate">
                      {esitoLabel(row.esito, row.direzione)} · {formatWhen(row.created_at)}
                    </p>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
