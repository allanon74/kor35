import React, { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2, ChevronDown, ChevronUp } from 'lucide-react';
import {
  emptyVincolo,
  parseRequisitiJson,
  stringifyRequisitiJson,
  sumRicaricaConfigurata,
  labelMattone,
} from '../../staff/requisitiComponentiJson';

const TIPO_OPTS = [
  { value: 'specifico', label: 'Specifico (mattone fisso)' },
  { value: 'scelta', label: 'A scelta (uno tra più mattoni)' },
];

function VincoloEditor({
  vincolo,
  index,
  catalogo,
  mode,
  unitaLabel,
  onChange,
  onRemove,
  onMoveUp,
  onMoveDown,
  canMoveUp,
  canMoveDown,
}) {
  const tipo = vincolo.tipo || 'specifico';
  const withRicarica = mode === 'ricarica';

  const toggleMattoneScelta = (id) => {
    const ids = new Set(vincolo.mattone_ids || []);
    if (ids.has(id)) ids.delete(id);
    else ids.add(id);
    onChange({ ...vincolo, mattone_ids: [...ids] });
  };

  return (
    <div className="rounded-lg border border-gray-700 bg-gray-900/70 p-3 space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <span className="text-xs font-bold uppercase text-indigo-300">Vincolo {index + 1}</span>
        <div className="flex items-center gap-1">
          <button type="button" className="p-1 text-gray-500 hover:text-white disabled:opacity-30" disabled={!canMoveUp} onClick={onMoveUp} aria-label="Su">
            <ChevronUp size={16} />
          </button>
          <button type="button" className="p-1 text-gray-500 hover:text-white disabled:opacity-30" disabled={!canMoveDown} onClick={onMoveDown} aria-label="Giù">
            <ChevronDown size={16} />
          </button>
          <button type="button" className="p-1 text-red-400 hover:text-red-300" onClick={onRemove} aria-label="Elimina">
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      <div className="grid sm:grid-cols-3 gap-2">
        <label className="block text-xs">
          <span className="text-gray-500">Tipo</span>
          <select
            className="mt-1 w-full bg-gray-950 border border-gray-600 rounded px-2 py-1.5"
            value={tipo}
            onChange={(e) => {
              const nextTipo = e.target.value;
              onChange({
                ...emptyVincolo(nextTipo, { withRicarica }),
                quantita: vincolo.quantita || 1,
                ricarica: vincolo.ricarica ?? 10,
              });
            }}
          >
            {TIPO_OPTS.map((o) => (
              <option key={o.value} value={o.value}>{o.label}</option>
            ))}
          </select>
        </label>
        <label className="block text-xs">
          <span className="text-gray-500">Quantità</span>
          <input
            type="number"
            min={1}
            className="mt-1 w-full bg-gray-950 border border-gray-600 rounded px-2 py-1.5"
            value={vincolo.quantita ?? 1}
            onChange={(e) => onChange({ ...vincolo, quantita: Math.max(1, Number(e.target.value) || 1) })}
          />
        </label>
        {withRicarica ? (
          <label className="block text-xs">
            <span className="text-gray-500">Ricarica (+{unitaLabel})</span>
            <input
              type="number"
              min={0.1}
              step={0.1}
              className="mt-1 w-full bg-gray-950 border border-gray-600 rounded px-2 py-1.5"
              value={vincolo.ricarica ?? 10}
              onChange={(e) => onChange({ ...vincolo, ricarica: Math.max(0.1, Number(e.target.value) || 0) })}
            />
          </label>
        ) : null}
      </div>

      {tipo === 'specifico' ? (
        <label className="block text-xs">
          <span className="text-gray-500">Mattone componente</span>
          <select
            className="mt-1 w-full bg-gray-950 border border-gray-600 rounded px-2 py-1.5"
            value={vincolo.mattone_id || ''}
            onChange={(e) => onChange({ ...vincolo, mattone_id: e.target.value })}
          >
            <option value="">— seleziona —</option>
            {(catalogo || []).map((m) => (
              <option key={m.id} value={m.id}>
                {labelMattone(catalogo, m.id)}
              </option>
            ))}
          </select>
        </label>
      ) : (
        <div className="text-xs space-y-1">
          <span className="text-gray-500">Opzioni a scelta (seleziona uno o più mattoni)</span>
          <div className="max-h-36 overflow-y-auto border border-gray-700 rounded p-2 space-y-1">
            {(catalogo || []).map((m) => {
              const checked = (vincolo.mattone_ids || []).includes(m.id);
              return (
                <label key={m.id} className="flex items-center gap-2 cursor-pointer hover:bg-gray-800/50 rounded px-1 py-0.5">
                  <input type="checkbox" checked={checked} onChange={() => toggleMattoneScelta(m.id)} />
                  <span>{labelMattone(catalogo, m.id)}</span>
                </label>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default function RequisitiComponentiWizard({
  mode = 'riparazione',
  jsonValue = '[]',
  onJsonChange,
  mattoniCatalogo = [],
  unitaLabel = 'unità',
  disabled = false,
}) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [vincoli, setVincoli] = useState([]);

  useEffect(() => {
    const parsed = parseRequisitiJson(jsonValue, { mode });
    setVincoli(parsed.ok ? parsed.items : []);
  }, [jsonValue, mode]);

  const syncOut = (next) => {
    setVincoli(next);
    onJsonChange(stringifyRequisitiJson(next));
  };

  const parsedPreview = useMemo(() => parseRequisitiJson(vincoli, { mode }), [vincoli, mode]);
  const ricaricaTot = useMemo(() => sumRicaricaConfigurata(vincoli), [vincoli]);

  const addVincolo = () => {
    syncOut([...vincoli, emptyVincolo('specifico', { withRicarica: mode === 'ricarica' })]);
  };

  const updateAt = (idx, next) => {
    const copy = [...vincoli];
    copy[idx] = next;
    syncOut(copy);
  };

  const removeAt = (idx) => {
    syncOut(vincoli.filter((_, i) => i !== idx));
  };

  const moveAt = (idx, dir) => {
    const j = idx + dir;
    if (j < 0 || j >= vincoli.length) return;
    const copy = [...vincoli];
    [copy[idx], copy[j]] = [copy[j], copy[idx]];
    syncOut(copy);
  };

  if (!mattoniCatalogo?.length) {
    return (
      <p className="text-xs text-amber-300/90 border border-amber-800/40 rounded p-2 bg-amber-950/20">
        Catalogo componenti non disponibile. Esegui seed componenti nave e apri la tab Stiva.
      </p>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-xs text-gray-500">
          {mode === 'ricarica'
            ? `Vincoli ricarica (${unitaLabel}). Totale: +${ricaricaTot}`
            : 'Vincoli consumo componenti per riparazione QR.'}
        </p>
        <button
          type="button"
          disabled={disabled}
          className="inline-flex items-center gap-1 px-2 py-1 rounded bg-indigo-900/60 text-indigo-200 text-xs font-bold hover:bg-indigo-800/60 disabled:opacity-50"
          onClick={addVincolo}
        >
          <Plus size={14} /> Aggiungi vincolo
        </button>
      </div>

      {vincoli.length === 0 ? (
        <p className="text-xs text-gray-600 italic">Nessun vincolo configurato.</p>
      ) : (
        <div className="space-y-2">
          {vincoli.map((v, i) => (
            <VincoloEditor
              key={`v-${i}-${v.tipo}`}
              vincolo={v}
              index={i}
              catalogo={mattoniCatalogo}
              mode={mode}
              unitaLabel={unitaLabel}
              onChange={(next) => updateAt(i, next)}
              onRemove={() => removeAt(i)}
              onMoveUp={() => moveAt(i, -1)}
              onMoveDown={() => moveAt(i, 1)}
              canMoveUp={i > 0}
              canMoveDown={i < vincoli.length - 1}
            />
          ))}
        </div>
      )}

      {!parsedPreview.ok ? (
        <p className="text-xs text-red-300">{parsedPreview.error}</p>
      ) : null}

      <button
        type="button"
        className="text-xs text-gray-500 hover:text-gray-300 underline"
        onClick={() => setShowAdvanced((v) => !v)}
      >
        {showAdvanced ? 'Nascondi JSON' : 'Modifica JSON avanzato'}
      </button>

      {showAdvanced ? (
        <textarea
          rows={6}
          disabled={disabled}
          className="w-full bg-gray-950 border border-gray-600 rounded px-2 py-1.5 font-mono text-xs"
          value={jsonValue}
          onChange={(e) => onJsonChange(e.target.value)}
          spellCheck={false}
        />
      ) : null}
    </div>
  );
}
