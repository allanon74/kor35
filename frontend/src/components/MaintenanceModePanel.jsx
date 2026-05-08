import React, { useEffect, useState } from 'react';
import { getAdminMaintenanceConfig, updateAdminMaintenanceConfig } from '../api';

export default function MaintenanceModePanel({ onLogout }) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const [okMsg, setOkMsg] = useState('');
  const [form, setForm] = useState({
    maintenance_mode: false,
    maintenance_public_message: '',
    maintenance_admin_note: '',
  });

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await getAdminMaintenanceConfig(onLogout);
        if (cancelled) return;
        setForm({
          maintenance_mode: !!data?.maintenance_mode,
          maintenance_public_message: String(data?.maintenance_public_message || ''),
          maintenance_admin_note: String(data?.maintenance_admin_note || ''),
        });
      } catch (e) {
        if (cancelled) return;
        setError('Impossibile caricare la configurazione maintenance.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onLogout]);

  const save = async () => {
    setSaving(true);
    setError('');
    setOkMsg('');
    try {
      const data = await updateAdminMaintenanceConfig(form, onLogout);
      setForm({
        maintenance_mode: !!data?.maintenance_mode,
        maintenance_public_message: String(data?.maintenance_public_message || ''),
        maintenance_admin_note: String(data?.maintenance_admin_note || ''),
      });
      setOkMsg('Configurazione maintenance salvata.');
    } catch (e) {
      setError('Salvataggio fallito.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-400">Caricamento configurazione maintenance...</div>;
  }

  return (
    <div className="p-6 max-w-4xl mx-auto">
      <h2 className="text-2xl font-black text-white mb-4">Console Maintenance Mode</h2>
      <div className="rounded-xl border border-amber-500/40 bg-amber-950/30 p-4 mb-6 text-amber-100 text-sm">
        Disponibile solo per admin generali Django. In manutenzione questa e l'unica funzione accessibile nella web app.
      </div>

      <div className="space-y-5">
        <label className="flex items-center gap-3 text-white">
          <input
            type="checkbox"
            checked={form.maintenance_mode}
            onChange={(e) => setForm((prev) => ({ ...prev, maintenance_mode: e.target.checked }))}
            className="w-5 h-5"
          />
          <span className="font-bold">Attiva maintenance mode globale</span>
        </label>

        <div>
          <label className="block text-sm font-bold text-gray-300 mb-2">
            Messaggio pubblico (Wiki/Home)
          </label>
          <textarea
            value={form.maintenance_public_message}
            onChange={(e) => setForm((prev) => ({ ...prev, maintenance_public_message: e.target.value }))}
            rows={4}
            className="w-full rounded-lg bg-gray-900 border border-gray-700 text-white p-3"
          />
        </div>

        <div>
          <label className="block text-sm font-bold text-gray-300 mb-2">
            Nota Admin Django (banner rosso)
          </label>
          <textarea
            value={form.maintenance_admin_note}
            onChange={(e) => setForm((prev) => ({ ...prev, maintenance_admin_note: e.target.value }))}
            rows={4}
            className="w-full rounded-lg bg-gray-900 border border-gray-700 text-white p-3"
          />
        </div>

        {error ? <div className="text-red-400 text-sm">{error}</div> : null}
        {okMsg ? <div className="text-emerald-400 text-sm">{okMsg}</div> : null}

        <button
          type="button"
          onClick={save}
          disabled={saving}
          className="px-5 py-2 rounded-lg bg-indigo-600 text-white font-bold hover:bg-indigo-500 disabled:opacity-60"
        >
          {saving ? 'Salvataggio...' : 'Salva configurazione'}
        </button>
      </div>
    </div>
  );
}
