import React, { useEffect, useMemo, useState } from 'react';
import { ShieldCheck, UserRound, Mail, KeyRound, RefreshCw } from 'lucide-react';
import { staffGetArcanaProfiles } from '../../api';

const prettyDate = (value) => {
  if (!value) return '-';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '-';
  return d.toLocaleString('it-IT');
};

export default function ArcanaProfilesTab({ onLogout }) {
  const [profiles, setProfiles] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  const load = async () => {
    setIsLoading(true);
    setError('');
    try {
      const data = await staffGetArcanaProfiles(onLogout);
      setProfiles(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || 'Errore caricamento profili Arcana');
      setProfiles([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const stats = useMemo(() => {
    const total = profiles.length;
    const withLocalPassword = profiles.filter((p) => p?.user?.has_local_password).length;
    const staffUsers = profiles.filter((p) => p?.user?.is_staff || p?.user?.is_superuser).length;
    return { total, withLocalPassword, staffUsers };
  }, [profiles]);

  return (
    <div className="h-full w-full p-4 md:p-6 text-white bg-gray-900 overflow-y-auto">
      <div className="max-w-6xl mx-auto space-y-4">
        <div className="flex items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-black italic text-indigo-300">Profili Arcana SSO</h2>
            <p className="text-xs text-gray-400 mt-1">
              Vista HR dei dati utente ricevuti da Arcana Domine e salvati localmente.
            </p>
          </div>
          <button
            type="button"
            onClick={load}
            className="inline-flex items-center gap-2 px-3 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-xs font-bold"
          >
            <RefreshCw size={14} /> Aggiorna
          </button>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
            <div className="text-xs text-gray-400">Profili totali</div>
            <div className="text-xl font-black text-white mt-1">{stats.total}</div>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
            <div className="text-xs text-gray-400">Password locale configurata</div>
            <div className="text-xl font-black text-emerald-300 mt-1">{stats.withLocalPassword}</div>
          </div>
          <div className="rounded-lg border border-gray-700 bg-gray-800 p-3">
            <div className="text-xs text-gray-400">Utenti staff/admin</div>
            <div className="text-xl font-black text-amber-300 mt-1">{stats.staffUsers}</div>
          </div>
        </div>

        {isLoading && <div className="text-sm text-gray-400">Caricamento profili...</div>}
        {!!error && <div className="text-sm text-red-300">{error}</div>}

        {!isLoading && !error && (
          <div className="space-y-3">
            {profiles.map((row) => (
              <div key={row.id} className="rounded-xl border border-gray-700 bg-gray-800 p-4">
                <div className="flex flex-wrap items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="text-base font-bold text-white truncate">
                      {row.user?.full_name || row.user?.username || 'Utente'}
                    </div>
                    <div className="text-xs text-gray-400 truncate">{row.user?.username}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {(row.user?.is_staff || row.user?.is_superuser) && (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-amber-900/60 text-amber-200 border border-amber-700">
                        <ShieldCheck size={12} /> Staff/Admin
                      </span>
                    )}
                    {row.user?.has_local_password ? (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-emerald-900/60 text-emerald-200 border border-emerald-700">
                        <KeyRound size={12} /> Password locale OK
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-[10px] px-2 py-1 rounded bg-red-900/60 text-red-200 border border-red-700">
                        <KeyRound size={12} /> Password locale assente
                      </span>
                    )}
                  </div>
                </div>

                <div className="grid md:grid-cols-2 gap-3 mt-3 text-sm">
                  <div className="rounded-lg bg-gray-900/50 border border-gray-700 p-3">
                    <div className="text-xs text-gray-400 mb-2">Dati locali</div>
                    <div className="space-y-1">
                      <div className="inline-flex items-center gap-2 text-gray-300">
                        <UserRound size={14} /> ID utente: {row.user?.id ?? '-'}
                      </div>
                      <div className="inline-flex items-center gap-2 text-gray-300">
                        <Mail size={14} /> Email: {row.user?.email || '-'}
                      </div>
                      <div className="text-gray-400 text-xs">Creato: {prettyDate(row.created_at)}</div>
                      <div className="text-gray-400 text-xs">Ultimo update: {prettyDate(row.updated_at)}</div>
                    </div>
                  </div>

                  <div className="rounded-lg bg-gray-900/50 border border-gray-700 p-3">
                    <div className="text-xs text-gray-400 mb-2">Dati Arcana (HR)</div>
                    <div className="space-y-1 text-gray-300">
                      <div>Sub: {row.arcana_profile_hr?.sub ?? '-'}</div>
                      <div>AD ID: {row.arcana_profile_hr?.arcanadomine_id ?? '-'}</div>
                      <div>Username AD: {row.arcana_profile_hr?.username ?? '-'}</div>
                      <div>Nome/Cognome: {row.arcana_profile_hr?.nome || '-'} {row.arcana_profile_hr?.cognome || ''}</div>
                      <div>Email AD: {row.arcana_profile_hr?.email ?? '-'}</div>
                      <div>Tipologia: {row.arcana_profile_hr?.tipologia ?? '-'}</div>
                      <div>Stato: {row.arcana_profile_hr?.stato ?? '-'}</div>
                      <div>Ruoli: {Array.isArray(row.arcana_profile_hr?.ruoli) ? row.arcana_profile_hr.ruoli.join(', ') : '-'}</div>
                    </div>
                  </div>
                </div>

                <details className="mt-3">
                  <summary className="text-xs text-indigo-300 cursor-pointer">Mostra JSON completo Arcana</summary>
                  <pre className="mt-2 p-3 rounded bg-gray-950 border border-gray-700 text-[11px] text-gray-300 overflow-x-auto">
                    {JSON.stringify(row.arcana_profile_json || {}, null, 2)}
                  </pre>
                </details>
              </div>
            ))}
            {profiles.length === 0 && (
              <div className="text-sm text-gray-400">Nessun profilo Arcana salvato al momento.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
