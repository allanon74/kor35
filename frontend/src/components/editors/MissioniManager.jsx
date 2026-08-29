import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  createMissione,
  deleteMissione,
  getEventiOpzioni,
  getMissione,
  getMissioni,
  staffGetKorps,
  updateMissione,
} from '../../api';
import {
  LabeledField,
  StaffFieldGrid,
  StaffModal,
  StaffSection,
  staffInputClass,
} from '../../staff/StaffCrudUi';
import { StaffToolShell } from '../../staff/StaffToolShell';
import SearchableSelect from './SearchableSelect';
import MasterGenericList from './MasterGenericList';

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

const formFromMissione = (row) => ({
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

export default function MissioniManager({ onLogout }) {
  const [items, setItems] = useState([]);
  const [eventi, setEventi] = useState([]);
  const [korps, setKorps] = useState([]);
  const [metaLoaded, setMetaLoaded] = useState(false);
  const [metaLoading, setMetaLoading] = useState(false);
  const metaPromiseRef = useRef(null);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(emptyForm());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  /** Solo lista snella — non blocca su eventi/carriere. */
  const loadList = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const m = await getMissioni({}, onLogout);
      setItems(Array.isArray(m) ? m : m?.results || []);
    } catch (err) {
      setError(err?.message || 'Errore caricamento task');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  /** Meta leggeri solo all’apertura del form (create/edit). */
  const ensureFormMeta = useCallback(async () => {
    if (metaLoaded) return;
    if (!metaPromiseRef.current) {
      setMetaLoading(true);
      metaPromiseRef.current = (async () => {
        const [e, k] = await Promise.all([
          getEventiOpzioni(onLogout),
          staffGetKorps(onLogout),
        ]);
        setEventi(Array.isArray(e) ? e : e?.results || []);
        setKorps(Array.isArray(k) ? k : k?.results || []);
        setMetaLoaded(true);
      })()
        .catch((err) => {
          setError(err?.message || 'Errore caricamento opzioni form');
        })
        .finally(() => {
          setMetaLoading(false);
          metaPromiseRef.current = null;
        });
    }
    await metaPromiseRef.current;
  }, [metaLoaded, onLogout]);

  useEffect(() => { loadList(); }, [loadList]);

  // SearchableSelect usa di default valueKey=id / labelKey=nome (non value/label).
  const korpOptions = useMemo(
    () =>
      korps.map((k) => ({
        id: k.id,
        nome: `${k.nome || `KORP #${k.id}`}${k.fattore_task != null ? ` (×${k.fattore_task})` : ''}`,
      })),
    [korps],
  );

  const openCreate = async () => {
    setForm(emptyForm());
    setModalOpen(true);
    await ensureFormMeta();
  };

  const openEdit = async (row) => {
    setModalOpen(true);
    setForm(formFromMissione({ ...row, eventi: row.eventi || [] }));
    setError('');
    try {
      const [full] = await Promise.all([
        getMissione(row.id, onLogout),
        ensureFormMeta(),
      ]);
      if (full) setForm(formFromMissione(full));
    } catch (err) {
      setError(err?.message || 'Impossibile caricare il dettaglio task');
    }
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
      await loadList();
    } catch (err) {
      setError(err?.message || 'Salvataggio fallito');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id) => {
    setError('');
    try {
      await deleteMissione(id, onLogout);
      await loadList();
    } catch (err) {
      setError(err?.message || 'Eliminazione fallita');
    }
  };

  const missioneColumns = useMemo(
    () => [
      { key: 'titolo', header: 'Titolo', getSortValue: (x) => x.titolo || '', render: (x) => <span className="font-semibold">{x.titolo}</span> },
      {
        key: 'tipo',
        header: 'Tipo',
        getSortValue: (x) => x.tipo_risoluzione || '',
        render: (x) => x.tipo_risoluzione,
        width: 130,
      },
      {
        key: 'korp',
        header: 'KORP',
        getSortValue: (x) => x.korp_nome || 'Generica',
        render: (x) => (x.korp_nome ? `${x.korp_nome}${x.esclusiva ? ' · esclusiva' : ''}` : 'Generica'),
      },
      {
        key: 'crediti',
        header: 'Crediti',
        getSortValue: (x) => Number(x.reward_crediti || 0),
        render: (x) => Number(x.reward_crediti || 0).toLocaleString('it-IT'),
        align: 'right',
        width: 100,
      },
      {
        key: 'prestigio',
        header: 'Prestigio',
        getSortValue: (x) => Number(x.reward_prestigio || 0),
        render: (x) => x.reward_prestigio || 0,
        align: 'center',
        width: 90,
      },
      {
        key: 'eventi',
        header: 'Eventi',
        getSortValue: (x) => x.eventi_count ?? (x.eventi || []).length,
        render: (x) => x.eventi_count ?? (x.eventi || []).length,
        align: 'center',
        width: 80,
      },
      {
        key: 'ordine',
        header: 'Ordine',
        getSortValue: (x) => x.ordine ?? 0,
        render: (x) => x.ordine ?? 0,
        align: 'center',
        width: 80,
      },
    ],
    [],
  );

  const missioneFilterConfig = useMemo(
    () => [
      {
        key: 'tipo_risoluzione',
        label: 'Tipo',
        options: TIPO_OPTS.map((o) => ({ id: o.value, label: o.label })),
      },
      {
        key: 'korp',
        label: 'KORP',
        options: [
          { id: '__none__', label: 'Generica' },
          ...korps.map((k) => ({ id: k.id, label: k.nome })),
        ],
        match: (item, values) =>
          values.some((v) => (v === '__none__' ? !item.korp : String(item.korp) === String(v))),
      },
    ],
    [korps],
  );

  return (
    <StaffToolShell fill>
      {error ? <p className="mb-3 px-4 pt-3 text-sm text-red-400">{error}</p> : null}
      <div className="h-full min-h-0 p-4">
        <MasterGenericList
          title="Tasks (missioni)"
          items={items}
          columns={missioneColumns}
          filterConfig={missioneFilterConfig}
          loading={loading}
          persistKey="staff-tasks-missioni"
          addLabel="Nuova"
          emptyMessage="Nessuna task definita."
          searchPlaceholder="Cerca titolo, KORP…"
          getSearchText={(row) => [row.titolo, row.korp_nome, row.tipo_risoluzione].filter(Boolean).join(' ')}
          getItemLabel={(row) => row.titolo || `Task #${row.id}`}
          onAdd={openCreate}
          onEdit={openEdit}
          onDelete={remove}
        />
      </div>

      <StaffModal open={modalOpen} title={form.id ? 'Modifica task' : 'Nuova task'} onClose={() => setModalOpen(false)} onSave={save} saving={saving} wide>
        {metaLoading && !metaLoaded ? (
          <p className="mb-3 text-xs text-gray-500">Caricamento opzioni…</p>
        ) : null}
        <StaffSection title="Anagrafica">
          <StaffFieldGrid>
            <LabeledField label="Titolo" required>
              <input className={staffInputClass()} value={form.titolo} onChange={(e) => setForm({ ...form, titolo: e.target.value })} />
            </LabeledField>
            <LabeledField label="KORP">
              <SearchableSelect
                options={korpOptions}
                value={form.korp}
                onChange={(v) => setForm({ ...form, korp: v })}
                placeholder="Generica (nessuna)"
                allowClear
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
          <LabeledField label="Descrizione" className="mt-3">
            <textarea className={staffInputClass()} rows={3} value={form.descrizione} onChange={(e) => setForm({ ...form, descrizione: e.target.value })} />
          </LabeledField>
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            <label className="inline-flex items-center gap-2"><input type="checkbox" checked={!!form.esclusiva} onChange={(e) => setForm({ ...form, esclusiva: e.target.checked })} /> Esclusiva KORP</label>
            <label className="inline-flex items-center gap-2"><input type="checkbox" checked={!!form.attiva} onChange={(e) => setForm({ ...form, attiva: e.target.checked })} /> Attiva</label>
            <label className="inline-flex items-center gap-2"><input type="checkbox" checked={!!form.premio_solo_primo} onChange={(e) => setForm({ ...form, premio_solo_primo: e.target.checked })} /> Premio solo al primo</label>
          </div>
        </StaffSection>

        <StaffSection title="Premi">
          <StaffFieldGrid>
            <LabeledField label="Crediti"><input type="number" step="0.01" className={staffInputClass()} value={form.reward_crediti} onChange={(e) => setForm({ ...form, reward_crediti: e.target.value })} /></LabeledField>
            <LabeledField label="Prestigio"><input type="number" className={staffInputClass()} value={form.reward_prestigio} onChange={(e) => setForm({ ...form, reward_prestigio: e.target.value })} /></LabeledField>
            <LabeledField label="Malus Cr non-primo"><input type="number" step="0.01" className={staffInputClass()} value={form.malus_non_primo_crediti} onChange={(e) => setForm({ ...form, malus_non_primo_crediti: e.target.value })} /></LabeledField>
            <LabeledField label="Malus Pr non-primo"><input type="number" className={staffInputClass()} value={form.malus_non_primo_prestigio} onChange={(e) => setForm({ ...form, malus_non_primo_prestigio: e.target.value })} /></LabeledField>
            <LabeledField label="Bonus Cr successive"><input type="number" step="0.01" className={staffInputClass()} value={form.bonus_successive_crediti} onChange={(e) => setForm({ ...form, bonus_successive_crediti: e.target.value })} /></LabeledField>
            <LabeledField label="Bonus Pr successive"><input type="number" className={staffInputClass()} value={form.bonus_successive_prestigio} onChange={(e) => setForm({ ...form, bonus_successive_prestigio: e.target.value })} /></LabeledField>
          </StaffFieldGrid>
        </StaffSection>

        <StaffSection title="Eventi collegati">
          <div className="max-h-48 space-y-1 overflow-y-auto rounded border border-gray-800 p-2">
            {eventi.length === 0 ? (
              <p className="text-xs text-gray-500">{metaLoading ? 'Caricamento…' : 'Nessun evento'}</p>
            ) : eventi.map((ev) => (
              <label key={ev.id} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={(form.eventi_ids || []).map(Number).includes(Number(ev.id))}
                  onChange={() => toggleEvento(ev.id)}
                />
                <span>{ev.titolo}</span>
              </label>
            ))}
          </div>
        </StaffSection>
      </StaffModal>
    </StaffToolShell>
  );
}
