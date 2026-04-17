import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  staffCreateCampagna,
  staffCreateCampagnaFeaturePolicy,
  staffCreateCampagnaUtente,
  staffDeleteCampagna,
  staffDeleteCampagnaFeaturePolicy,
  staffDeleteCampagnaUtente,
  staffGetCampagnaFeaturePolicy,
  staffGetCampagnaUtenti,
  staffGetCampagne,
  staffGetUsers,
  staffUpdateCampagna,
  staffUpdateCampagnaFeaturePolicy,
  staffUpdateCampagnaUtente,
} from '../../api';

const ROLE_OPTIONS = ['PLAYER', 'REDACTOR', 'STAFFER', 'MASTER', 'HEAD_MASTER'];
const FEATURE_KEYS = ['abilita', 'tessiture', 'infusioni', 'oggetti_base', 'cerimoniali', 'social'];
const MODE_OPTIONS = ['SHARED', 'EXCLUSIVE'];

const CampaignManager = ({ onLogout }) => {
  const [campagne, setCampagne] = useState([]);
  const [membri, setMembri] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [newCampagna, setNewCampagna] = useState({ nome: '', slug: '', attiva: true });
  const [newMembro, setNewMembro] = useState({ campagna: '', user: '', ruolo: 'PLAYER', attivo: true });
  const [newPolicy, setNewPolicy] = useState({ campagna: '', feature_key: 'social', mode: 'SHARED' });
  const [filterCampagne, setFilterCampagne] = useState('');
  const [filterMembri, setFilterMembri] = useState('');
  const [filterPolicies, setFilterPolicies] = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [c, m, p, u] = await Promise.all([
        staffGetCampagne(onLogout),
        staffGetCampagnaUtenti(onLogout),
        staffGetCampagnaFeaturePolicy(onLogout),
        staffGetUsers(onLogout),
      ]);
      setCampagne(Array.isArray(c) ? c : c.results || []);
      setMembri(Array.isArray(m) ? m : m.results || []);
      setPolicies(Array.isArray(p) ? p : p.results || []);
      setUsers(Array.isArray(u) ? u : u.results || []);
    } catch (e) {
      setError(e?.message || 'Errore caricamento dati campagne.');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const campagneById = useMemo(() => {
    const map = {};
    campagne.forEach((c) => {
      map[c.id] = c;
    });
    return map;
  }, [campagne]);

  const filteredCampagne = useMemo(() => {
    const q = filterCampagne.trim().toLowerCase();
    if (!q) return campagne;
    return campagne.filter((c) => (`${c.nome} ${c.slug}`).toLowerCase().includes(q));
  }, [campagne, filterCampagne]);

  const filteredMembri = useMemo(() => {
    const q = filterMembri.trim().toLowerCase();
    if (!q) return membri;
    return membri.filter((m) => {
      const campName = campagneById[m.campagna]?.nome || m.campagna_nome || '';
      const txt = `${m.user_username || ''} ${m.user || ''} ${campName} ${m.ruolo || ''}`.toLowerCase();
      return txt.includes(q);
    });
  }, [membri, campagneById, filterMembri]);

  const filteredPolicies = useMemo(() => {
    const q = filterPolicies.trim().toLowerCase();
    if (!q) return policies;
    return policies.filter((p) => {
      const campName = campagneById[p.campagna]?.nome || p.campagna_nome || '';
      const txt = `${campName} ${p.feature_key || ''} ${p.mode || ''}`.toLowerCase();
      return txt.includes(q);
    });
  }, [policies, campagneById, filterPolicies]);

  const executeAction = useCallback(async (action) => {
    setSaving(true);
    setError('');
    try {
      await action();
      await loadAll();
    } catch (e) {
      setError(e?.message || 'Operazione non riuscita.');
    } finally {
      setSaving(false);
    }
  }, [loadAll]);

  if (loading) return <div className="p-6 text-gray-300">Caricamento campagne...</div>;

  return (
    <div className="p-4 md:p-6 space-y-6 text-white">
      {error && <div className="bg-red-900/40 border border-red-700 rounded p-3 text-sm">{error}</div>}

      <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-black uppercase tracking-wide text-sm">Campagne</h2>
          <button
            className="px-3 py-1.5 bg-cyan-600 rounded text-xs font-bold disabled:opacity-50"
            disabled={saving || !newCampagna.nome || !newCampagna.slug}
            onClick={() => executeAction(async () => {
              await staffCreateCampagna(newCampagna, onLogout);
              setNewCampagna({ nome: '', slug: '', attiva: true });
            })}
          >
            Nuova campagna
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <input className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" placeholder="Nome campagna" value={newCampagna.nome} onChange={(e) => setNewCampagna((s) => ({ ...s, nome: e.target.value }))} />
          <input className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" placeholder="slug-campagna" value={newCampagna.slug} onChange={(e) => setNewCampagna((s) => ({ ...s, slug: e.target.value }))} />
          <label className="text-xs flex items-center gap-2">
            <input type="checkbox" checked={!!newCampagna.attiva} onChange={(e) => setNewCampagna((s) => ({ ...s, attiva: e.target.checked }))} />
            Attiva
          </label>
        </div>
        <input
          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm"
          placeholder="Filtra campagne per nome/slug..."
          value={filterCampagne}
          onChange={(e) => setFilterCampagne(e.target.value)}
        />
        <div className="space-y-2">
          {filteredCampagne.map((c) => (
            <div key={c.id} className="grid grid-cols-1 md:grid-cols-6 gap-2 bg-gray-900/60 border border-gray-700 rounded p-2">
              <div className="md:col-span-2 text-sm">
                <div className="font-bold">{c.nome}</div>
                <div className="text-gray-400 text-xs">{c.slug}</div>
              </div>
              <label className="text-xs flex items-center gap-2">
                <input type="checkbox" checked={!!c.attiva} onChange={(e) => executeAction(() => staffUpdateCampagna(c.id, { attiva: e.target.checked }, onLogout))} />
                Attiva
              </label>
              <label className="text-xs flex items-center gap-2">
                <input type="checkbox" checked={!!c.is_default} onChange={(e) => executeAction(() => staffUpdateCampagna(c.id, { is_default: e.target.checked }, onLogout))} />
                Default
              </label>
              <label className="text-xs flex items-center gap-2">
                <input type="checkbox" checked={!!c.is_base} onChange={(e) => executeAction(() => staffUpdateCampagna(c.id, { is_base: e.target.checked }, onLogout))} />
                Base
              </label>
              <button className="text-xs bg-red-700/40 border border-red-700 rounded px-2 py-1" onClick={() => executeAction(() => staffDeleteCampagna(c.id, onLogout))}>Elimina</button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-black uppercase tracking-wide text-sm">Membership utenti-campagna</h2>
          <button className="px-3 py-1.5 bg-cyan-600 rounded text-xs font-bold disabled:opacity-50" disabled={saving || !newMembro.campagna || !newMembro.user} onClick={() => executeAction(async () => {
            await staffCreateCampagnaUtente(newMembro, onLogout);
            setNewMembro({ campagna: '', user: '', ruolo: 'PLAYER', attivo: true });
          })}>Nuova membership</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-5 gap-2">
          <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" value={newMembro.campagna} onChange={(e) => setNewMembro((s) => ({ ...s, campagna: e.target.value }))}>
            <option value="">Seleziona campagna</option>
            {campagne.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
          <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" value={newMembro.user} onChange={(e) => setNewMembro((s) => ({ ...s, user: e.target.value }))}>
            <option value="">Seleziona utente</option>
            {users.map((u) => <option key={u.id} value={u.id}>{u.username} ({u.id})</option>)}
          </select>
          <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" value={newMembro.ruolo} onChange={(e) => setNewMembro((s) => ({ ...s, ruolo: e.target.value }))}>
            {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
          </select>
          <label className="text-xs flex items-center gap-2">
            <input type="checkbox" checked={!!newMembro.attivo} onChange={(e) => setNewMembro((s) => ({ ...s, attivo: e.target.checked }))} />
            Attivo
          </label>
        </div>
        <input
          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm"
          placeholder="Filtra membership per utente/campagna/ruolo..."
          value={filterMembri}
          onChange={(e) => setFilterMembri(e.target.value)}
        />
        <div className="space-y-2">
          {filteredMembri.map((m) => (
            <div key={m.id} className="grid grid-cols-1 md:grid-cols-6 gap-2 bg-gray-900/60 border border-gray-700 rounded p-2 text-sm">
              <div className="md:col-span-2">
                <div>{m.user_username || m.user}</div>
                <div className="text-gray-400 text-xs">{campagneById[m.campagna]?.nome || m.campagna_nome || m.campagna}</div>
              </div>
              <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1" value={m.ruolo} onChange={(e) => executeAction(() => staffUpdateCampagnaUtente(m.id, { ruolo: e.target.value }, onLogout))}>
                {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
              </select>
              <label className="text-xs flex items-center gap-2">
                <input type="checkbox" checked={!!m.attivo} onChange={(e) => executeAction(() => staffUpdateCampagnaUtente(m.id, { attivo: e.target.checked }, onLogout))} />
                Attivo
              </label>
              <button className="text-xs bg-red-700/40 border border-red-700 rounded px-2 py-1" onClick={() => executeAction(() => staffDeleteCampagnaUtente(m.id, onLogout))}>Rimuovi</button>
            </div>
          ))}
        </div>
      </section>

      <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-black uppercase tracking-wide text-sm">Policy feature</h2>
          <button className="px-3 py-1.5 bg-cyan-600 rounded text-xs font-bold disabled:opacity-50" disabled={saving || !newPolicy.campagna} onClick={() => executeAction(async () => {
            await staffCreateCampagnaFeaturePolicy(newPolicy, onLogout);
            setNewPolicy({ campagna: '', feature_key: 'social', mode: 'SHARED' });
          })}>Nuova policy</button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
          <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" value={newPolicy.campagna} onChange={(e) => setNewPolicy((s) => ({ ...s, campagna: e.target.value }))}>
            <option value="">Seleziona campagna</option>
            {campagne.map((c) => <option key={c.id} value={c.id}>{c.nome}</option>)}
          </select>
          <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" value={newPolicy.feature_key} onChange={(e) => setNewPolicy((s) => ({ ...s, feature_key: e.target.value }))}>
            {FEATURE_KEYS.map((k) => <option key={k} value={k}>{k}</option>)}
          </select>
          <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm" value={newPolicy.mode} onChange={(e) => setNewPolicy((s) => ({ ...s, mode: e.target.value }))}>
            {MODE_OPTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
        </div>
        <input
          className="w-full bg-gray-900 border border-gray-700 rounded px-2 py-1 text-sm"
          placeholder="Filtra policy per campagna/feature/mode..."
          value={filterPolicies}
          onChange={(e) => setFilterPolicies(e.target.value)}
        />
        <div className="space-y-2">
          {filteredPolicies.map((p) => (
            <div key={p.id} className="grid grid-cols-1 md:grid-cols-6 gap-2 bg-gray-900/60 border border-gray-700 rounded p-2 text-sm">
              <div className="md:col-span-2">{campagneById[p.campagna]?.nome || p.campagna_nome || p.campagna}</div>
              <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1" value={p.feature_key} onChange={(e) => executeAction(() => staffUpdateCampagnaFeaturePolicy(p.id, { feature_key: e.target.value }, onLogout))}>
                {FEATURE_KEYS.map((k) => <option key={k} value={k}>{k}</option>)}
              </select>
              <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1" value={p.mode} onChange={(e) => executeAction(() => staffUpdateCampagnaFeaturePolicy(p.id, { mode: e.target.value }, onLogout))}>
                {MODE_OPTIONS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
              <button className="text-xs bg-red-700/40 border border-red-700 rounded px-2 py-1" onClick={() => executeAction(() => staffDeleteCampagnaFeaturePolicy(p.id, onLogout))}>Elimina</button>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
};

export default CampaignManager;
