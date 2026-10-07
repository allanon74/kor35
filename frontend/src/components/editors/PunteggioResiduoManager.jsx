import React, { useEffect, useMemo, useState } from 'react';
import EditorSaveActions from './EditorSaveActions';
import StaffCatalogListEditor from '../../staff/StaffCatalogListEditor';
import { FieldLabel, PUNTEGGI_RESIDUI_TIPI, TextInput } from '../../staff/staffCatalogForm';
import {
  staffGetPunteggiResidui,
  staffCreatePunteggioResiduo,
  staffUpdatePunteggioResiduo,
  staffDeletePunteggioResiduo,
} from '../../api';

const EMPTY_FORM = {
  nome: '',
  sigla: '',
  tipo: 'EL',
  ordine: 0,
  colore: '#1976D2',
  descrizione: '',
};

const tipoLabel = (tipo) => PUNTEGGI_RESIDUI_TIPI.find((t) => t.value === tipo)?.label || tipo;

const FormPanel = ({ value, onClose, onSave, statusMessage = '', statusType = 'success' }) => {
  const [form, setForm] = useState(value || EMPTY_FORM);
  useEffect(() => setForm(value || EMPTY_FORM), [value]);
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));

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
        Qui stanno i punteggi senza maschera propria: elementi, condizioni (Tier 2), culti, vie, arti, archetipi, castoni, nodi, kata.
        Statistiche, aure, caratteristiche e mattoni hanno tool dedicati.
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
          <FieldLabel>Tipo</FieldLabel>
          <select className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.tipo || 'EL'} onChange={(e) => set({ tipo: e.target.value })}>
            {PUNTEGGI_RESIDUI_TIPI.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
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
      <textarea className="w-full min-h-[90px] bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Descrizione" value={form.descrizione || ''} onChange={(e) => set({ descrizione: e.target.value })} />
    </div>
  );
};

export default function PunteggioResiduoManager({ onLogout }) {
  const columns = useMemo(() => [
    { key: 'sigla', header: 'Sigla', width: 70, getSortValue: (x) => x.sigla || '', render: (x) => <span className="font-mono text-indigo-300">{x.sigla}</span> },
    { key: 'nome', header: 'Nome', getSortValue: (x) => x.nome || '', render: (x) => <span className="font-bold break-words">{x.nome}</span> },
    { key: 'tipo', header: 'Tipo', width: 140, getSortValue: (x) => x.tipo || '', render: (x) => tipoLabel(x.tipo) },
  ], []);

  return (
    <StaffCatalogListEditor
      title="Punteggi"
      hint="Catalogo residuo: elementi, condizioni, culti, vie, arti, archetipi, castoni, nodi, kata."
      persistKey="staff-punteggi-residui"
      addLabel="Nuovo punteggio"
      emptyMessage="Nessun punteggio residuo."
      filterConfig={[{
        key: 'tipo',
        label: 'Tipo',
        options: PUNTEGGI_RESIDUI_TIPI.map((opt) => ({ id: opt.value, label: opt.label })),
      }]}
      columns={columns}
      emptyForm={EMPTY_FORM}
      modalSize="lg"
      FormPanel={FormPanel}
      loadItems={async () => {
        const rows = await staffGetPunteggiResidui(onLogout);
        return Array.isArray(rows) ? rows : rows?.results || [];
      }}
      saveItem={async (form, mode, setStatus) => {
        if (!form.nome?.trim() || !form.sigla?.trim()) {
          setStatus({ type: 'warning', message: 'Nome e sigla sono obbligatori.' });
          return false;
        }
        const payload = {
          nome: form.nome.trim(),
          sigla: form.sigla.trim(),
          tipo: form.tipo || 'EL',
          ordine: Number(form.ordine || 0),
          colore: form.colore || '#1976D2',
          descrizione: form.descrizione || '',
        };
        const isExisting = !!form.id && mode !== 'save_as_new';
        return isExisting
          ? staffUpdatePunteggioResiduo(form.id, payload, onLogout)
          : staffCreatePunteggioResiduo(payload, onLogout);
      }}
      deleteItem={(id) => staffDeletePunteggioResiduo(id, onLogout)}
    />
  );
}
