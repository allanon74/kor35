import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Bell, Calendar, Check, Copy, ListTodo } from 'lucide-react';
import {
  completaStaffCompito,
  getMieiStaffCompiti,
  getStaffCompitiFeedToken,
} from '../api';

function formatScadenza(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleString('it-IT', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function isOverdue(iso, completatoAt) {
  if (completatoAt || !iso) return false;
  return new Date(iso).getTime() < Date.now();
}

export function useMieiStaffCompiti(onLogout, { enabled = true } = {}) {
  const [items, setItems] = useState([]);
  const [icsPath, setIcsPath] = useState('');
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(async () => {
    if (!enabled) {
      setItems([]);
      return;
    }
    setLoading(true);
    try {
      const [rows, token] = await Promise.all([
        getMieiStaffCompiti(onLogout),
        getStaffCompitiFeedToken(onLogout).catch(() => null),
      ]);
      setItems(Array.isArray(rows) ? rows : []);
      if (token?.path) setIcsPath(token.path);
    } catch {
      setItems([]);
    } finally {
      setLoading(false);
    }
  }, [enabled, onLogout]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const aperti = useMemo(
    () => items.filter((c) => c.attivo && !c.mia_assegnazione?.completato_at),
    [items],
  );

  const icsUrl = useMemo(() => {
    if (!icsPath || typeof window === 'undefined') return '';
    return `${window.location.origin}${icsPath}`;
  }, [icsPath]);

  const completa = useCallback(
    async (compitoId, undo = false) => {
      await completaStaffCompito(compitoId, onLogout, { undo });
      await refresh();
    },
    [onLogout, refresh],
  );

  return { items, aperti, icsUrl, loading, refresh, completa };
}

export default function StaffCompitiWidget({ onLogout, compact = false }) {
  const { aperti, icsUrl, loading, completa } = useMieiStaffCompiti(onLogout);

  const copyIcs = useCallback(async () => {
    if (!icsUrl) return;
    try {
      await navigator.clipboard.writeText(icsUrl);
      alert(
        'Link calendario copiato. Incollalo in Google Calendar (Altri calendari → Da URL) o in iOS Calendario (Aggiungi calendario iscritto). Le modifiche sul telefono non tornano in KOR35; le notifiche affidabili restano le push dell’app.',
      );
    } catch {
      window.prompt('Copia il link calendario:', icsUrl);
    }
  }, [icsUrl]);

  if (loading && aperti.length === 0) {
    return null;
  }
  if (aperti.length === 0 && compact) {
    return null;
  }

  return (
    <div className={`rounded-xl border border-sky-800/70 bg-sky-950/40 ${compact ? 'p-3 mb-4' : 'p-4 mb-6'}`}>
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="flex items-center gap-2 min-w-0">
          <ListTodo size={18} className="text-sky-300 shrink-0" />
          <div>
            <h3 className="text-sm font-bold text-sky-100">Compiti in scadenza</h3>
            <p className="text-[11px] text-sky-300/80">
              {aperti.length === 0 ? 'Nessun compito aperto.' : `${aperti.length} da completare`}
            </p>
          </div>
        </div>
        {icsUrl ? (
          <button
            type="button"
            onClick={copyIcs}
            className="inline-flex items-center gap-1 text-[11px] font-semibold text-sky-200 hover:text-white shrink-0"
            title="Copia link iCal"
          >
            <Calendar size={14} />
            <Copy size={12} />
            Calendario
          </button>
        ) : null}
      </div>
      <ul className="space-y-2">
        {aperti.map((c) => {
          const overdue = isOverdue(c.scadenza, c.mia_assegnazione?.completato_at);
          return (
            <li
              key={c.id}
              className={`rounded-lg border p-2.5 ${
                overdue
                  ? 'border-red-800 bg-red-950/40'
                  : 'border-sky-900/80 bg-gray-900/50'
              }`}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="min-w-0">
                  <div className="font-semibold text-white text-sm truncate">{c.titolo}</div>
                  <div className={`text-[11px] mt-0.5 ${overdue ? 'text-red-300 font-bold' : 'text-sky-300'}`}>
                    {formatScadenza(c.scadenza)}
                    {overdue ? ' · in ritardo' : ''}
                  </div>
                  {c.descrizione ? (
                    <p className="text-xs text-gray-400 mt-1 line-clamp-3 whitespace-pre-wrap">{c.descrizione}</p>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => completa(c.id, false)}
                  className="inline-flex items-center gap-1 rounded-md bg-emerald-800 hover:bg-emerald-700 px-2 py-1 text-[11px] font-bold text-emerald-50 shrink-0"
                >
                  <Check size={12} /> Fatto
                </button>
              </div>
            </li>
          );
        })}
      </ul>
      {aperti.length > 0 ? (
        <p className="mt-3 text-[10px] text-sky-400/70 flex items-center gap-1">
          <Bell size={11} /> Preavviso via le notifiche che hai scelto (console Notifiche).
        </p>
      ) : null}
    </div>
  );
}
