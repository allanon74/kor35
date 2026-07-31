import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Target } from 'lucide-react';
import {
  createMissione,
  deleteMissione,
  getEventi,
  getMissioni,
  staffGetCarriere,
  updateMissione,
} from '../../api';
import {
  LabeledField,
  StaffFieldGrid,
  StaffListRow,
  StaffListToolbar,
  StaffModal,
  StaffSection,
  staffInputClass,
} from '../../staff/StaffCrudUi';
import SearchableSelect from './SearchableSelect';

const TIPO_OPTS = [
  { value: 'TECNICA', label: 'Tecnica' },
  { value: 'POST_SOCIAL', label: 'Post Social' },
  { value: 'QUEST', label: 'Quest' },
  { value: 'MANUALE', label: 'Manuale' },
];

const emptyForm = () => ({
  titolo: '',
  descrizione: '',
  korp: null,
  esclusiva: false,
  reward_crediti: 0,
  reward_prestigio: 0,
  tipo_risoluzione: 'MANUALE',
  premio_solo_primo: false,
  malus_non_primo_crediti: 0,
  malus_non_primo_prestigio: 0,
  bonus_successive_crediti: 0,
  bonus_successive_prestigio: 0,
  attiva: true,
  ordine: 0,
  eventi_ids: [],
});

export default function MissioniManager({ onLogout }) {
  const [items, setItems] = useState([]);
  const [eventi, setEventi] = useState([]);
  const [korps, setKorps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [m, e, c] = await Promise.all([
        getMissioni({}, onLogout),
        getEventi(onLogout),
        staffGetCarriere(onLogout),
      ]);
      setItems(Array.isArray(m) ? m : m?.results || []);
      setEventi(Array.isArray(e) ? e : e?.results || []);
      const carriere = Array.isArray(c) ? c : c?.results || [];
      setKorps(carriere.filter((x) => x.tipo_carriera_codice === 'korp' || x.tipo_carriera?.codice === 'korp'));
    } catch (err) {
      setError(err?.message || 'Errore caricamento task');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => { load(); }, [load]);

  // SearchableSelect usa di default valueKey=id / labelKey=nome (non value/label).
  const korpOptions = useMemo(
    () =>
      korps.map((k) => ({
        id: k.id,
        nome: `${k.nome || `KORP #${k.id}`}${k.fattore_task != null ? ` (×${k.fattore_task})` : ''}`,
      })),
    [korps],
  );

  const openCreate = () => { setForm(emptyForm()); setModalOpen(true); };
  const openEdit = (row) => {
    setForm({
      ...emptyForm(),
      id: row.id,
      titolo: row.titolo || '',
      descrizione: row.descrizione || '',
      korp: row.korp || null,
      esclusiva: !!row.esclusiva,
      reward_crediti: row.reward_crediti ?? 0,
      reward_prestigio: row.reward_prestigio ?? 0,
      tipo_risoluzione: row.tipo_risoluzione || 'MANUALE',
      premio_solo_primo: !!row.premio_solo_primo,
      malus_non_primo_crediti: row.malus_non_primo_crediti ?? 0,
      malus_non_primo_prestigio: row.malus_non_primo_prestigio ?? 0,
      bonus_successive_crediti: row.bonus_successive_crediti ?? 0,
      bonus_successive_prestigio: row.bonus_successive_prestigio ?? 0,
      attiva: row.attiva !== false,
      ordine: row.ordine ?? 0,
      eventi_ids: (row.eventi || []).map((ev) => ev.id),
    });
    setModalOpen(true);
  };

  const toggleEvento = (eid) => {
    const id = Number(eid);
    setForm((f) => {
      const set = new Set((f.eventi_ids || []).map(Number));
      if (set.has(id)) set.delete(id);
      else set.add(id);
      return { ...f, eventi_ids: [...set] };
    });
  };

  const save = async () => {
    if (!String(form.titolo || '').trim()) {
      setError('Titolo obbligatorio');
      return;
    }
    setSaving(true);
    setError('');
    try {
      const korpId =
        form.korp === null || form.korp === undefined || form.korp === ''
          ? null
          : Number(form.korp);
      const payload = {
        titolo: form.titolo.trim(),
        descrizione: form.descrizione || '',
        korp: Number.isFinite(korpId) ? korpId : null,
        esclusiva: !!form.esclusiva,
        reward_crediti: form.reward_crediti ?? 0,
        reward_prestigio: Math.max(0, parseInt(form.reward_prestigio, 10) || 0),
        tipo_risoluzione: form.tipo_risoluzione,
        premio_solo_primo: !!form.premio_solo_primo,
        malus_non_primo_crediti: form.malus_non_primo_crediti ?? 0,
        malus_non_primo_prestigio: Math.max(0, parseInt(form.malus_non_primo_prestigio, 10) || 0),
        bonus_successive_crediti: form.bonus_successive_crediti ?? 0,
        bonus_successive_prestigio: Math.max(0, parseInt(form.bonus_successive_prestigio, 10) || 0),
        attiva: !!form.attiva,
        ordine: parseInt(form.ordine, 10) || 0,
        eventi_ids: (form.eventi_ids || []).map(Number),
      };
      if (form.id) await updateMissione(form.id, payload, onLogout);
      else await createMissione(payload, onLogout);
      setModalOpen(false);
      await load();
    } catch (err) {
      setError(err?.message || 'Salvataggio fallito');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (row) => {
    try {
      await deleteMissione(row.id, onLogout);
      await load();
    } catch (err) {
      setError(err?.message || 'Eliminazione fallita');
    }
  };

  return (
    <div className="h-full overflow-y-auto bg-gray-950 p-4 text-gray-100">
      <StaffListToolbar title="Tasks (missioni)" count={items.length} onAdd={openCreate} />
      {error ? <p className="mb-3 text-sm text-red-400">{error}</p> : null}
      {loading ? (
        <p className="text-sm text-gray-500">Caricamento…</p>
      ) : (
        <ul className="space-y-2">
          {items.map((row) => (
            <StaffListRow
              key={row.id}
              onEdit={() => openEdit(row)}
              onDelete={() => remove(row)}
              deleteConfirm={`Eliminare la task «${row.titolo}»?`}
            >
              <div className="font-semibold text-white">{row.titolo}</div>
              <div className="mt-1 flex flex-wrap gap-2 text-[11px] text-gray-400">
                <span className="inline-flex items-center gap-1 rounded bg-gray-800 px-2 py-0.5">
                  <Target size={12} /> {row.tipo_risoluzione}
                </span>
                {row.korp_nome ? (
                  <span className="rounded bg-violet-900/50 px-2 py-0.5 text-violet-200">
                    {row.korp_nome}{row.esclusiva ? ' · esclusiva' : ''}
                  </span>
                ) : (
                  <span className="rounded bg-gray-800 px-2 py-0.5">Generica</span>
                )}
                <span>
                  {Number(row.reward_crediti || 0).toLocaleString('it-IT')} Cr · {row.reward_prestigio || 0} Pr
                </span>
                {row.premio_solo_primo ? <span className="text-amber-300">Solo primo</span> : null}
                <span>{(row.eventi || []).length} eventi</span>
              </div>
            </StaffListRow>
          ))}
        </ul>
      )}

      <StaffModal open={modalOpen} title={form.id ? 'Modifica task' : 'Nuova task'} onClose={() => setModalOpen(false)} onSave={save} saving={saving} wide>
        <StaffSection title="Anagrafica">
          <StaffFieldGrid>
            <LabeledField label="Titolo" required>
              <input className={staffInputClass()} value={form.titolo} onChange={(e) => setForm({ ...form, titolo: e.target.value })} />
            </LabeledField>
            <LabeledField label="KORP">
              <SearchableSelect
                options={korpOptions}
                value={form.korp}
                onChange={(v) => setForm({ ...form, korp: v, esclusiva: v ? form.esclusiva : false })}
                placeholder="— Nessuna (generica) —"
              />
            </LabeledField>
            <LabeledField label="Tipo risoluzione">
              <select className={staffInputClass()} value={form.tipo_risoluzione} onChange={(e) => setForm({ ...form, tipo_risoluzione: e.target.value })}>
                {TIPO_OPTS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </LabeledField>
            <LabeledField label="Ordine">
              <input type="number" className={staffInputClass()} value={form.ordine} onChange={(e) => setForm({ ...form, ordine: e.target.value })} />
            </LabeledField>
          </StaffFieldGrid>
          <LabeledField label="Descrizione">
            <textarea className={staffInputClass()} rows={3} value={form.descrizione} onChange={(e) => setForm({ ...form, descrizione: e.target.value })} />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={!!form.esclusiva} disabled={!form.korp} onChange={(e) => setForm({ ...form, esclusiva: e.target.checked })} />
            Esclusiva KORP (solo membri)
          </label>
        </StaffSection>

        <StaffSection title="Premi">
          <StaffFieldGrid>
            <LabeledField label="Crediti (Cr)">
              <input type="number" step="0.01" className={staffInputClass()} value={form.reward_crediti} onChange={(e) => setForm({ ...form, reward_crediti: e.target.value })} />
            </LabeledField>
            <LabeledField label="Prestigio (Pr)">
              <input type="number" min={0} className={staffInputClass()} value={form.reward_prestigio} onChange={(e) => setForm({ ...form, reward_prestigio: e.target.value })} />
            </LabeledField>
          </StaffFieldGrid>
          <label className="mt-2 flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={!!form.premio_solo_primo} onChange={(e) => setForm({ ...form, premio_solo_primo: e.target.checked })} />
            Premio solo al primo (poi sparisce dalle effettuabili)
          </label>
          {!form.premio_solo_primo ? (
            <StaffFieldGrid>
              <LabeledField label="Malus Cr se non primo">
                <input type="number" step="0.01" className={staffInputClass()} value={form.malus_non_primo_crediti} onChange={(e) => setForm({ ...form, malus_non_primo_crediti: e.target.value })} />
              </LabeledField>
              <LabeledField label="Malus Pr se non primo">
                <input type="number" className={staffInputClass()} value={form.malus_non_primo_prestigio} onChange={(e) => setForm({ ...form, malus_non_primo_prestigio: e.target.value })} />
              </LabeledField>
              <LabeledField label="Bonus Cr successive">
                <input type="number" step="0.01" className={staffInputClass()} value={form.bonus_successive_crediti} onChange={(e) => setForm({ ...form, bonus_successive_crediti: e.target.value })} />
              </LabeledField>
              <LabeledField label="Bonus Pr successive">
                <input type="number" className={staffInputClass()} value={form.bonus_successive_prestigio} onChange={(e) => setForm({ ...form, bonus_successive_prestigio: e.target.value })} />
              </LabeledField>
            </StaffFieldGrid>
          ) : null}
          <label className="mt-2 flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={!!form.attiva} onChange={(e) => setForm({ ...form, attiva: e.target.checked })} />
            Attiva
          </label>
        </StaffSection>

        <StaffSection title="Eventi associati">
          <div className="max-h-48 space-y-1 overflow-y-auto rounded border border-gray-700 p-2">
            {(eventi || []).map((ev) => (
              <label key={ev.id} className="flex items-center gap-2 text-sm text-gray-200">
                <input type="checkbox" checked={(form.eventi_ids || []).map(Number).includes(Number(ev.id))} onChange={() => toggleEvento(ev.id)} />
                {ev.titolo}
              </label>
            ))}
          </div>
        </StaffSection>
      </StaffModal>
    </div>
  );
}
