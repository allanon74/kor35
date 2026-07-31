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
  invalidatePlotRisorseCache,
} from '../../api';
import {
  CAMPAGNA_MODULI_REGISTRY,
  MODULO_ACCESSO_DEFAULT,
  MODULO_ACCESSO_OPTIONS,
  isModuloOverride,
  moduloImpatti,
} from '../../lib/campagnaModuli';

const ROLE_OPTIONS = ['PLAYER', 'REDACTOR', 'STAFFER', 'MASTER', 'HEAD_MASTER'];
const FEATURE_KEYS = [
  'abilita',
  'tessiture',
  'infusioni',
  'oggetti_base',
  'cerimoniali',
  'social',
  'negozi_mercante',
  'carte_collezionabili',
];
const MODE_OPTIONS = ['SHARED', 'EXCLUSIVE'];

const TABS = [
  { id: 'moduli', label: 'Moduli' },
  { id: 'campagne', label: 'Campagne' },
  { id: 'membership', label: 'Membership' },
  { id: 'policy', label: 'Policy catalogo' },
];

const modoBadgeClass = (modo) => {
  if (modo === 'OPEN') return 'text-emerald-300 border-emerald-700 bg-emerald-900/30';
  if (modo === 'TEST') return 'text-amber-200 border-amber-700 bg-amber-900/30';
  return 'text-gray-400 border-gray-600 bg-gray-900/50';
};

const STAFF_TOOL_LABELS = {
  tasks: 'Tasks',
  pilotaggio: 'Pilotaggio',
  'carte-collezionabili': 'Carte collezionabili',
  scommesse: 'Scommesse',
  'negozi-mercante': 'Negozi mercante',
  'creazione-guidata': 'Creazione guidata',
  'social-report': 'Report social',
};

const PLAYER_TAB_LABELS = {
  scommesse: 'Scommesse',
  carte: 'Carte',
  negozi: 'Negozi',
  social: 'Social',
};

const impattiTesto = (key) => {
  const { staffTools, playerTabs } = moduloImpatti(key);
  const parti = [];
  if (playerTabs.length) {
    parti.push(`Tab giocatore: ${playerTabs.map((t) => PLAYER_TAB_LABELS[t] || t).join(', ')}`);
  }
  if (staffTools.length) {
    parti.push(`Tool staff: ${staffTools.map((t) => STAFF_TOOL_LABELS[t] || t).join(', ')}`);
  }
  return parti.join(' · ');
};

const CampaignManager = ({ onLogout }) => {
  const [activeTab, setActiveTab] = useState('moduli');
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
  const [moduliCampagnaId, setModuliCampagnaId] = useState('');

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
      const campagneList = Array.isArray(c) ? c : c.results || [];
      setCampagne(campagneList);
      setMembri(Array.isArray(m) ? m : m.results || []);
      setPolicies(Array.isArray(p) ? p : p.results || []);
      setUsers(Array.isArray(u) ? u : u.results || []);
      setModuliCampagnaId((prev) => {
        if (prev && campagneList.some((x) => String(x.id) === String(prev))) return prev;
        return campagneList[0]?.id ? String(campagneList[0].id) : '';
      });
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

  const moduliRegistry = useMemo(() => {
    const fromApi = campagne.find((c) => Array.isArray(c.moduli_accesso_registry))?.moduli_accesso_registry;
    return Array.isArray(fromApi) && fromApi.length ? fromApi : CAMPAGNA_MODULI_REGISTRY;
  }, [campagne]);

  const selectedModuliCampagna = campagneById[moduliCampagnaId] || null;
  // moduli_accesso = mappa effettiva (default + bridge carte); _raw = solo override espliciti.
  const selectedModuliMap = selectedModuliCampagna?.moduli_accesso || {};
  const selectedModuliRaw = selectedModuliCampagna?.moduli_accesso_raw || {};

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

  const executeAction = useCallback(async (action, { invalidatePlotCache = false } = {}) => {
    setSaving(true);
    setError('');
    try {
      await action();
      await loadAll();
      if (invalidatePlotCache) invalidatePlotRisorseCache();
    } catch (e) {
      setError(e?.message || 'Operazione non riuscita.');
    } finally {
      setSaving(false);
    }
  }, [loadAll]);

  const updateModulo = useCallback((key, modo) => {
    if (!moduliCampagnaId) return;
    executeAction(() => staffUpdateCampagna(moduliCampagnaId, { moduli_accesso: { [key]: modo } }, onLogout));
  }, [executeAction, moduliCampagnaId, onLogout]);

  const resetModulo = useCallback((key) => {
    updateModulo(key, MODULO_ACCESSO_DEFAULT);
  }, [updateModulo]);

  if (loading) return <div className="p-6 text-gray-300">Caricamento campagne...</div>;

  return (
    <div className="p-4 md:p-6 space-y-4 text-white h-full overflow-y-auto">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 className="text-lg font-black uppercase tracking-wide">Campagne</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            Gestione campagne, moduli feature, membership e policy catalogo.
          </p>
        </div>
      </div>

      {error && <div className="bg-red-900/40 border border-red-700 rounded p-3 text-sm">{error}</div>}

      <div
        className="flex flex-wrap gap-1 border-b border-gray-700 pb-0"
        role="tablist"
        aria-label="Sezioni campagne"
      >
        {TABS.map((tab) => {
          const active = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              type="button"
              role="tab"
              aria-selected={active}
              onClick={() => setActiveTab(tab.id)}
              className={[
                'px-3 py-2 text-xs font-bold uppercase tracking-wide rounded-t border-b-2 transition-colors',
                active
                  ? 'border-cyan-400 text-cyan-200 bg-gray-800/80'
                  : 'border-transparent text-gray-400 hover:text-gray-200 hover:bg-gray-800/40',
              ].join(' ')}
            >
              {tab.label}
            </button>
          );
        })}
      </div>

      {activeTab === 'moduli' && (
        <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3" role="tabpanel">
          <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <h2 className="font-black uppercase tracking-wide text-sm">Moduli campagna</h2>
              <p className="text-xs text-gray-400 mt-1 max-w-2xl">
                Abilita o disabilita le feature per campagna.
                {' '}
                <span className="text-amber-200">TEST</span>
                {' '}
                = solo staff/master (e PnG) per collaudi;
                {' '}
                <span className="text-emerald-300">OPEN</span>
                {' '}
                = tutti i giocatori.
                Il modulo Carte resta allineato alla config carte.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {saving && (
                <span className="text-[11px] uppercase tracking-wide text-cyan-300" role="status">
                  Salvataggio...
                </span>
              )}
              <select
                className="bg-gray-900 border border-gray-700 rounded px-2 py-1.5 text-sm min-w-48"
                value={moduliCampagnaId}
                onChange={(e) => setModuliCampagnaId(e.target.value)}
                disabled={saving || !campagne.length}
                aria-label="Campagna per i moduli"
              >
                {!campagne.length && <option value="">Nessuna campagna</option>}
                {campagne.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome}</option>
                ))}
              </select>
            </div>
          </div>
          {!selectedModuliCampagna ? (
            <p className="text-sm text-gray-500">Seleziona una campagna.</p>
          ) : (
            <div className="space-y-2">
              {moduliRegistry.map((row) => {
                const modo = selectedModuliMap[row.key] || row.default || 'OFF';
                const override = isModuloOverride(selectedModuliRaw, row.key);
                const impatti = impattiTesto(row.key);
                return (
                  <div
                    key={row.key}
                    className="grid grid-cols-1 md:grid-cols-12 gap-2 items-center bg-gray-900/60 border border-gray-700 rounded p-3"
                  >
                    <div className="md:col-span-5">
                      <div className="text-sm font-semibold">{row.label}</div>
                      <div className="text-xs text-gray-500">{row.descrizione || row.key}</div>
                      {impatti && <div className="text-[11px] text-gray-600 mt-0.5">{impatti}</div>}
                    </div>
                    <div className="md:col-span-3 flex flex-wrap items-center gap-1.5">
                      <span className={`inline-block text-[10px] uppercase tracking-wide font-bold px-2 py-0.5 rounded border ${modoBadgeClass(modo)}`}>
                        {modo}
                      </span>
                      {override ? (
                        <button
                          type="button"
                          className="text-[10px] uppercase tracking-wide font-bold px-2 py-0.5 rounded border border-cyan-800 text-cyan-300 bg-cyan-900/20 hover:bg-cyan-900/40 disabled:opacity-50"
                          disabled={saving}
                          onClick={() => resetModulo(row.key)}
                          title={`Rimuove l'override e torna al default (${row.default})`}
                        >
                          Ripristina default
                        </button>
                      ) : (
                        <span className="text-[10px] uppercase tracking-wide text-gray-500">
                          default
                        </span>
                      )}
                    </div>
                    <div className="md:col-span-4">
                      <select
                        className="w-full bg-gray-950 border border-gray-700 rounded px-2 py-1.5 text-sm disabled:opacity-50"
                        value={modo}
                        disabled={saving}
                        onChange={(e) => updateModulo(row.key, e.target.value)}
                        aria-label={`Accesso ${row.label}`}
                      >
                        {MODULO_ACCESSO_OPTIONS.map((opt) => (
                          <option key={opt.value} value={opt.value}>{opt.label}</option>
                        ))}
                      </select>
                      {row.key === 'carte' && (
                        <p className="text-[11px] text-gray-500 mt-1">
                          Sincronizzato con la config Carte collezionabili.
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </section>
      )}

      {activeTab === 'campagne' && (
        <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3" role="tabpanel">
          <div className="flex items-center justify-between">
            <h2 className="font-black uppercase tracking-wide text-sm">Elenco campagne</h2>
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
      )}

      {activeTab === 'membership' && (
        <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3" role="tabpanel">
          <div className="flex items-center justify-between">
            <h2 className="font-black uppercase tracking-wide text-sm">Membership utenti-campagna</h2>
            <button className="px-3 py-1.5 bg-cyan-600 rounded text-xs font-bold disabled:opacity-50" disabled={saving || !newMembro.campagna || !newMembro.user} onClick={() => executeAction(async () => {
              await staffCreateCampagnaUtente(newMembro, onLogout);
              setNewMembro({ campagna: '', user: '', ruolo: 'PLAYER', attivo: true });
            }, { invalidatePlotCache: true })}>Nuova membership</button>
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
                <select className="bg-gray-900 border border-gray-700 rounded px-2 py-1" value={m.ruolo} onChange={(e) => executeAction(() => staffUpdateCampagnaUtente(m.id, { ruolo: e.target.value }, onLogout), { invalidatePlotCache: true })}>
                  {ROLE_OPTIONS.map((r) => <option key={r} value={r}>{r}</option>)}
                </select>
                <label className="text-xs flex items-center gap-2">
                  <input type="checkbox" checked={!!m.attivo} onChange={(e) => executeAction(() => staffUpdateCampagnaUtente(m.id, { attivo: e.target.checked }, onLogout), { invalidatePlotCache: true })} />
                  Attivo
                </label>
                <button className="text-xs bg-red-700/40 border border-red-700 rounded px-2 py-1" onClick={() => executeAction(() => staffDeleteCampagnaUtente(m.id, onLogout), { invalidatePlotCache: true })}>Rimuovi</button>
              </div>
            ))}
          </div>
        </section>
      )}

      {activeTab === 'policy' && (
        <section className="bg-gray-800 border border-gray-700 rounded-xl p-4 space-y-3" role="tabpanel">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h2 className="font-black uppercase tracking-wide text-sm">Policy feature (catalogo)</h2>
              <p className="text-xs text-gray-400 mt-1">
                SHARED / EXCLUSIVE sul catalogo tecniche — diverso dai moduli OFF/TEST/OPEN nel tab Moduli.
              </p>
            </div>
            <button className="px-3 py-1.5 bg-cyan-600 rounded text-xs font-bold disabled:opacity-50 shrink-0" disabled={saving || !newPolicy.campagna} onClick={() => executeAction(async () => {
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
      )}
    </div>
  );
};

export default CampaignManager;
