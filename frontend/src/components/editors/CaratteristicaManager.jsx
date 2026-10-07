import React, { useEffect, useMemo, useState } from 'react';
import EditorSaveActions from './EditorSaveActions';
import SearchableSelect from './SearchableSelect';
import StaffCatalogListEditor from '../../staff/StaffCatalogListEditor';
import {
  FieldLabel,
  Section,
  TextInput,
  fkId,
  labeledStats,
} from '../../staff/staffCatalogForm';
import {
  staffGetCaratteristiche,
  staffCreateCaratteristica,
  staffUpdateCaratteristica,
  staffDeleteCaratteristica,
  staffGetStatistiche,
} from '../../api';

const EMPTY_FORM = {
  nome: '',
  sigla: '',
  descrizione: '',
  ordine: 0,
  colore: '#1976D2',
  modificatori: [],
};

const FormPanel = ({ value, onClose, onSave, lookups, statusMessage = '', statusType = 'success' }) => {
  const [form, setForm] = useState(value || EMPTY_FORM);
  useEffect(() => setForm(value || EMPTY_FORM), [value]);
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));
  const mods = form.modificatori || [];
  const stats = lookups?.stats || [];

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
      <p className="text-xs text-gray-400">
        Include anche i colori nave 0C0–0C9 (catalogo componenti). Nelle abilità restano filtrati.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <div className="sm:col-span-2">
          <FieldLabel>Nome</FieldLabel>
          <TextInput value={form.nome} onChange={(v) => set({ nome: v })} />
        </div>
        <div>
          <FieldLabel>Sigla</FieldLabel>
          <TextInput className="font-mono" maxLength={3} value={form.sigla} onChange={(v) => set({ sigla: v })} />
        </div>
        <div>
          <FieldLabel>Ordine</FieldLabel>
          <TextInput type="number" value={form.ordine ?? 0} onChange={(v) => set({ ordine: parseInt(v || '0', 10) })} />
        </div>
        <div>
          <FieldLabel>Colore</FieldLabel>
          <input type="color" className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-1" value={form.colore || '#1976D2'} onChange={(e) => set({ colore: e.target.value })} />
        </div>
      </div>
      <textarea
        className="w-full min-h-[90px] bg-gray-800 border border-gray-700 rounded p-2 text-white"
        placeholder="Descrizione"
        value={form.descrizione || ''}
        onChange={(e) => set({ descrizione: e.target.value })}
      />
      <Section title="Modificatori alle statistiche">
        <div className="space-y-2">
          {mods.map((row, i) => (
            <div key={i} className="grid grid-cols-1 sm:grid-cols-[1fr_5rem_5rem_2.75rem] gap-2 min-w-0">
              <SearchableSelect
                options={labeledStats(stats)}
                value={fkId(row.statistica_modificata)}
                onChange={(v) => {
                  const n = [...mods];
                  n[i] = { ...n[i], statistica_modificata: v };
                  set({ modificatori: n });
                }}
                placeholder="Statistica"
              />
              <TextInput type="number" step="0.01" value={row.modificatore ?? 1} onChange={(v) => {
                const n = [...mods];
                n[i] = { ...n[i], modificatore: v };
                set({ modificatori: n });
              }} />
              <TextInput type="number" value={row.ogni_x_punti ?? 1} onChange={(v) => {
                const n = [...mods];
                n[i] = { ...n[i], ogni_x_punti: parseInt(v || '1', 10) };
                set({ modificatori: n });
              }} />
              <button type="button" className="min-h-11 min-w-11 text-red-400" onClick={() => set({ modificatori: mods.filter((_, idx) => idx !== i) })}>✕</button>
            </div>
          ))}
          <button
            type="button"
            className="min-h-11 px-3 rounded bg-indigo-600 text-sm"
            onClick={() => set({ modificatori: [...mods, { statistica_modificata: null, modificatore: 1, ogni_x_punti: 1 }] })}
          >
            + Modificatore
          </button>
        </div>
      </Section>
    </div>
  );
};

export default function CaratteristicaManager({ onLogout }) {
  const columns = useMemo(() => [
    { key: 'sigla', header: 'Sigla', width: 80, getSortValue: (x) => x.sigla || '', render: (x) => <span className="font-mono text-indigo-300">{x.sigla}</span> },
    { key: 'nome', header: 'Nome', getSortValue: (x) => x.nome || '', render: (x) => <span className="font-bold break-words">{x.nome}</span> },
    { key: 'mods', header: 'Mod', width: 70, getSortValue: (x) => (x.modificatori || []).length, render: (x) => (x.modificatori || []).length, align: 'center' },
  ], []);

  return (
    <StaffCatalogListEditor
      title="Caratteristiche"
      hint="Le 10 CA di scheda e i colori 0C* dei componenti nave. I modificatori (es. +1 ogni 2 punti) restano qui."
      persistKey="staff-caratteristiche"
      addLabel="Nuova caratteristica"
      emptyMessage="Nessuna caratteristica in catalogo."
      columns={columns}
      emptyForm={EMPTY_FORM}
      modalSize="lg"
      FormPanel={FormPanel}
      loadItems={async () => {
        const [rows, stats] = await Promise.all([
          staffGetCaratteristiche(onLogout),
          staffGetStatistiche(onLogout),
        ]);
        return {
          items: Array.isArray(rows) ? rows : rows?.results || [],
          lookups: { stats: Array.isArray(stats) ? stats : stats?.results || [] },
        };
      }}
      saveItem={async (form, mode, setStatus) => {
        if (!form.nome?.trim() || !form.sigla?.trim()) {
          setStatus({ type: 'warning', message: 'Nome e sigla sono obbligatori.' });
          return false;
        }
        const payload = {
          nome: form.nome.trim(),
          sigla: form.sigla.trim(),
          descrizione: form.descrizione || '',
          ordine: Number(form.ordine || 0),
          colore: form.colore || '#1976D2',
          modificatori: (form.modificatori || [])
            .filter((r) => fkId(r.statistica_modificata))
            .map((r) => ({
              statistica_modificata: fkId(r.statistica_modificata),
              modificatore: Number(r.modificatore || 0),
              ogni_x_punti: Number(r.ogni_x_punti || 1),
            })),
        };
        const isExisting = !!form.id && mode !== 'save_as_new';
        return isExisting
          ? staffUpdateCaratteristica(form.id, payload, onLogout)
          : staffCreateCaratteristica(payload, onLogout);
      }}
      deleteItem={(id) => staffDeleteCaratteristica(id, onLogout)}
    />
  );
}
