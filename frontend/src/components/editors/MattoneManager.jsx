import React, { useEffect, useMemo, useState } from 'react';
import EditorSaveActions from './EditorSaveActions';
import SearchableSelect from './SearchableSelect';
import RichTextEditor from '../RichTextEditor';
import StaffCatalogListEditor from '../../staff/StaffCatalogListEditor';
import {
  FieldLabel,
  METATALENTO_OPZIONI,
  MOSTRA_CLASSI_ARMA_OPZIONI,
  Section,
  TextInput,
  fkId,
  labeledPunteggi,
  labeledStats,
} from '../../staff/staffCatalogForm';
import {
  staffGetMattoni,
  staffCreateMattone,
  staffUpdateMattone,
  staffDeleteMattone,
  staffGetAure,
  staffGetCaratteristiche,
  staffGetStatistiche,
} from '../../api';

const EMPTY_FORM = {
  nome: '',
  sigla: '',
  tipo: 'MA',
  ordine: 0,
  colore: '#1976D2',
  aura: null,
  caratteristica_associata: null,
  indice_componente: '',
  descrizione_mattone: '',
  dichiarazione: '',
  funzionamento_metatalento: 'NE',
  descrizione_metatalento: '',
  testo_addizionale: '',
  mostra_classi_arma: 'nessuno',
  statistiche_mod: [],
};

const FormPanel = ({ value, onClose, onSave, lookups, statusMessage = '', statusType = 'success' }) => {
  const [form, setForm] = useState(value || EMPTY_FORM);
  useEffect(() => setForm(value || EMPTY_FORM), [value]);
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));
  const rows = form.statistiche_mod || [];

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
          <FieldLabel>Aura</FieldLabel>
          <SearchableSelect options={labeledPunteggi(lookups?.aure)} value={fkId(form.aura)} onChange={(v) => set({ aura: v })} placeholder="Aura" />
        </div>
        <div>
          <FieldLabel>Caratteristica associata</FieldLabel>
          <SearchableSelect options={labeledPunteggi(lookups?.caratteristiche)} value={fkId(form.caratteristica_associata)} onChange={(v) => set({ caratteristica_associata: v })} placeholder="CA / colore nave" />
        </div>
        <div>
          <FieldLabel>Indice componente nave (0-9, vuoto se tessitura)</FieldLabel>
          <TextInput value={form.indice_componente ?? ''} onChange={(v) => set({ indice_componente: v })} placeholder="vuoto" />
        </div>
        <div>
          <FieldLabel>Colore</FieldLabel>
          <input type="color" className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-1" value={form.colore || '#1976D2'} onChange={(e) => set({ colore: e.target.value })} />
        </div>
        <div>
          <FieldLabel>Mostra classi arma</FieldLabel>
          <select className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.mostra_classi_arma || 'nessuno'} onChange={(e) => set({ mostra_classi_arma: e.target.value })}>
            {MOSTRA_CLASSI_ARMA_OPZIONI.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
        <div>
          <FieldLabel>Metatalento</FieldLabel>
          <select className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={form.funzionamento_metatalento || 'NE'} onChange={(e) => set({ funzionamento_metatalento: e.target.value })}>
            {METATALENTO_OPZIONI.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        </div>
      </div>
      <RichTextEditor label="Descrizione mattone" value={form.descrizione_mattone || ''} onChange={(v) => set({ descrizione_mattone: v })} editorHeightClass="min-h-[120px] max-h-[30vh]" />
      <textarea className="w-full min-h-[70px] bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Dichiarazione" value={form.dichiarazione || ''} onChange={(e) => set({ dichiarazione: e.target.value })} />
      <RichTextEditor label="Descrizione metatalento" value={form.descrizione_metatalento || ''} onChange={(v) => set({ descrizione_metatalento: v })} editorHeightClass="min-h-[100px] max-h-[24vh]" />
      <RichTextEditor label="Testo addizionale" value={form.testo_addizionale || ''} onChange={(v) => set({ testo_addizionale: v })} editorHeightClass="min-h-[80px] max-h-[20vh]" />
      <Section title="Modificatori statistica">
        <div className="space-y-2">
          {rows.map((row, i) => (
            <div key={i} className="grid grid-cols-1 sm:grid-cols-[1fr_5rem_7rem_2.75rem] gap-2 min-w-0">
              <SearchableSelect
                options={labeledStats(lookups?.stats)}
                value={fkId(row.statistica)}
                onChange={(v) => {
                  const n = [...rows];
                  n[i] = { ...n[i], statistica: v };
                  set({ statistiche_mod: n });
                }}
                placeholder="Statistica"
              />
              <TextInput type="number" value={row.valore ?? 0} onChange={(v) => {
                const n = [...rows];
                n[i] = { ...n[i], valore: v };
                set({ statistiche_mod: n });
              }} />
              <select className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white" value={row.tipo_modificatore || 'ADD'} onChange={(e) => {
                const n = [...rows];
                n[i] = { ...n[i], tipo_modificatore: e.target.value };
                set({ statistiche_mod: n });
              }}>
                <option value="ADD">+N</option>
                <option value="MOL">xN</option>
              </select>
              <button type="button" className="min-h-11 text-red-400" onClick={() => set({ statistiche_mod: rows.filter((_, idx) => idx !== i) })}>✕</button>
            </div>
          ))}
          <button type="button" className="min-h-11 px-3 rounded bg-indigo-600 text-sm" onClick={() => set({ statistiche_mod: [...rows, { statistica: null, valore: 0, tipo_modificatore: 'ADD' }] })}>+ Statistica</button>
        </div>
      </Section>
    </div>
  );
};

export default function MattoneManager({ onLogout }) {
  const columns = useMemo(() => [
    { key: 'sigla', header: 'Sigla', width: 70, getSortValue: (x) => x.sigla || '', render: (x) => <span className="font-mono text-indigo-300">{x.sigla}</span> },
    { key: 'nome', header: 'Nome', getSortValue: (x) => x.nome || '', render: (x) => <span className="font-bold break-words">{x.nome}</span> },
    { key: 'aura', header: 'Aura', getSortValue: (x) => x.aura_nome || '', render: (x) => x.aura_nome || '—' },
  ], []);

  return (
    <StaffCatalogListEditor
      title="Mattoni"
      hint="Mattoni di tessitura e componenti nave (indice 0-9). L'associazione caratteristica può essere una CA vera o un colore 0C*."
      persistKey="staff-mattoni"
      addLabel="Nuovo mattone"
      emptyMessage="Nessun mattone in catalogo."
      columns={columns}
      emptyForm={EMPTY_FORM}
      modalSize="xl"
      FormPanel={FormPanel}
      loadItems={async () => {
        const [rows, aure, caratteristiche, stats] = await Promise.all([
          staffGetMattoni(onLogout),
          staffGetAure(onLogout),
          staffGetCaratteristiche(onLogout),
          staffGetStatistiche(onLogout),
        ]);
        return {
          items: Array.isArray(rows) ? rows : rows?.results || [],
          lookups: {
            aure: Array.isArray(aure) ? aure : aure?.results || [],
            caratteristiche: Array.isArray(caratteristiche) ? caratteristiche : caratteristiche?.results || [],
            stats: Array.isArray(stats) ? stats : stats?.results || [],
          },
        };
      }}
      saveItem={async (form, mode, setStatus) => {
        if (!form.nome?.trim() || !form.sigla?.trim() || !fkId(form.aura) || !fkId(form.caratteristica_associata)) {
          setStatus({ type: 'warning', message: 'Nome, sigla, aura e caratteristica associata sono obbligatori.' });
          return false;
        }
        const idxRaw = String(form.indice_componente ?? '').trim();
        const payload = {
          nome: form.nome.trim(),
          sigla: form.sigla.trim(),
          tipo: form.tipo || 'MA',
          ordine: Number(form.ordine || 0),
          colore: form.colore || '#1976D2',
          aura: fkId(form.aura),
          caratteristica_associata: fkId(form.caratteristica_associata),
          indice_componente: idxRaw === '' ? null : parseInt(idxRaw, 10),
          descrizione_mattone: form.descrizione_mattone || '',
          dichiarazione: form.dichiarazione || '',
          funzionamento_metatalento: form.funzionamento_metatalento || 'NE',
          descrizione_metatalento: form.descrizione_metatalento || '',
          testo_addizionale: form.testo_addizionale || '',
          mostra_classi_arma: form.mostra_classi_arma || 'nessuno',
          statistiche_mod: (form.statistiche_mod || [])
            .filter((r) => fkId(r.statistica))
            .map((r) => ({
              statistica: fkId(r.statistica),
              valore: Number(r.valore || 0),
              tipo_modificatore: r.tipo_modificatore === 'MOL' ? 'MOL' : 'ADD',
            })),
        };
        const isExisting = !!form.id && mode !== 'save_as_new';
        return isExisting
          ? staffUpdateMattone(form.id, payload, onLogout)
          : staffCreateMattone(payload, onLogout);
      }}
      deleteItem={(id) => staffDeleteMattone(id, onLogout)}
    />
  );
}
