import React, { memo, useEffect, useMemo, useState } from 'react';
import { StaffToolShell } from '../../staff/StaffToolShell';
import MasterGenericList from './MasterGenericList';
import StaffEditorModal from './StaffEditorModal';
import EditorSaveActions from './EditorSaveActions';
import {
  staffGetStatistiche,
  staffCreateStatistica,
  staffUpdateStatistica,
  staffDeleteStatistica,
} from '../../api';

const EMPTY_FORM = {
  nome: '',
  sigla: '',
  parametro: '',
  descrizione: '',
  ordine: 0,
  colore: '#1976D2',
  formula: false,
  tipo_modificatore: 'ADD',
  is_primaria: false,
  is_costo: false,
  is_tempo: false,
  is_numero: false,
  is_risorsa_pool: false,
  valore_predefinito: 0,
  valore_base_predefinito: 0,
  pool_corrente_default_pieno_se_assente: true,
  auto_recupero_attivo: false,
  auto_recupero_intervallo_secondi: 300,
  auto_recupero_step: 1,
  massimo_pool_sigla: '',
};

function isStatSistema(item) {
  return /^0[A-Z]/i.test(String(item?.sigla || ''));
}

const Flag = ({ label, checked, onChange }) => (
  <label className="flex items-center gap-2 min-h-11 text-sm text-gray-200">
    <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
    {label}
  </label>
);

const StatisticaFormPanel = ({ value, onClose, onSave, statusMessage = '', statusType = 'success' }) => {
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
        Se <span className="font-mono">parametro</span> è vuoto, al salvataggio viene copiata la sigla.
        Senza parametro i bonus delle abilità non si applicano in scheda.
        Produzione oggetti, costi tessitura/infusione e aure infusione stanno sul catalogo{' '}
        <strong className="text-gray-200">Aure</strong>, non qui: i flag costo/tempo/numero
        rendono questa statistica selezionabile in quella maschera.
      </p>
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
          <label className="text-xs text-gray-500 uppercase font-bold">Parametro (formule)</label>
          <input
            className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white font-mono"
            maxLength={10}
            placeholder={form.sigla || 'copia della sigla'}
            value={form.parametro || ''}
            onChange={(e) => set({ parametro: e.target.value })}
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
        <div>
          <label className="text-xs text-gray-500 uppercase font-bold">Valore base predefinito</label>
          <input
            type="number"
            className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.valore_base_predefinito ?? 0}
            onChange={(e) => set({ valore_base_predefinito: parseInt(e.target.value || '0', 10) })}
          />
        </div>
        <div>
          <label className="text-xs text-gray-500 uppercase font-bold">Valore predefinito (modificatore)</label>
          <input
            type="number"
            className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
            value={form.valore_predefinito ?? 0}
            onChange={(e) => set({ valore_predefinito: parseInt(e.target.value || '0', 10) })}
          />
        </div>
      </div>
      <textarea
        className="w-full min-h-[110px] bg-gray-800 border border-gray-700 rounded p-2 text-white"
        placeholder="Descrizione"
        value={form.descrizione || ''}
        onChange={(e) => set({ descrizione: e.target.value })}
      />
      <div>
        <label className="text-xs text-gray-500 uppercase font-bold">Tipo modificatore predefinito</label>
        <select
          className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
          value={form.tipo_modificatore || 'ADD'}
          onChange={(e) => set({ tipo_modificatore: e.target.value })}
        >
          <option value="ADD">Additivo (+N)</option>
          <option value="MOL">Moltiplicativo (xN)</option>
        </select>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <Flag label="Formula" checked={form.formula} onChange={(v) => set({ formula: v })} />
        <Flag label="Primaria (scheda)" checked={form.is_primaria} onChange={(v) => set({ is_primaria: v })} />
        <Flag label="Statistica costo" checked={form.is_costo} onChange={(v) => set({ is_costo: v })} />
        <Flag label="Statistica tempo" checked={form.is_tempo} onChange={(v) => set({ is_tempo: v })} />
        <Flag label="Statistica numero" checked={form.is_numero} onChange={(v) => set({ is_numero: v })} />
        <Flag label="Risorsa a pool" checked={form.is_risorsa_pool} onChange={(v) => set({ is_risorsa_pool: v })} />
      </div>
      {form.is_risorsa_pool && (
        <div className="space-y-2 rounded border border-amber-900/40 p-3">
          <Flag
            label="Pool assente = pieno"
            checked={form.pool_corrente_default_pieno_se_assente}
            onChange={(v) => set({ pool_corrente_default_pieno_se_assente: v })}
          />
          <Flag
            label="Recupero automatico"
            checked={form.auto_recupero_attivo}
            onChange={(v) => set({ auto_recupero_attivo: v })}
          />
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
            <div>
              <label className="text-xs text-gray-500 uppercase font-bold">Intervallo (sec)</label>
              <input
                type="number"
                className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
                value={form.auto_recupero_intervallo_secondi ?? 300}
                onChange={(e) => set({ auto_recupero_intervallo_secondi: parseInt(e.target.value || '0', 10) })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase font-bold">Step recupero</label>
              <input
                type="number"
                className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white"
                value={form.auto_recupero_step ?? 1}
                onChange={(e) => set({ auto_recupero_step: parseInt(e.target.value || '0', 10) })}
              />
            </div>
            <div>
              <label className="text-xs text-gray-500 uppercase font-bold">Max da altra sigla</label>
              <input
                className="w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white font-mono"
                maxLength={10}
                value={form.massimo_pool_sigla || ''}
                onChange={(e) => set({ massimo_pool_sigla: e.target.value })}
              />
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

const StatisticaManager = ({ onLogout }) => {
  const [items, setItems] = useState([]);
  const [editingItem, setEditingItem] = useState(null);
  const [editorStatus, setEditorStatus] = useState({ type: 'success', message: '' });

  const loadItems = async () => {
    try {
      const data = await staffGetStatistiche(onLogout);
      const rows = Array.isArray(data) ? data : data.results || [];
      setItems(rows);
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
            {isStatSistema(x) ? (
              <span className="ml-2 text-[10px] uppercase text-amber-400">sistema</span>
            ) : null}
          </span>
        ),
      },
      {
        key: 'parametro',
        header: 'Parametro',
        width: 110,
        getSortValue: (x) => x.parametro || '',
        render: (x) =>
          x.parametro ? (
            <span className="font-mono text-gray-300">{x.parametro}</span>
          ) : (
            <span className="text-red-400 text-xs font-bold">manca</span>
          ),
      },
      {
        key: 'base',
        header: 'Base',
        width: 70,
        getSortValue: (x) => x.valore_base_predefinito ?? 0,
        render: (x) => x.valore_base_predefinito ?? 0,
      },
      {
        key: 'flags',
        header: 'Flag',
        getSortValue: (x) => (x.is_primaria ? '1' : '0'),
        render: (x) => (
          <span className="text-xs text-gray-400">
            {[
              x.formula && 'formula',
              x.is_primaria && 'primaria',
              x.is_risorsa_pool && 'pool',
              x.is_costo && 'costo',
            ]
              .filter(Boolean)
              .join(', ') || '—'}
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
      parametro: (form.parametro || '').trim() || form.sigla.trim(),
      descrizione: form.descrizione || '',
      ordine: Number(form.ordine || 0),
      colore: form.colore || '#1976D2',
      formula: !!form.formula,
      tipo_modificatore: form.tipo_modificatore === 'MOL' ? 'MOL' : 'ADD',
      is_primaria: !!form.is_primaria,
      is_costo: !!form.is_costo,
      is_tempo: !!form.is_tempo,
      is_numero: !!form.is_numero,
      is_risorsa_pool: !!form.is_risorsa_pool,
      valore_predefinito: Number(form.valore_predefinito || 0),
      valore_base_predefinito: Number(form.valore_base_predefinito || 0),
      pool_corrente_default_pieno_se_assente: !!form.pool_corrente_default_pieno_se_assente,
      auto_recupero_attivo: !!form.auto_recupero_attivo,
      auto_recupero_intervallo_secondi: Number(form.auto_recupero_intervallo_secondi || 300),
      auto_recupero_step: Number(form.auto_recupero_step || 1),
      massimo_pool_sigla: (form.massimo_pool_sigla || '').trim() || null,
    };
    const isSaveAsNew = mode === 'save_as_new';
    const isExisting = !!form.id && !isSaveAsNew;
    const saved = isExisting
      ? await staffUpdateStatistica(form.id, payload, onLogout)
      : await staffCreateStatistica(payload, onLogout);
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
        Catalogo statistiche (P01, COG, pool, …). Le sigle 0K* sono componenti nave: si possono
        modificare, non cancellare.
      </p>
      <MasterGenericList
        title="Statistiche"
        items={items}
        columns={columns}
        persistKey="staff-statistiche"
        onAdd={() => setEditingItem({ ...EMPTY_FORM })}
        onEdit={(item) => setEditingItem(item)}
        onDelete={async (id) => {
          const item = items.find((x) => x.id === id);
          if (isStatSistema(item)) {
            setEditorStatus({
              type: 'warning',
              message: `«${item.sigla}» è una statistica di sistema (componenti nave) e non si elimina da qui.`,
            });
            return;
          }
          await staffDeleteStatistica(id, onLogout);
          await loadItems();
        }}
        addLabel="Nuova statistica"
        emptyMessage="Nessuna statistica in catalogo."
      />
      {editingItem && (
        <StaffEditorModal
          title={editingItem.id ? 'Modifica statistica' : 'Nuova statistica'}
          size="lg"
          showSave={false}
          onClose={() => {
            setEditingItem(null);
            setEditorStatus({ type: 'success', message: '' });
          }}
        >
          <StatisticaFormPanel
            value={editingItem}
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

export default memo(StatisticaManager);
