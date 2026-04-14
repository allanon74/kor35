import React, { memo, useEffect, useMemo, useState } from 'react';
import { ArrowLeft, X } from 'lucide-react';
import MasterGenericList from './MasterGenericList';
import EditorSaveActions from './EditorSaveActions';
import RichTextEditor from '../RichTextEditor';
import {
  staffGetDichiarazioni,
  staffCreateDichiarazione,
  staffUpdateDichiarazione,
  staffDeleteDichiarazione,
} from '../../api';

const TIPO_OPZIONI = [
  { value: 'DAN_NRM', label: 'Danno - Normale' },
  { value: 'DAN_ELM', label: 'Danno - Elementale' },
  { value: 'DAN_SUF', label: 'Danno - Suffissi' },
  { value: 'EFF_DUR', label: 'Effetto - Durata' },
  { value: 'EFF_IST', label: 'Effetto - Istantaneo' },
  { value: 'SUF_RNG', label: 'Suffisso - Rango' },
  { value: 'AFF_EFF', label: 'Affisso - Efficacia' },
  { value: 'SUF_TRG', label: 'Suffisso - Bersaglio' },
  { value: 'PRE_MOL', label: 'Prefisso - Moltiplicativo' },
  { value: 'PRM_CAP', label: 'Premessa - Capacita' },
  { value: 'PRM_SRC', label: 'Premessa - Sorgente' },
  { value: 'PRM_LVL', label: 'Premessa - Livello' },
  { value: 'PRM_TIP', label: 'Premessa - Tipologia' },
  { value: 'PRE_FRM', label: 'Prefisso - Forma' },
  { value: 'EFF_SPC', label: 'Effetto - Speciale' },
  { value: 'GLOS', label: 'Glossario' },
];

const TIPO_DICHIARAZIONI = TIPO_OPZIONI.filter((opt) => opt.value !== 'GLOS');

const EMPTY_FORM = { nome: '', tipo: 'GLOS', dichiarazione: '', descrizione: '' };

const DichiarazioneFormModal = ({ isOpen, value, onClose, onSave, isGlossario, statusMessage = '', statusType = 'success' }) => {
  const [form, setForm] = useState(value || {});
  useEffect(() => setForm(value || {}), [value]);
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4">
      <div className="w-full max-w-2xl bg-gray-900 border border-gray-700 rounded-xl">
        <div className="p-4 border-b border-gray-700 flex items-center justify-between">
          <h3 className="text-lg font-bold text-white">
            {form?.id ? `Modifica ${isGlossario ? 'voce glossario' : 'dichiarazione'}` : `Nuova ${isGlossario ? 'voce glossario' : 'dichiarazione'}`}
          </h3>
          <button onClick={onClose}><X className="text-gray-400" size={18} /></button>
        </div>
        <div className="p-4 space-y-3">
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Nome interno"
            value={form.nome || ''}
            onChange={(e) => setForm({ ...form, nome: e.target.value })}
          />
          {isGlossario ? (
            <div className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white">
              Tipo: Glossario
            </div>
          ) : (
            <select
              className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
              value={form.tipo || TIPO_DICHIARAZIONI[0].value}
              onChange={(e) => setForm({ ...form, tipo: e.target.value })}
            >
              {TIPO_DICHIARAZIONI.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          )}
          <input
            className="w-full bg-gray-800 border border-gray-700 rounded p-2 text-white"
            placeholder="Termine / dichiarazione"
            value={form.dichiarazione || ''}
            onChange={(e) => setForm({ ...form, dichiarazione: e.target.value })}
          />
          <RichTextEditor
            label="Descrizione"
            value={form.descrizione || ''}
            onChange={(value) => setForm({ ...form, descrizione: value })}
          />
        </div>
        <div className="p-4 border-t border-gray-700 flex gap-2">
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
        </div>
      </div>
    </div>
  );
};

const DichiarazioniGlossarioManager = ({ onBack, onLogout }) => {
  const [items, setItems] = useState([]);
  const [editingItem, setEditingItem] = useState(null);
  const [activeTab, setActiveTab] = useState('glossario');
  const [editorStatus, setEditorStatus] = useState({ type: 'success', message: '' });

  const loadItems = async () => {
    try {
      const data = await staffGetDichiarazioni(onLogout);
      setItems(Array.isArray(data) ? data : data.results || []);
    } catch (error) {
      console.error(error);
      setItems([]);
    }
  };

  useEffect(() => { loadItems(); }, []);

  const columns = useMemo(() => [
    { header: 'Nome', render: (x) => <span className="font-bold">{x.nome}</span> },
    { header: 'Tipo', render: (x) => TIPO_OPZIONI.find((opt) => opt.value === x.tipo)?.label || x.tipo, width: 220 },
    { header: 'Termine', render: (x) => x.dichiarazione, width: 260 },
    { header: 'Descrizione', render: (x) => <span className="text-gray-300">{(x.descrizione || '').slice(0, 90)}{(x.descrizione || '').length > 90 ? '...' : ''}</span> },
  ], []);

  const isGlossarioTab = activeTab === 'glossario';
  const filteredItems = useMemo(
    () => items.filter((item) => (isGlossarioTab ? item.tipo === 'GLOS' : item.tipo !== 'GLOS')),
    [items, isGlossarioTab],
  );

  return (
    <div className="h-full p-4 space-y-4">
      <button onClick={onBack} className="px-3 py-2 rounded bg-gray-800 hover:bg-gray-700 text-gray-200 flex items-center gap-2 w-full sm:w-auto justify-center sm:justify-start">
        <ArrowLeft size={16} /> Indietro
      </button>

      <div className="bg-gray-900/70 border border-gray-700 rounded-xl p-2">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          <button
            onClick={() => setActiveTab('glossario')}
            className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors ${isGlossarioTab ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Glossario
          </button>
          <button
            onClick={() => setActiveTab('dichiarazioni')}
            className={`px-3 py-2 rounded-lg text-sm font-bold transition-colors ${!isGlossarioTab ? 'bg-indigo-600 text-white' : 'bg-gray-800 text-gray-300 hover:bg-gray-700'}`}
          >
            Dichiarazioni
          </button>
        </div>
      </div>

      <div className="h-[calc(100%-122px)]">
        <MasterGenericList
          title={isGlossarioTab ? 'Glossario' : 'Dichiarazioni'}
          items={filteredItems}
          columns={columns}
          onAdd={() => setEditingItem({ nome: '', tipo: isGlossarioTab ? 'GLOS' : TIPO_DICHIARAZIONI[0].value, dichiarazione: '', descrizione: '' })}
          onEdit={(item) => setEditingItem(item)}
          onDelete={async (id) => {
            await staffDeleteDichiarazione(id, onLogout);
            await loadItems();
          }}
          addLabel="Nuova Voce"
          filterConfig={isGlossarioTab ? [] : [{
            key: 'tipo',
            label: 'Tipo',
            options: TIPO_DICHIARAZIONI.map((opt) => ({ id: opt.value, label: opt.label })),
          }]}
          emptyMessage="Nessuna voce presente."
        />
      </div>

      <DichiarazioneFormModal
        isOpen={!!editingItem}
        value={editingItem}
        isGlossario={isGlossarioTab}
        onClose={() => setEditingItem(null)}
        statusMessage={editorStatus.message}
        statusType={editorStatus.type}
        onSave={async (form, mode = 'save_close') => {
          if (!form.nome?.trim()) {
            setEditorStatus({ type: 'warning', message: 'Il nome e obbligatorio.' });
            return;
          }
          if (!form.dichiarazione?.trim()) {
            setEditorStatus({ type: 'warning', message: 'Il termine/dichiarazione e obbligatorio.' });
            return;
          }
          if (!form.descrizione?.trim()) {
            setEditorStatus({ type: 'warning', message: 'La descrizione e obbligatoria.' });
            return;
          }
          const payload = {
            nome: form.nome.trim(),
            tipo: isGlossarioTab ? 'GLOS' : (form.tipo || TIPO_DICHIARAZIONI[0].value),
            dichiarazione: form.dichiarazione.trim(),
            descrizione: form.descrizione.trim(),
          };
          const isSaveAsNew = mode === 'save_as_new';
          const isExisting = !!form.id && !isSaveAsNew;
          const saved = isExisting
            ? await staffUpdateDichiarazione(form.id, payload, onLogout)
            : await staffCreateDichiarazione(payload, onLogout);
          const recordName = saved?.nome || payload.nome || 'Record';
          if (mode === 'save_as_new') setEditorStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
          if (mode === 'save_continue') setEditorStatus({ type: 'success', message: `"${recordName}" salvato.` });
          if (mode === 'save_new_blank') setEditorStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
          if (mode === 'save_close') {
            setEditingItem(null);
            setEditorStatus({ type: 'success', message: '' });
          } else if (mode === 'save_new_blank') {
            setEditingItem({ ...EMPTY_FORM, tipo: isGlossarioTab ? 'GLOS' : TIPO_DICHIARAZIONI[0].value });
          } else if (saved?.id) {
            setEditingItem(saved);
          }
          await loadItems();
        }}
      />
    </div>
  );
};

export default memo(DichiarazioniGlossarioManager);
