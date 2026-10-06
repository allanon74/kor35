import React, { memo, useEffect, useMemo, useState } from 'react';
import { StaffToolShell } from '../../staff/StaffToolShell';
import MasterGenericList from './MasterGenericList';
import StaffEditorModal from './StaffEditorModal';
import EditorSaveActions from './EditorSaveActions';
import SearchableSelect from './SearchableSelect';
import RichTextEditor from '../RichTextEditor';
import {
  staffGetAure,
  staffCreateAura,
  staffUpdateAura,
  staffDeleteAura,
  staffGetStatistiche,
} from '../../api';

const STAT_FK_GROUPS = [
  {
    title: 'Costi tecniche (infusioni / tessiture)',
    fields: [
      { key: 'stat_costo_creazione_infusione', label: 'Costo creazione infusione', flag: 'is_costo' },
      { key: 'stat_costo_creazione_tessitura', label: 'Costo creazione tessitura', flag: 'is_costo' },
      { key: 'stat_costo_acquisto_infusione', label: 'Costo acquisto infusione', flag: 'is_costo' },
      { key: 'stat_costo_acquisto_tessitura', label: 'Costo acquisto tessitura', flag: 'is_costo' },
      { key: 'stat_costo_invio_proposta_infusione', label: 'Costo invio proposta infusione', flag: 'is_costo' },
      { key: 'stat_costo_invio_proposta_tessitura', label: 'Costo invio proposta tessitura', flag: 'is_costo' },
    ],
  },
  {
    title: 'Forgiatura',
    fields: [
      { key: 'stat_costo_forgiatura', label: 'Costo forgiatura', flag: 'is_costo' },
      { key: 'stat_tempo_forgiatura', label: 'Tempo forgiatura', flag: 'is_tempo' },
    ],
  },
  {
    title: 'Creazione oggetti (senza forgiatura)',
    fields: [
      { key: 'stat_costo_creazione_oggetto', label: 'Costo creazione oggetto (Materia)', flag: 'is_costo' },
      { key: 'stat_costo_creazione_mod', label: 'Costo creazione Mod', flag: 'is_costo' },
      { key: 'stat_costo_creazione_innesto', label: 'Costo creazione Innesto', flag: 'is_costo' },
      { key: 'stat_costo_creazione_mutazione', label: 'Costo creazione Mutazione', flag: 'is_costo' },
    ],
  },
  {
    title: 'Cerimoniali',
    fields: [
      { key: 'stat_costo_acquisto_cerimoniale', label: 'Costo acquisto cerimoniale', flag: 'is_costo' },
      { key: 'stat_costo_creazione_cerimoniale', label: 'Costo creazione cerimoniale', flag: 'is_costo' },
      { key: 'stat_costo_invio_proposta_cerimoniale', label: 'Costo invio proposta cerimoniale', flag: 'is_costo' },
    ],
  },
  {
    title: 'Consumabili da tessitura',
    fields: [
      { key: 'stat_costo_consumabili', label: 'Costo creazione consumabili', flag: 'is_costo' },
      { key: 'stat_numero_consumabili', label: 'Numero consumabili', flag: 'is_numero' },
      { key: 'stat_tempo_creazione_consumabili', label: 'Tempo creazione consumabili (sec)', flag: 'is_tempo' },
      { key: 'stat_durata_consumabili', label: 'Durata consumabili (giorni)', flag: 'is_tempo' },
    ],
  },
];

const EMPTY_FORM = {
  nome: '',
  sigla: '',
  descrizione: '',
  ordine: 0,
  colore: '#1976D2',
  is_soprannaturale: false,
  is_generica: false,
  permette_infusioni: false,
  permette_tessiture: false,
  permette_cerimoniali: false,
  produce_aumenti: false,
  produce_potenziamenti: false,
  nome_tipo_aumento: '',
  nome_tipo_potenziamento: '',
  nome_tipo_tessitura: '',
  spegne_a_zero_cariche: false,
  potenziamenti_multi_slot: false,
  aure_infusione_consentite: [],
  ...Object.fromEntries(STAT_FK_GROUPS.flatMap((g) => g.fields.map((f) => [f.key, null]))),
};

function isAuraSistema(item) {
  return /^0[A-Z]/i.test(String(item?.sigla || ''));
}

function fkId(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'object') return value.id ?? null;
  return value;
}

function statOptions(stats, flag) {
  return (stats || [])
    .filter((s) => s[flag])
    .map((s) => ({ id: s.id, nome: `${s.sigla || '—'} — ${s.nome}` }));
}

const Flag = ({ label, checked, onChange }) => (
  <label className="flex items-center gap-2 min-h-11 text-sm text-gray-200">
    <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
    {label}
  </label>
);

const Section = ({ title, children }) => (
  <div className="space-y-2 rounded border border-gray-700 p-3">
    <h3 className="text-xs uppercase tracking-wider text-gray-400 font-bold">{title}</h3>
    {children}
  </div>
);

const AuraFormPanel = ({
  value,
  onClose,
  onSave,
  stats,
  allAure,
  statusMessage = '',
  statusType = 'success',
}) => {
  const [form, setForm] = useState(value || EMPTY_FORM);
  useEffect(() => setForm(value || EMPTY_FORM), [value]);
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));

  const otherAure = useMemo(
    () => (allAure || []).filter((a) => a.id !== form.id),
    [allAure, form.id],
  );
  const selectedInfuse = form.aure_infusione_consentite || [];

  const toggleInfuse = (id) => {
    const next = selectedInfuse.includes(id)
      ? selectedInfuse.filter((x) => x !== id)
      : [...selectedInfuse, id];
    set({ aure_infusione_consentite: next });
  };

  return (
    <div className="space-y-3">
      <EditorSaveActions
        onSave={() => onSave(form, 'save_close')}
        onSaveAndContinue={() => onSave(form, 'save_continue')}
        onSaveAsNew={form?.id ? () => onSave(form, 'save_as_new') : null}
        onSaveAndNew={() => onSave(form, 'save_new_blank')}
        onCancel={onClose}
        saveLabel="Salva"
        statusMessage={statusMessage}
        statusType={statusType}
      />
      <Section title="Anagrafica">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="sm:col-span-2">
            <label className="text-xs text-gray-500 uppercase font-bold">Nome</label>
            <input
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
              value={form.nome || ''}
              onChange={(e) => set({ nome: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">Sigla</label>
            <input
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white font-mono"
              maxLength={3}
              value={form.sigla || ''}
              onChange={(e) => set({ sigla: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">Ordine</label>
            <input
              type="number"
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
              value={form.ordine ?? 0}
              onChange={(e) => set({ ordine: parseInt(e.target.value || '0', 10) })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">Colore</label>
            <input
              type="color"
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-1"
              value={form.colore || '#1976D2'}
              onChange={(e) => set({ colore: e.target.value })}
            />
          </div>
        </div>
        <RichTextEditor
          label="Descrizione"
          value={form.descrizione || ''}
          onChange={(v) => set({ descrizione: v })}
          editorHeightClass="min-h-[180px] max-h-[40vh]"
        />
      </Section>

      <Section title="Natura e tecniche">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <Flag label="Soprannaturale" checked={form.is_soprannaturale} onChange={(v) => set({ is_soprannaturale: v })} />
          <Flag label="Generica" checked={form.is_generica} onChange={(v) => set({ is_generica: v })} />
          <Flag label="Permette infusioni" checked={form.permette_infusioni} onChange={(v) => set({ permette_infusioni: v })} />
          <Flag label="Permette tessiture" checked={form.permette_tessiture} onChange={(v) => set({ permette_tessiture: v })} />
          <Flag label="Permette cerimoniali" checked={form.permette_cerimoniali} onChange={(v) => set({ permette_cerimoniali: v })} />
        </div>
      </Section>

      <Section title="Produzione oggetti">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <Flag label="Produce aumenti (Innesti/Mutazioni)" checked={form.produce_aumenti} onChange={(v) => set({ produce_aumenti: v })} />
          <Flag label="Produce potenziamenti (Mod/Materia)" checked={form.produce_potenziamenti} onChange={(v) => set({ produce_potenziamenti: v })} />
          <Flag label="Si spegne a 0 cariche (tecnologico)" checked={form.spegne_a_zero_cariche} onChange={(v) => set({ spegne_a_zero_cariche: v })} />
          <Flag label="Potenziamenti multi-slot" checked={form.potenziamenti_multi_slot} onChange={(v) => set({ potenziamenti_multi_slot: v })} />
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">Nome tipo aumento</label>
            <input
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
              placeholder="Innesto, Mutazione…"
              value={form.nome_tipo_aumento || ''}
              onChange={(e) => set({ nome_tipo_aumento: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">Nome tipo potenziamento</label>
            <input
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
              placeholder="Mod, Materia…"
              value={form.nome_tipo_potenziamento || ''}
              onChange={(e) => set({ nome_tipo_potenziamento: e.target.value })}
            />
          </div>
          <div>
            <label className="text-xs text-gray-500 uppercase font-bold">Nome tipo tessitura</label>
            <input
              className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
              placeholder="Incantesimo, Preghiera…"
              value={form.nome_tipo_tessitura || ''}
              onChange={(e) => set({ nome_tipo_tessitura: e.target.value })}
            />
          </div>
        </div>
      </Section>

      {STAT_FK_GROUPS.map((group) => (
        <Section key={group.title} title={group.title}>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {group.fields.map((field) => (
              <div key={field.key} className="min-w-0">
                <label className="text-xs text-gray-500 uppercase font-bold">{field.label}</label>
                <SearchableSelect
                  options={statOptions(stats, field.flag)}
                  value={fkId(form[field.key])}
                  onChange={(v) => set({ [field.key]: v })}
                  placeholder="- Nessuna -"
                />
              </div>
            ))}
          </div>
        </Section>
      ))}

      <Section title="Aure infusione consentite">
        <p className="text-xs text-gray-500">Quali altre aure possono essere infuse in questa.</p>
        <div className="flex flex-wrap gap-2">
          {otherAure.map((a) => {
            const on = selectedInfuse.includes(a.id);
            return (
              <button
                key={a.id}
                type="button"
                onClick={() => toggleInfuse(a.id)}
                className={`min-h-11 px-3 py-2 rounded border text-sm ${
                  on
                    ? 'bg-indigo-600 border-indigo-400 text-white'
                    : 'bg-gray-900 border-gray-700 text-gray-300'
                }`}
              >
                {a.sigla ? `${a.sigla} — ${a.nome}` : a.nome}
              </button>
            );
          })}
          {otherAure.length === 0 ? (
            <span className="text-xs text-gray-500">Nessun&apos;altra aura in catalogo.</span>
          ) : null}
        </div>
      </Section>
    </div>
  );
};

const AuraManager = ({ onLogout }) => {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState([]);
  const [editingItem, setEditingItem] = useState(null);
  const [editorStatus, setEditorStatus] = useState({ type: 'success', message: '' });

  const loadItems = async () => {
    try {
      const [aure, statistiche] = await Promise.all([
        staffGetAure(onLogout),
        staffGetStatistiche(onLogout),
      ]);
      setItems(Array.isArray(aure) ? aure : aure?.results || []);
      setStats(Array.isArray(statistiche) ? statistiche : statistiche?.results || []);
    } catch (error) {
      console.error(error);
      setItems([]);
    }
  };

  useEffect(() => {
    loadItems();
  }, []);

  const columns = useMemo(
    () => [
      {
        key: 'sigla',
        header: 'Sigla',
        width: 80,
        getSortValue: (x) => x.sigla || '',
        render: (x) => <span className="font-mono text-indigo-300">{x.sigla}</span>,
      },
      {
        key: 'nome',
        header: 'Nome',
        getSortValue: (x) => x.nome || '',
        render: (x) => (
          <span className="font-bold">
            {x.nome}
            {isAuraSistema(x) ? (
              <span className="ml-2 text-[10px] uppercase text-amber-400">sistema</span>
            ) : null}
          </span>
        ),
      },
      {
        key: 'natura',
        header: 'Natura',
        getSortValue: (x) => (x.is_soprannaturale ? '1' : '0'),
        render: (x) => (
          <span className="text-xs text-gray-400">
            {[
              x.is_soprannaturale && 'soprannaturale',
              x.is_generica && 'generica',
              x.permette_tessiture && 'tessiture',
              x.permette_infusioni && 'infusioni',
              x.permette_cerimoniali && 'cerimoniali',
            ]
              .filter(Boolean)
              .join(', ') || '—'}
          </span>
        ),
      },
      {
        key: 'produce',
        header: 'Produce',
        getSortValue: (x) => x.nome_tipo_potenziamento || x.nome_tipo_aumento || '',
        render: (x) => (
          <span className="text-xs text-gray-400">
            {[x.nome_tipo_aumento, x.nome_tipo_potenziamento, x.nome_tipo_tessitura]
              .filter(Boolean)
              .join(' / ') || '—'}
          </span>
        ),
      },
    ],
    [],
  );

  const saveEditor = async (form, mode = 'save_close') => {
    if (!form.nome?.trim()) {
      setEditorStatus({ type: 'warning', message: 'Il nome è obbligatorio.' });
      return;
    }
    if (!form.sigla?.trim()) {
      setEditorStatus({ type: 'warning', message: 'La sigla è obbligatoria (max 3 caratteri).' });
      return;
    }
    const payload = {
      nome: form.nome.trim(),
      sigla: form.sigla.trim(),
      descrizione: form.descrizione || '',
      ordine: Number(form.ordine || 0),
      colore: form.colore || '#1976D2',
      is_soprannaturale: !!form.is_soprannaturale,
      is_generica: !!form.is_generica,
      permette_infusioni: !!form.permette_infusioni,
      permette_tessiture: !!form.permette_tessiture,
      permette_cerimoniali: !!form.permette_cerimoniali,
      produce_aumenti: !!form.produce_aumenti,
      produce_potenziamenti: !!form.produce_potenziamenti,
      nome_tipo_aumento: (form.nome_tipo_aumento || '').trim(),
      nome_tipo_potenziamento: (form.nome_tipo_potenziamento || '').trim(),
      nome_tipo_tessitura: (form.nome_tipo_tessitura || '').trim(),
      spegne_a_zero_cariche: !!form.spegne_a_zero_cariche,
      potenziamenti_multi_slot: !!form.potenziamenti_multi_slot,
      aure_infusione_consentite: (form.aure_infusione_consentite || []).map((id) => fkId(id)).filter(Boolean),
    };
    STAT_FK_GROUPS.forEach((g) => {
      g.fields.forEach((f) => {
        payload[f.key] = fkId(form[f.key]);
      });
    });
    const isSaveAsNew = mode === 'save_as_new';
    const isExisting = !!form.id && !isSaveAsNew;
    const saved = isExisting
      ? await staffUpdateAura(form.id, payload, onLogout)
      : await staffCreateAura(payload, onLogout);
    const recordName = saved?.nome || payload.nome;
    if (mode === 'save_as_new') {
      setEditorStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
    }
    if (mode === 'save_continue') {
      setEditorStatus({ type: 'success', message: `"${recordName}" salvato.` });
    }
    if (mode === 'save_new_blank') {
      setEditorStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
    }
    if (mode === 'save_close') {
      setEditingItem(null);
      setEditorStatus({ type: 'success', message: '' });
    } else if (mode === 'save_new_blank') {
      setEditingItem({ ...EMPTY_FORM });
    } else if (saved?.id) {
      setEditingItem(saved);
    }
    await loadItems();
  };

  return (
    <StaffToolShell className="space-y-4" fill>
      <p className="text-sm text-gray-400 px-1">
        Catalogo aure (ATE, AMS, …): produzione oggetti, costi tessitura/infusione/cerimoniali
        e aure infusione consentite. I mattoni restano in admin Django.
      </p>
      <MasterGenericList
        title="Aure"
        items={items}
        columns={columns}
        persistKey="staff-aure"
        onAdd={() => setEditingItem({ ...EMPTY_FORM })}
        onEdit={(item) => setEditingItem({
          ...EMPTY_FORM,
          ...item,
          aure_infusione_consentite: (item.aure_infusione_consentite || []).map((x) => fkId(x)),
        })}
        onDelete={async (id) => {
          const item = items.find((x) => x.id === id);
          if (isAuraSistema(item)) {
            setEditorStatus({
              type: 'warning',
              message: `«${item.sigla}» è un'aura di sistema e non si elimina da qui.`,
            });
            return;
          }
          await staffDeleteAura(id, onLogout);
          await loadItems();
        }}
        addLabel="Nuova aura"
        emptyMessage="Nessuna aura in catalogo."
      />
      {editingItem && (
        <StaffEditorModal
          title={editingItem.id ? 'Modifica aura' : 'Nuova aura'}
          size="xl"
          showSave={false}
          onClose={() => {
            setEditingItem(null);
            setEditorStatus({ type: 'success', message: '' });
          }}
        >
          <AuraFormPanel
            value={editingItem}
            stats={stats}
            allAure={items}
            onClose={() => {
              setEditingItem(null);
              setEditorStatus({ type: 'success', message: '' });
            }}
            statusMessage={editorStatus.message}
            statusType={editorStatus.type}
            onSave={saveEditor}
          />
        </StaffEditorModal>
      )}
    </StaffToolShell>
  );
};

export default memo(AuraManager);
