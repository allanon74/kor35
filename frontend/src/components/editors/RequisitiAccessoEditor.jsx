import React from 'react';
import { Plus, Trash2 } from 'lucide-react';
import FilterableCombobox from './FilterableCombobox';
import {
  ItalianDateTimeInput,
  ItalianTimeInput,
} from '../ItalianDateTimeInputs';

const TIPO_REQUISITO_OPTS = [
  { id: 'statistica', label: 'Statistica (sigla)' },
  { id: 'abilita', label: 'Abilità' },
  { id: 'punteggio', label: 'Aura / punteggio' },
  { id: 'korp', label: 'KORP' },
  { id: 'carriera', label: 'Carriera' },
  { id: 'carica', label: 'Carica' },
];

const GIORNI_SETTIMANA = [
  { v: 0, l: 'Lun' },
  { v: 1, l: 'Mar' },
  { v: 2, l: 'Mer' },
  { v: 3, l: 'Gio' },
  { v: 4, l: 'Ven' },
  { v: 5, l: 'Sab' },
  { v: 6, l: 'Dom' },
];

const emptyRequisito = () => ({ tipo: 'statistica', sigla: '', min: 1 });

const statisticaOptions = (lookup) =>
  (lookup.statistiche || []).map((s) => ({
    value: (s.sigla || '').toUpperCase(),
    label: s.sigla ? `${s.sigla} — ${s.nome || s.sigla}` : s.nome,
    searchText: `${s.sigla} ${s.nome}`,
  })).filter((o) => o.value);

const auraOptions = (lookup) =>
  (lookup.auras || []).map((a) => ({
    value: a.nome,
    label: a.sigla ? `${a.nome} (${a.sigla})` : a.nome,
    searchText: `${a.nome} ${a.sigla || ''}`,
  })).filter((o) => o.value);

const entityOptions = (list) =>
  (list || []).map((x) => ({
    value: x.id,
    label: x.nome || String(x.id),
    searchText: x.nome,
  }));

const RequisitiListaEditor = ({ requisiti, onChange, lookup = {}, lookupLoading = false }) => {
  const list = Array.isArray(requisiti) ? requisiti : [];

  const updateAt = (idx, patch) => {
    const next = list.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    onChange(next);
  };

  const removeAt = (idx) => onChange(list.filter((_, i) => i !== idx));

  const add = () => onChange([...list, emptyRequisito()]);

  return (
    <div className="space-y-2">
      {list.map((req, idx) => {
        const tipo = req.tipo || 'statistica';
        return (
          <div key={idx} className="flex flex-wrap gap-1 items-center bg-gray-900/60 p-2 rounded border border-gray-700">
            <select
              className="bg-gray-800 border border-gray-600 rounded px-1 py-0.5 text-xs"
              value={tipo}
              onChange={(e) => updateAt(idx, { tipo: e.target.value })}
            >
              {TIPO_REQUISITO_OPTS.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
            {tipo === 'statistica' && (
              <>
                <FilterableCombobox
                  options={statisticaOptions(lookup)}
                  value={req.sigla || ''}
                  onChange={(sigla) => updateAt(idx, { sigla: String(sigla || '').toUpperCase() })}
                  placeholder={lookupLoading ? 'Caricamento…' : 'Sigla statistica'}
                  allowCustom
                  normalizeCustom={(v) => v.toUpperCase()}
                  disabled={lookupLoading}
                  className="min-w-[140px]"
                />
                <span className="text-gray-500 text-xs">≥</span>
                <input
                  type="number"
                  className="w-12 bg-gray-800 border border-gray-600 rounded px-1 text-xs"
                  value={req.min ?? 1}
                  onChange={(e) => updateAt(idx, { min: Number(e.target.value) })}
                />
              </>
            )}
            {tipo === 'punteggio' && (
              <>
                <FilterableCombobox
                  options={auraOptions(lookup)}
                  value={req.nome || ''}
                  onChange={(nome) => updateAt(idx, { nome: String(nome || '') })}
                  placeholder={lookupLoading ? 'Caricamento…' : 'Aura / punteggio'}
                  disabled={lookupLoading}
                />
                <span className="text-gray-500 text-xs">≥</span>
                <input
                  type="number"
                  className="w-12 bg-gray-800 border border-gray-600 rounded px-1 text-xs"
                  value={req.min ?? 1}
                  onChange={(e) => updateAt(idx, { min: Number(e.target.value) })}
                />
              </>
            )}
            {(tipo === 'abilita' || tipo === 'korp' || tipo === 'carriera' || tipo === 'carica') && (
              <FilterableCombobox
                options={
                  tipo === 'abilita'
                    ? entityOptions(lookup.abilita)
                    : tipo === 'korp'
                      ? entityOptions(lookup.korps)
                      : tipo === 'carica'
                        ? entityOptions(lookup.cariche)
                        : entityOptions(lookup.carriere)
                }
                value={req.id ?? ''}
                onChange={(id) => updateAt(idx, { id: id || null })}
                placeholder={
                  lookupLoading
                    ? 'Caricamento…'
                    : tipo === 'abilita'
                      ? 'Abilità'
                      : tipo === 'korp'
                        ? 'KORP'
                        : tipo === 'carica'
                          ? 'Carica'
                          : 'Carriera'
                }
                disabled={lookupLoading}
              />
            )}
            <button type="button" className="text-red-400 p-1" onClick={() => removeAt(idx)} aria-label="Rimuovi">
              <Trash2 size={14} />
            </button>
          </div>
        );
      })}
      <button
        type="button"
        onClick={add}
        className="text-xs text-amber-400 flex items-center gap-1 hover:text-amber-300"
      >
        <Plus size={14} />
        Aggiungi requisito
      </button>
    </div>
  );
};

const FasciaEditor = ({ fascia, onChange, onRemove }) => {
  const tipo = fascia.tipo || 'ricorrente';
  const giorni = fascia.giorni || [];

  const toggleGiorno = (v) => {
    const set = new Set(giorni);
    if (set.has(v)) set.delete(v);
    else set.add(v);
    onChange({ ...fascia, giorni: [...set].sort() });
  };

  return (
    <div className="bg-gray-900/60 border border-gray-700 rounded p-2 space-y-2 text-xs">
      <div className="flex justify-between items-center">
        <select
          className="bg-gray-800 border border-gray-600 rounded px-1"
          value={tipo}
          onChange={(e) => onChange({ ...fascia, tipo: e.target.value })}
        >
          <option value="ricorrente">Ricorrente (settimanale)</option>
          <option value="episodica">Episodica (date evento)</option>
        </select>
        <button type="button" className="text-red-400" onClick={onRemove}>
          <Trash2 size={14} />
        </button>
      </div>
      {tipo === 'ricorrente' ? (
        <>
          <div className="flex flex-wrap gap-1">
            {GIORNI_SETTIMANA.map((g) => (
              <button
                key={g.v}
                type="button"
                onClick={() => toggleGiorno(g.v)}
                className={`px-1.5 py-0.5 rounded ${
                  giorni.includes(g.v) ? 'bg-amber-700 text-white' : 'bg-gray-800 text-gray-400'
                }`}
              >
                {g.l}
              </button>
            ))}
          </div>
          <div className="flex gap-2">
            <label className="flex-1">
              Da
              <ItalianTimeInput
                className="w-full mt-0.5 bg-gray-800 border border-gray-600 rounded px-1"
                value={fascia.ora_inizio || '09:00'}
                onChange={(v) => onChange({ ...fascia, ora_inizio: v || '09:00' })}
              />
            </label>
            <label className="flex-1">
              A
              <ItalianTimeInput
                className="w-full mt-0.5 bg-gray-800 border border-gray-600 rounded px-1"
                value={fascia.ora_fine || '18:00'}
                onChange={(v) => onChange({ ...fascia, ora_fine: v || '18:00' })}
              />
            </label>
          </div>
        </>
      ) : (
        <div className="flex flex-col gap-2">
          <label>
            Inizio
            <ItalianDateTimeInput
              className="w-full mt-0.5 bg-gray-800 border border-gray-600 rounded px-1"
              value={fascia.inizio_local || ''}
              onChange={(v) => onChange({ ...fascia, inizio_local: v })}
            />
          </label>
          <label>
            Fine
            <ItalianDateTimeInput
              className="w-full mt-0.5 bg-gray-800 border border-gray-600 rounded px-1"
              value={fascia.fine_local || ''}
              onChange={(v) => onChange({ ...fascia, fine_local: v })}
            />
          </label>
        </div>
      )}
    </div>
  );
};

const toIsoFromLocal = (local) => {
  if (!local) return '';
  const d = new Date(local);
  if (Number.isNaN(d.getTime())) return '';
  return d.toISOString();
};

const fromIsoToLocal = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

export const RegoleAperturaEditor = ({ value, onChange, lookup }) => {
  const regole = value && typeof value === 'object' ? value : { modalita: 'sempre_aperto' };
  const modalita = regole.modalita || 'sempre_aperto';
  const fasce = (regole.fasce || []).map((f) => ({
    ...f,
    inizio_local: f.inizio_local ?? fromIsoToLocal(f.inizio),
    fine_local: f.fine_local ?? fromIsoToLocal(f.fine),
  }));

  const setModalita = (m) => onChange({ ...regole, modalita: m });

  const setFasce = (nextUi) => {
    const serialized = nextUi.map(({ inizio_local, fine_local, ...rest }) => {
      if ((rest.tipo || 'ricorrente') === 'episodica') {
        return {
          ...rest,
          inizio: toIsoFromLocal(inizio_local),
          fine: toIsoFromLocal(fine_local),
        };
      }
      const { inizio_local: _a, fine_local: _b, ...clean } = rest;
      return clean;
    });
    onChange({ ...regole, fasce: serialized });
  };

  return (
    <div className="space-y-2 text-sm">
      <label className="block text-gray-400 text-xs font-semibold uppercase">Apertura (negozi QR)</label>
      <select
        className="w-full bg-gray-900 border border-gray-600 rounded p-2"
        value={modalita}
        onChange={(e) => setModalita(e.target.value)}
      >
        <option value="sempre_aperto">Sempre aperto</option>
        <option value="fasce_orarie">Solo in fasce orarie</option>
      </select>
      {modalita === 'fasce_orarie' && (
        <div className="space-y-2">
          {fasce.map((f, idx) => (
            <FasciaEditor
              key={idx}
              fascia={f}
              onChange={(patch) => {
                const next = [...fasce];
                next[idx] = patch;
                setFasce(next);
              }}
              onRemove={() => setFasce(fasce.filter((_, i) => i !== idx))}
            />
          ))}
          <button
            type="button"
            className="text-xs text-amber-400 flex items-center gap-1"
            onClick={() =>
              setFasce([
                ...fasce,
                { tipo: 'ricorrente', giorni: [5, 6], ora_inizio: '10:00', ora_fine: '22:00' },
              ])
            }
          >
            <Plus size={14} />
            Aggiungi fascia
          </button>
        </div>
      )}
      <label className="block text-gray-500 text-xs mt-2">Requisiti extra (opzionali, anche con sempre aperto)</label>
      <RequisitiListaEditor
        requisiti={regole.requisiti_extra || []}
        onChange={(requisiti_extra) => onChange({ ...regole, requisiti_extra })}
        lookup={lookup}
      />
    </div>
  );
};

export const RegoleGruppoListaEditor = ({ gruppi, onChange, lookup, lookupLoading, renderExtra, addLabel = 'Aggiungi regola' }) => {
  const list = Array.isArray(gruppi) ? gruppi : [];

  const updateAt = (idx, patch) => {
    onChange(list.map((g, i) => (i === idx ? { ...g, ...patch } : g)));
  };

  const removeAt = (idx) => onChange(list.filter((_, i) => i !== idx));

  const add = () =>
    onChange([
      ...list,
      { operator: 'AND', requisiti: [{ tipo: 'statistica', sigla: '', min: 1 }] },
    ]);

  return (
    <div className="space-y-2">
      {list.map((gruppo, idx) => (
        <div key={idx} className="bg-gray-950/80 border border-gray-700 rounded p-2 space-y-2">
          <div className="flex flex-wrap gap-2 items-center justify-between">
            <select
              className="bg-gray-800 border border-gray-600 rounded px-1 py-0.5 text-xs"
              value={gruppo.operator || 'AND'}
              onChange={(e) => updateAt(idx, { operator: e.target.value })}
            >
              <option value="AND">Tutti (AND)</option>
              <option value="OR">Almeno uno (OR)</option>
            </select>
            {renderExtra ? renderExtra(gruppo, (patch) => updateAt(idx, patch)) : null}
            <button type="button" className="text-red-400 p-1 ml-auto" onClick={() => removeAt(idx)} aria-label="Rimuovi">
              <Trash2 size={14} />
            </button>
          </div>
          <RequisitiListaEditor
            requisiti={gruppo.requisiti || []}
            onChange={(requisiti) => updateAt(idx, { requisiti })}
            lookup={lookup}
            lookupLoading={lookupLoading}
          />
        </div>
      ))}
      <button
        type="button"
        onClick={add}
        className="text-xs text-amber-400 flex items-center gap-1 hover:text-amber-300"
      >
        <Plus size={14} />
        {addLabel}
      </button>
    </div>
  );
};

export const RegoleVisibilitaEditor = ({ value, onChange, lookup }) => {
  const regole = value && typeof value === 'object' ? value : { operator: 'OR', requisiti: [] };
  return (
    <div className="space-y-2 text-sm">
      <label className="block text-gray-400 text-xs font-semibold uppercase">
        Visibilità tab (negozi corporativi)
      </label>
      <select
        className="w-full bg-gray-900 border border-gray-600 rounded p-2"
        value={regole.operator || 'OR'}
        onChange={(e) => onChange({ ...regole, operator: e.target.value })}
      >
        <option value="OR">Basta uno dei requisiti (OR)</option>
        <option value="AND">Tutti i requisiti (AND)</option>
      </select>
      <RequisitiListaEditor
        requisiti={regole.requisiti || []}
        onChange={(requisiti) => onChange({ ...regole, requisiti })}
        lookup={lookup}
      />
    </div>
  );
};

export default RequisitiListaEditor;
