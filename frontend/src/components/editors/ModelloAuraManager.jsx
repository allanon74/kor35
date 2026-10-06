import React, { useEffect, useMemo, useState } from 'react';
import EditorSaveActions from './EditorSaveActions';
import SearchableSelect from './SearchableSelect';
import StaffCatalogListEditor from '../../staff/StaffCatalogListEditor';
import {
  ChipToggle,
  FieldLabel,
  Flag,
  Section,
  TextInput,
  fkId,
  labeledPunteggi,
} from '../../staff/staffCatalogForm';
import {
  staffGetModelliAura,
  staffCreateModelloAura,
  staffUpdateModelloAura,
  staffDeleteModelloAura,
  staffGetAure,
  staffGetMattoni,
  staffGetPunteggiResidui,
  staffGetCaratteristiche,
} from '../../api';

const EMPTY_REQ = () => ({ requisito: null, valore: 1 });

const EMPTY_FORM = {
  nome: '',
  aura: null,
  descrizione: '',
  mattoni_proibiti: [],
  mattoni_obbligatori: [],
  usa_doppia_formula: false,
  elemento_secondario: null,
  usa_condizione_doppia: false,
  requisiti_doppia: [],
  usa_formula_per_mattone: false,
  usa_condizione_mattone: false,
  requisiti_mattone: [],
  usa_formula_per_caratteristica: false,
  usa_condizione_caratt: false,
  requisiti_caratt: [],
};

function ReqRows({ rows, options, onChange }) {
  return (
    <div className="space-y-2">
      {(rows || []).map((row, i) => (
        <div key={i} className="grid grid-cols-1 sm:grid-cols-[1fr_5rem_2.75rem] gap-2 min-w-0">
          <SearchableSelect
            options={options}
            value={fkId(row.requisito)}
            onChange={(v) => {
              const n = [...rows];
              n[i] = { ...n[i], requisito: v };
              onChange(n);
            }}
            placeholder="Requisito"
          />
          <TextInput type="number" value={row.valore ?? 1} onChange={(v) => {
            const n = [...rows];
            n[i] = { ...n[i], valore: parseInt(v || '1', 10) };
            onChange(n);
          }} />
          <button type="button" className="min-h-11 text-red-400" onClick={() => onChange(rows.filter((_, idx) => idx !== i))}>✕</button>
        </div>
      ))}
      <button type="button" className="min-h-11 px-3 rounded bg-indigo-600 text-sm" onClick={() => onChange([...(rows || []), EMPTY_REQ()])}>+ Requisito</button>
    </div>
  );
}

const FormPanel = ({ value, onClose, onSave, lookups, statusMessage = '', statusType = 'success' }) => {
  const [form, setForm] = useState(value || EMPTY_FORM);
  useEffect(() => {
    setForm({
      ...EMPTY_FORM,
      ...(value || {}),
      mattoni_proibiti: (value?.mattoni_proibiti || []).map(fkId),
      mattoni_obbligatori: (value?.mattoni_obbligatori || []).map(fkId),
    });
  }, [value]);
  const set = (patch) => setForm((prev) => ({ ...prev, ...patch }));
  const toggleList = (key, id) => {
    const cur = form[key] || [];
    const has = cur.some((x) => String(x) === String(id));
    set({ [key]: has ? cur.filter((x) => String(x) !== String(id)) : [...cur, id] });
  };
  const reqOptions = labeledPunteggi([
    ...(lookups?.caratteristiche || []),
    ...(lookups?.residui || []),
  ]);
  const elementi = (lookups?.residui || []).filter((p) => p.tipo === 'EL');

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
          <FieldLabel>Nome modello</FieldLabel>
          <TextInput value={form.nome} onChange={(v) => set({ nome: v })} />
        </div>
        <div className="sm:col-span-2">
          <FieldLabel>Aura</FieldLabel>
          <SearchableSelect options={labeledPunteggi(lookups?.aure)} value={fkId(form.aura)} onChange={(v) => set({ aura: v })} placeholder="Aura" />
        </div>
      </div>
      <textarea className="w-full min-h-[80px] bg-gray-800 border border-gray-700 rounded p-2 text-white" placeholder="Descrizione breve" value={form.descrizione || ''} onChange={(e) => set({ descrizione: e.target.value })} />
      <Section title="Mattoni proibiti">
        <ChipToggle items={lookups?.mattoni} selected={form.mattoni_proibiti} onToggle={(id) => toggleList('mattoni_proibiti', id)} labelOf={(m) => m.sigla ? `${m.sigla} — ${m.nome}` : m.nome} />
      </Section>
      <Section title="Mattoni obbligatori">
        <ChipToggle items={lookups?.mattoni} selected={form.mattoni_obbligatori} onToggle={(id) => toggleList('mattoni_obbligatori', id)} labelOf={(m) => m.sigla ? `${m.sigla} — ${m.nome}` : m.nome} />
      </Section>
      <Section title="Doppia formula">
        <Flag label="Abilita doppia formula" checked={form.usa_doppia_formula} onChange={(v) => set({ usa_doppia_formula: v })} />
        <FieldLabel>Elemento secondario</FieldLabel>
        <SearchableSelect options={labeledPunteggi(elementi)} value={fkId(form.elemento_secondario)} onChange={(v) => set({ elemento_secondario: v })} placeholder="- Nessuno -" />
        <Flag label="Richiede condizione" checked={form.usa_condizione_doppia} onChange={(v) => set({ usa_condizione_doppia: v })} />
        {form.usa_condizione_doppia ? <ReqRows rows={form.requisiti_doppia} options={reqOptions} onChange={(n) => set({ requisiti_doppia: n })} /> : null}
      </Section>
      <Section title="Formula per mattone">
        <Flag label="Abilita formula per mattone" checked={form.usa_formula_per_mattone} onChange={(v) => set({ usa_formula_per_mattone: v })} />
        <Flag label="Richiede condizione" checked={form.usa_condizione_mattone} onChange={(v) => set({ usa_condizione_mattone: v })} />
        {form.usa_condizione_mattone ? <ReqRows rows={form.requisiti_mattone} options={reqOptions} onChange={(n) => set({ requisiti_mattone: n })} /> : null}
      </Section>
      <Section title="Formula per caratteristica">
        <Flag label="Abilita formula per caratteristica" checked={form.usa_formula_per_caratteristica} onChange={(v) => set({ usa_formula_per_caratteristica: v })} />
        <Flag label="Richiede condizione" checked={form.usa_condizione_caratt} onChange={(v) => set({ usa_condizione_caratt: v })} />
        {form.usa_condizione_caratt ? <ReqRows rows={form.requisiti_caratt} options={reqOptions} onChange={(n) => set({ requisiti_caratt: n })} /> : null}
      </Section>
    </div>
  );
};

export default function ModelloAuraManager({ onLogout }) {
  const columns = useMemo(() => [
    { key: 'nome', header: 'Nome', getSortValue: (x) => x.nome || '', render: (x) => <span className="font-bold break-words">{x.nome}</span> },
    { key: 'aura', header: 'Aura', getSortValue: (x) => x.aura_nome || '', render: (x) => x.aura_nome || '—' },
  ], []);

  return (
    <StaffCatalogListEditor
      title="Modelli di aura"
      hint="Limitazioni mattoni e formule (doppia, per mattone, per caratteristica)."
      persistKey="staff-modelli-aura"
      addLabel="Nuovo modello"
      emptyMessage="Nessun modello di aura."
      columns={columns}
      emptyForm={EMPTY_FORM}
      modalSize="xl"
      FormPanel={FormPanel}
      isSistema={() => false}
      loadItems={async () => {
        const [rows, aure, mattoni, residui, caratteristiche] = await Promise.all([
          staffGetModelliAura(onLogout),
          staffGetAure(onLogout),
          staffGetMattoni(onLogout),
          staffGetPunteggiResidui(onLogout),
          staffGetCaratteristiche(onLogout),
        ]);
        return {
          items: Array.isArray(rows) ? rows : rows?.results || [],
          lookups: {
            aure: Array.isArray(aure) ? aure : aure?.results || [],
            mattoni: Array.isArray(mattoni) ? mattoni : mattoni?.results || [],
            residui: Array.isArray(residui) ? residui : residui?.results || [],
            caratteristiche: Array.isArray(caratteristiche) ? caratteristiche : caratteristiche?.results || [],
          },
        };
      }}
      saveItem={async (form, mode, setStatus) => {
        if (!form.nome?.trim() || !fkId(form.aura)) {
          setStatus({ type: 'warning', message: 'Nome e aura sono obbligatori.' });
          return false;
        }
        const mapReq = (rows) => (rows || [])
          .filter((r) => fkId(r.requisito))
          .map((r) => ({ requisito: fkId(r.requisito), valore: Number(r.valore || 1) }));
        const payload = {
          nome: form.nome.trim(),
          aura: fkId(form.aura),
          descrizione: form.descrizione || '',
          mattoni_proibiti: form.mattoni_proibiti || [],
          mattoni_obbligatori: form.mattoni_obbligatori || [],
          usa_doppia_formula: !!form.usa_doppia_formula,
          elemento_secondario: fkId(form.elemento_secondario),
          usa_condizione_doppia: !!form.usa_condizione_doppia,
          requisiti_doppia: mapReq(form.requisiti_doppia),
          usa_formula_per_mattone: !!form.usa_formula_per_mattone,
          usa_condizione_mattone: !!form.usa_condizione_mattone,
          requisiti_mattone: mapReq(form.requisiti_mattone),
          usa_formula_per_caratteristica: !!form.usa_formula_per_caratteristica,
          usa_condizione_caratt: !!form.usa_condizione_caratt,
          requisiti_caratt: mapReq(form.requisiti_caratt),
        };
        const isExisting = !!form.id && mode !== 'save_as_new';
        return isExisting
          ? staffUpdateModelloAura(form.id, payload, onLogout)
          : staffCreateModelloAura(payload, onLogout);
      }}
      deleteItem={(id) => staffDeleteModelloAura(id, onLogout)}
    />
  );
}
