import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarClock, Plus, Trash2, Sparkles, ExternalLink } from 'lucide-react';
import {
  createStaffCompito,
  deleteStaffCompito,
  getStaffCompiti,
  getStaffCompitiCandidati,
  updateStaffCompito,
  completaStaffCompito,
  getStaffCompitiAutomatici,
  updateStaffCompitiAutomatici,
} from '../../api';
import { useCharacter } from '../CharacterContext';
import {
  StaffToolPageTitle,
  StaffToolShell,
  staffMutedClass,
  staffPanelClass,
  staffPrimaryBtnClass,
  staffSecondaryBtnClass,
  staffDangerBtnClass,
} from '../../staff/StaffToolShell';
import StaffEditorModal from './StaffEditorModal';
import { campagnaRuoloLabel } from '../../lib/campagnaRuoli';
import { UiErrorState, UiLoadingState } from '../ui/AsyncState';

const PREAVVISO_PRESETS = [
  { label: '1 ora', minutes: 60 },
  { label: '1 giorno', minutes: 1440 },
  { label: '3 giorni', minutes: 4320 },
  { label: '7 giorni', minutes: 10080 },
];

function toDatetimeLocal(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromDatetimeLocal(value) {
  if (!value) return null;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

function formatScadenza(iso) {
  if (!iso) return '—';
  return new Date(iso).toLocaleString('it-IT', {
    day: '2-digit',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function isAutomatico(c) {
  return !!c?.automatico || String(c?.id || '').startsWith('auto:');
}

const emptyForm = () => ({
  titolo: '',
  descrizione: '',
  scadenza: toDatetimeLocal(new Date(Date.now() + 86400000).toISOString()),
  preavviso_minuti: 1440,
  crea_notifica_scadenza: true,
  assegnatari: [],
});

export default function StaffCalendarioCompitiManager({ onLogout, onOpenTool }) {
  const { isCampaignMaster } = useCharacter();
  const [mainTab, setMainTab] = useState('lista');
  const [items, setItems] = useState([]);
  const [candidati, setCandidati] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState('aperti');
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);

  const [autoItems, setAutoItems] = useState([]);
  const [autoCandidati, setAutoCandidati] = useState([]);
  const [autoLoading, setAutoLoading] = useState(false);
  const [autoDraft, setAutoDraft] = useState({});
  const [autoSaving, setAutoSaving] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const rows = await getStaffCompiti(onLogout);
      setItems(Array.isArray(rows) ? rows : []);
      if (isCampaignMaster) {
        const cand = await getStaffCompitiCandidati(onLogout);
        setCandidati(Array.isArray(cand) ? cand : []);
      }
    } catch (e) {
      setError(e?.message || 'Impossibile caricare i compiti.');
    } finally {
      setLoading(false);
    }
  }, [onLogout, isCampaignMaster]);

  const loadAutomatici = useCallback(async () => {
    if (!isCampaignMaster) return;
    setAutoLoading(true);
    try {
      const data = await getStaffCompitiAutomatici(onLogout);
      const rows = Array.isArray(data?.items) ? data.items : [];
      setAutoItems(rows);
      setAutoCandidati(Array.isArray(data?.candidati) ? data.candidati : []);
      const draft = {};
      rows.forEach((row) => {
        draft[row.codice] = {
          assegnatari: (row.assegnatari || []).map((a) => a.id),
          attivo: row.attivo !== false,
        };
      });
      setAutoDraft(draft);
    } catch (e) {
      setError(e?.message || 'Impossibile caricare i compiti automatici.');
    } finally {
      setAutoLoading(false);
    }
  }, [onLogout, isCampaignMaster]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (mainTab === 'automatici' && isCampaignMaster) {
      loadAutomatici();
    }
  }, [mainTab, isCampaignMaster, loadAutomatici]);

  const filtered = useMemo(() => {
    const now = Date.now();
    return items.filter((c) => {
      if (isAutomatico(c)) {
        if (filter === 'completati') return false;
        if (filter === 'scaduti') return false;
        return c.attivo && (c.conteggio || 0) > 0;
      }
      const allDone =
        (c.assegnazioni || []).length > 0 &&
        (c.assegnazioni || []).every((a) => !!a.completato_at);
      const overdue = c.attivo && !allDone && c.scadenza && new Date(c.scadenza).getTime() < now;
      if (filter === 'aperti') return c.attivo && !allDone;
      if (filter === 'scaduti') return overdue;
      if (filter === 'completati') return allDone || !c.attivo;
      return true;
    });
  }, [items, filter]);

  const toggleAssegnatario = (userId) => {
    setForm((s) => {
      const id = Number(userId);
      const has = s.assegnatari.includes(id);
      return {
        ...s,
        assegnatari: has ? s.assegnatari.filter((x) => x !== id) : [...s.assegnatari, id],
      };
    });
  };

  const selectRuolo = (ruolo) => {
    const ids = candidati
      .filter((c) => {
        if (ruolo === 'MASTER') return c.ruolo === 'MASTER' || c.ruolo === 'HEAD_MASTER';
        return c.ruolo === ruolo;
      })
      .map((c) => c.id);
    setForm((s) => ({ ...s, assegnatari: Array.from(new Set([...s.assegnatari, ...ids])) }));
  };

  const toggleAutoAssegnatario = (codice, userId) => {
    const id = Number(userId);
    setAutoDraft((s) => {
      const cur = s[codice] || { assegnatari: [], attivo: true };
      const has = cur.assegnatari.includes(id);
      return {
        ...s,
        [codice]: {
          ...cur,
          assegnatari: has ? cur.assegnatari.filter((x) => x !== id) : [...cur.assegnatari, id],
        },
      };
    });
  };

  const selectAutoRuolo = (codice, ruolo) => {
    const ids = autoCandidati
      .filter((c) => {
        if (ruolo === 'MASTER') return c.ruolo === 'MASTER' || c.ruolo === 'HEAD_MASTER';
        return c.ruolo === ruolo;
      })
      .map((c) => c.id);
    setAutoDraft((s) => {
      const cur = s[codice] || { assegnatari: [], attivo: true };
      return {
        ...s,
        [codice]: {
          ...cur,
          assegnatari: Array.from(new Set([...cur.assegnatari, ...ids])),
        },
      };
    });
  };

  const saveAutomatici = async () => {
    setAutoSaving(true);
    setError('');
    try {
      const itemsPayload = Object.entries(autoDraft).map(([codice, conf]) => ({
        codice,
        assegnatari: conf.assegnatari || [],
        attivo: conf.attivo !== false,
      }));
      const data = await updateStaffCompitiAutomatici(itemsPayload, onLogout);
      const rows = Array.isArray(data?.items) ? data.items : [];
      setAutoItems(rows);
      await load();
    } catch (e) {
      setError(e?.message || 'Salvataggio compiti automatici fallito.');
    } finally {
      setAutoSaving(false);
    }
  };

  const startCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setShowForm(true);
  };

  const startEdit = (c) => {
    if (isAutomatico(c)) return;
    setEditingId(c.id);
    setForm({
      titolo: c.titolo || '',
      descrizione: c.descrizione || '',
      scadenza: toDatetimeLocal(c.scadenza),
      preavviso_minuti: c.preavviso_minuti ?? 1440,
      crea_notifica_scadenza: c.crea_notifica_scadenza !== false,
      assegnatari: (c.assegnazioni || []).map((a) => a.user),
    });
    setShowForm(true);
  };

  const submit = async (e) => {
    e?.preventDefault?.();
    const scadenza = fromDatetimeLocal(form.scadenza);
    if (!form.titolo.trim() || !scadenza) {
      setError('Titolo e scadenza sono obbligatori.');
      return;
    }
    setSaving(true);
    setError('');
    const payload = {
      titolo: form.titolo.trim(),
      descrizione: form.descrizione,
      scadenza,
      preavviso_minuti: Number(form.preavviso_minuti) || 0,
      crea_notifica_scadenza: !!form.crea_notifica_scadenza,
      assegnatari: form.assegnatari,
      attivo: true,
    };
    try {
      if (editingId) {
        await updateStaffCompito(editingId, payload, onLogout);
      } else {
        await createStaffCompito(payload, onLogout);
      }
      setShowForm(false);
      setEditingId(null);
      await load();
    } catch (err) {
      setError(err?.message || 'Salvataggio fallito.');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    if (String(id).startsWith('auto:')) return;
    if (!window.confirm('Eliminare questo compito?')) return;
    try {
      await deleteStaffCompito(id, onLogout);
      await load();
    } catch (err) {
      setError(err?.message || 'Eliminazione fallita.');
    }
  };

  const toggleCompleta = async (c) => {
    if (isAutomatico(c)) return;
    const done = !!c.mia_assegnazione?.completato_at;
    try {
      await completaStaffCompito(c.id, onLogout, { undo: done });
      await load();
    } catch (err) {
      setError(err?.message || 'Impossibile aggiornare.');
    }
  };

  return (
    <StaffToolShell>
      <StaffToolPageTitle
        icon={<CalendarClock size={22} />}
        title="Calendario compiti"
        description="Scadenze operative per staff, master e aiuto-staff. I compiti automatici appaiono in cima alla lista quando c’è lavoro pendente."
      />

      {error ? <UiErrorState className="mb-4" message={error} /> : null}

      <div className="flex flex-wrap gap-2 mb-4">
        <button
          type="button"
          onClick={() => setMainTab('lista')}
          className={`${staffSecondaryBtnClass} ${mainTab === 'lista' ? 'border-violet-500 text-white' : ''}`}
        >
          Compiti
        </button>
        {isCampaignMaster ? (
          <button
            type="button"
            onClick={() => setMainTab('automatici')}
            className={`${staffSecondaryBtnClass} ${mainTab === 'automatici' ? 'border-violet-500 text-white' : ''}`}
          >
            <Sparkles size={14} /> Compiti automatici
          </button>
        ) : null}
      </div>

      {mainTab === 'automatici' && isCampaignMaster ? (
        <div className="space-y-4">
          <p className={staffMutedClass}>
            Scegli chi riceve i compiti generati automaticamente (in cima alla lista e sulla home) quando
            ci sono proposte in valutazione.
          </p>
          {autoLoading ? (
            <UiLoadingState label="Caricamento configurazione…" />
          ) : (
            <>
              {autoItems.map((row) => {
                const draft = autoDraft[row.codice] || { assegnatari: [], attivo: true };
                return (
                  <div key={row.codice} className={staffPanelClass}>
                    <div className="flex flex-wrap items-start justify-between gap-2 mb-3">
                      <div>
                        <div className="font-bold text-white">{row.titolo_base || row.label}</div>
                        <div className="text-xs text-gray-400 mt-0.5">
                          In valutazione ora: <span className="text-amber-300 font-semibold">{row.conteggio || 0}</span>
                        </div>
                      </div>
                      <label className="flex items-center gap-2 text-sm text-gray-300">
                        <input
                          type="checkbox"
                          checked={draft.attivo !== false}
                          onChange={(e) =>
                            setAutoDraft((s) => ({
                              ...s,
                              [row.codice]: { ...draft, attivo: e.target.checked },
                            }))
                          }
                        />
                        Attivo
                      </label>
                    </div>
                    <div className="flex flex-wrap gap-2 mb-2">
                      <button
                        type="button"
                        className={staffSecondaryBtnClass}
                        onClick={() => selectAutoRuolo(row.codice, 'STAFFER')}
                      >
                        Tutti gli staffer
                      </button>
                      <button
                        type="button"
                        className={staffSecondaryBtnClass}
                        onClick={() => selectAutoRuolo(row.codice, 'MASTER')}
                      >
                        Tutti i master
                      </button>
                    </div>
                    <div className="max-h-40 overflow-y-auto space-y-1">
                      {autoCandidati.map((u) => (
                        <label key={u.id} className="flex items-center gap-2 text-sm text-gray-200">
                          <input
                            type="checkbox"
                            checked={draft.assegnatari.includes(u.id)}
                            onChange={() => toggleAutoAssegnatario(row.codice, u.id)}
                          />
                          <span>
                            {u.username}
                            {u.first_name ? ` (${u.first_name})` : ''}
                            <span className="text-gray-500 text-xs ml-1">{campagnaRuoloLabel(u.ruolo)}</span>
                          </span>
                        </label>
                      ))}
                      {autoCandidati.length === 0 ? (
                        <p className={staffMutedClass}>Nessun master/staffer in campagna.</p>
                      ) : null}
                    </div>
                  </div>
                );
              })}
              <button
                type="button"
                className={staffPrimaryBtnClass}
                disabled={autoSaving}
                onClick={saveAutomatici}
              >
                {autoSaving ? 'Salvataggio…' : 'Salva compiti automatici'}
              </button>
            </>
          )}
        </div>
      ) : (
        <>
          <div className="flex flex-wrap gap-2 mb-4">
            {[
              ['aperti', 'Aperti'],
              ['scaduti', 'In ritardo'],
              ['completati', 'Completati'],
              ['tutti', 'Tutti'],
            ].map(([id, label]) => (
              <button
                key={id}
                type="button"
                onClick={() => setFilter(id)}
                className={`${staffSecondaryBtnClass} ${filter === id ? 'border-violet-500 text-white' : ''}`}
              >
                {label}
              </button>
            ))}
            {isCampaignMaster ? (
              <button type="button" onClick={startCreate} className={`${staffPrimaryBtnClass} ml-auto`}>
                <Plus size={14} /> Nuovo compito
              </button>
            ) : null}
          </div>

          {showForm && isCampaignMaster ? (
            <StaffEditorModal
              title={editingId ? 'Modifica compito' : 'Nuovo compito'}
              saving={saving}
              onClose={() => {
                setShowForm(false);
                setEditingId(null);
              }}
              onSave={submit}
              saveLabel="Salva"
            >
              <div className="space-y-3">
                <input
                  className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm"
                  placeholder="Titolo"
                  value={form.titolo}
                  onChange={(e) => setForm((s) => ({ ...s, titolo: e.target.value }))}
                  required
                />
                <textarea
                  className="w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm min-h-20"
                  placeholder="Descrizione / termini da rispettare"
                  value={form.descrizione}
                  onChange={(e) => setForm((s) => ({ ...s, descrizione: e.target.value }))}
                />
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <label className="text-xs text-gray-400">
                    Scadenza
                    <input
                      type="datetime-local"
                      className="mt-1 w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm text-white"
                      value={form.scadenza}
                      onChange={(e) => setForm((s) => ({ ...s, scadenza: e.target.value }))}
                      required
                    />
                  </label>
                  <label className="text-xs text-gray-400">
                    Preavviso (minuti)
                    <input
                      type="number"
                      min={0}
                      className="mt-1 w-full bg-gray-950 border border-gray-700 rounded px-3 py-2 text-sm text-white"
                      value={form.preavviso_minuti}
                      onChange={(e) => setForm((s) => ({ ...s, preavviso_minuti: e.target.value }))}
                    />
                  </label>
                </div>
                <div className="flex flex-wrap gap-2">
                  {PREAVVISO_PRESETS.map((p) => (
                    <button
                      key={p.minutes}
                      type="button"
                      className={staffSecondaryBtnClass}
                      onClick={() => setForm((s) => ({ ...s, preavviso_minuti: p.minutes }))}
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-300">
                  <input
                    type="checkbox"
                    checked={!!form.crea_notifica_scadenza}
                    onChange={(e) => setForm((s) => ({ ...s, crea_notifica_scadenza: e.target.checked }))}
                  />
                  Notifica anche a scadenza
                </label>
                <div>
                  <div className="text-xs font-bold text-gray-400 uppercase mb-2">Assegnatari</div>
                  <div className="flex flex-wrap gap-2 mb-2">
                    <button type="button" className={staffSecondaryBtnClass} onClick={() => selectRuolo('HELPER')}>
                      Tutti gli aiuto-staff
                    </button>
                    <button type="button" className={staffSecondaryBtnClass} onClick={() => selectRuolo('STAFFER')}>
                      Tutti gli staffer
                    </button>
                    <button type="button" className={staffSecondaryBtnClass} onClick={() => selectRuolo('MASTER')}>
                      Tutti i master
                    </button>
                  </div>
                  <div className="max-h-48 overflow-y-auto space-y-1">
                    {candidati.map((u) => (
                      <label key={u.id} className="flex items-center gap-2 text-sm text-gray-200">
                        <input
                          type="checkbox"
                          checked={form.assegnatari.includes(u.id)}
                          onChange={() => toggleAssegnatario(u.id)}
                        />
                        <span>
                          {u.username}
                          {u.first_name ? ` (${u.first_name})` : ''}
                          <span className="text-gray-500 text-xs ml-1">{campagnaRuoloLabel(u.ruolo)}</span>
                        </span>
                      </label>
                    ))}
                    {candidati.length === 0 ? (
                      <p className={staffMutedClass}>Nessun candidato (helper / staffer / master) in campagna.</p>
                    ) : null}
                  </div>
                </div>
              </div>
            </StaffEditorModal>
          ) : null}

          {loading ? (
            <UiLoadingState label="Caricamento compiti…" />
          ) : (
            <div className="space-y-2">
              {filtered.map((c) => {
                const auto = isAutomatico(c);
                const allDone =
                  !auto &&
                  (c.assegnazioni || []).length > 0 &&
                  (c.assegnazioni || []).every((a) => !!a.completato_at);
                const overdue =
                  !auto &&
                  c.attivo &&
                  !allDone &&
                  c.scadenza &&
                  new Date(c.scadenza).getTime() < Date.now();
                const mineDone = !!c.mia_assegnazione?.completato_at;
                return (
                  <div
                    key={c.id}
                    className={`${staffPanelClass} ${
                      auto ? 'border-amber-800/80 bg-amber-950/20' : overdue ? 'border-red-800' : ''
                    }`}
                  >
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          {auto ? <Sparkles size={14} className="text-amber-300 shrink-0" /> : null}
                          <div className="font-bold text-white">{c.titolo}</div>
                          {auto ? (
                            <span className="text-[10px] uppercase tracking-wide text-amber-300/90 border border-amber-800/60 px-1.5 py-0.5 rounded">
                              Automatico
                            </span>
                          ) : null}
                        </div>
                        <div className={`text-xs mt-0.5 ${overdue ? 'text-red-300 font-bold' : 'text-gray-400'}`}>
                          {auto ? 'Senza scadenza · si chiude quando non restano proposte' : formatScadenza(c.scadenza)}
                          {overdue ? ' · in ritardo' : ''}
                          {allDone ? ' · completato' : ''}
                        </div>
                        {c.descrizione ? (
                          <p className="text-sm text-gray-300 mt-2 whitespace-pre-wrap">{c.descrizione}</p>
                        ) : null}
                        <div className="mt-2 flex flex-wrap gap-1">
                          {(c.assegnazioni || []).map((a) => (
                            <span
                              key={a.id}
                              className={`text-[11px] px-2 py-0.5 rounded border ${
                                a.completato_at
                                  ? 'border-emerald-800 bg-emerald-950/50 text-emerald-200'
                                  : 'border-gray-700 text-gray-300'
                              }`}
                            >
                              {a.username}
                              {a.completato_at ? ' ✓' : ''}
                            </span>
                          ))}
                        </div>
                        {!auto ? (
                          <p className="text-[11px] text-gray-500 mt-2">
                            Preavviso {c.preavviso_minuti} min
                            {c.creato_da_username ? ` · da ${c.creato_da_username}` : ''}
                          </p>
                        ) : null}
                      </div>
                      <div className="flex flex-wrap gap-2">
                        {auto && typeof onOpenTool === 'function' && c.staff_tool ? (
                          <button
                            type="button"
                            className={staffPrimaryBtnClass}
                            onClick={() => onOpenTool(c.staff_tool)}
                          >
                            <ExternalLink size={14} /> Apri proposte
                          </button>
                        ) : null}
                        {!auto && c.mia_assegnazione ? (
                          <button type="button" className={staffSecondaryBtnClass} onClick={() => toggleCompleta(c)}>
                            {mineDone ? 'Riapri il mio' : 'Segna fatto'}
                          </button>
                        ) : null}
                        {!auto && isCampaignMaster ? (
                          <>
                            <button type="button" className={staffSecondaryBtnClass} onClick={() => startEdit(c)}>
                              Modifica
                            </button>
                            <button type="button" className={staffDangerBtnClass} onClick={() => remove(c.id)}>
                              <Trash2 size={14} />
                            </button>
                          </>
                        ) : null}
                      </div>
                    </div>
                  </div>
                );
              })}
              {filtered.length === 0 ? (
                <p className={staffMutedClass}>Nessun compito in questo filtro.</p>
              ) : null}
            </div>
          )}
        </>
      )}
    </StaffToolShell>
  );
}
