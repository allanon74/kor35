import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CalendarClock, Plus, Trash2 } from 'lucide-react';
import {
  createStaffCompito,
  deleteStaffCompito,
  getStaffCompiti,
  getStaffCompitiCandidati,
  updateStaffCompito,
  completaStaffCompito,
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

const emptyForm = () => ({
  titolo: '',
  descrizione: '',
  scadenza: toDatetimeLocal(new Date(Date.now() + 86400000).toISOString()),
  preavviso_minuti: 1440,
  crea_notifica_scadenza: true,
  assegnatari: [],
});

export default function StaffCalendarioCompitiManager({ onLogout }) {
  const { isCampaignMaster } = useCharacter();
  const [items, setItems] = useState([]);
  const [candidati, setCandidati] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);
  const [filter, setFilter] = useState('aperti');
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [showForm, setShowForm] = useState(false);

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

  useEffect(() => {
    load();
  }, [load]);

  const filtered = useMemo(() => {
    const now = Date.now();
    return items.filter((c) => {
      const allDone =
        (c.assegnazioni || []).length > 0 &&
        (c.assegnazioni || []).every((a) => !!a.completato_at);
      const overdue = c.attivo && !allDone && new Date(c.scadenza).getTime() < now;
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

  const startCreate = () => {
    setEditingId(null);
    setForm(emptyForm());
    setShowForm(true);
  };

  const startEdit = (c) => {
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
    e.preventDefault();
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
    if (!window.confirm('Eliminare questo compito?')) return;
    try {
      await deleteStaffCompito(id, onLogout);
      await load();
    } catch (err) {
      setError(err?.message || 'Eliminazione fallita.');
    }
  };

  const toggleCompleta = async (c) => {
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
        description="Scadenze operative per staff, master e aiuto-staff. Il preavviso arriva via web push; il link iCal si copia dalla home."
      />

      {error ? <UiErrorState className="mb-4" message={error} /> : null}

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
        <form onSubmit={submit} className={`${staffPanelClass} mb-4 space-y-3`}>
          <div className="text-sm font-bold text-white">{editingId ? 'Modifica compito' : 'Nuovo compito'}</div>
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
          <div className="flex gap-2">
            <button type="submit" disabled={saving} className={staffPrimaryBtnClass}>
              {saving ? 'Salvataggio…' : 'Salva'}
            </button>
            <button
              type="button"
              className={staffSecondaryBtnClass}
              onClick={() => {
                setShowForm(false);
                setEditingId(null);
              }}
            >
              Annulla
            </button>
          </div>
        </form>
      ) : null}

      {loading ? (
        <UiLoadingState label="Caricamento compiti…" />
      ) : (
        <div className="space-y-2">
          {filtered.map((c) => {
            const allDone =
              (c.assegnazioni || []).length > 0 &&
              (c.assegnazioni || []).every((a) => !!a.completato_at);
            const overdue =
              c.attivo && !allDone && new Date(c.scadenza).getTime() < Date.now();
            const mineDone = !!c.mia_assegnazione?.completato_at;
            return (
              <div
                key={c.id}
                className={`${staffPanelClass} ${overdue ? 'border-red-800' : ''}`}
              >
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div className="min-w-0">
                    <div className="font-bold text-white">{c.titolo}</div>
                    <div className={`text-xs mt-0.5 ${overdue ? 'text-red-300 font-bold' : 'text-gray-400'}`}>
                      {formatScadenza(c.scadenza)}
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
                    <p className="text-[11px] text-gray-500 mt-2">
                      Preavviso {c.preavviso_minuti} min
                      {c.creato_da_username ? ` · da ${c.creato_da_username}` : ''}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {c.mia_assegnazione ? (
                      <button type="button" className={staffSecondaryBtnClass} onClick={() => toggleCompleta(c)}>
                        {mineDone ? 'Riapri il mio' : 'Segna fatto'}
                      </button>
                    ) : null}
                    {isCampaignMaster ? (
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
    </StaffToolShell>
  );
}
