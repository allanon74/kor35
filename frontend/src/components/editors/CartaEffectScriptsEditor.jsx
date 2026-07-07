import React, { useCallback, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import EffectScriptWizard from './EffectScriptWizard';

const TRIGGER_OPTIONS = [
  { value: 'on_play', label: 'Ingresso in gioco (on_play)' },
  { value: 'on_exhaust', label: 'Alla morte (on_exhaust)' },
  { value: 'manual', label: 'Attivabile (manual)' },
  { value: 'on_turn_start', label: 'Continuo — inizio turno' },
  { value: 'on_turn_end', label: 'Continuo — fine turno' },
  { value: 'on_attack', label: 'Dopo attacco (on_attack)' },
];

const emptyEntry = () => ({
  codice: '',
  nome: '',
  scriptText: '',
});

function parseScriptText(text) {
  if (!text || !text.trim()) return null;
  return JSON.parse(text);
}

export default function CartaEffectScriptsEditor({ entries = [], onChange, onMessage, disabled = false }) {
  const [activeIdx, setActiveIdx] = useState(null);
  const [scriptText, setScriptText] = useState('');

  const syncEntryScript = useCallback((idx, text) => {
    onChange(
      entries.map((e, i) => (i === idx ? { ...e, scriptText: text } : e)),
    );
  }, [entries, onChange]);

  const openEditor = (idx) => {
    setActiveIdx(idx);
    setScriptText(entries[idx]?.scriptText || '');
  };

  const addEntry = () => {
    const next = [...entries, emptyEntry()];
    onChange(next);
    openEditor(next.length - 1);
  };

  const removeEntry = (idx) => {
    onChange(entries.filter((_, i) => i !== idx));
    if (activeIdx === idx) {
      setActiveIdx(null);
      setScriptText('');
    }
  };

  const updateMeta = (idx, field, value) => {
    onChange(entries.map((e, i) => (i === idx ? { ...e, [field]: value } : e)));
  };

  return (
    <div className="rounded border border-violet-900/60 bg-violet-950/20 p-2">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-xs font-bold text-violet-200">
          Effetti carta (EffectScript — senza keyword nel testo)
        </p>
        <button
          type="button"
          disabled={disabled}
          className="flex items-center gap-1 rounded bg-violet-800 px-2 py-0.5 text-[10px]"
          onClick={addEntry}
        >
          <Plus size={12} /> Aggiungi
        </button>
      </div>
      <p className="mb-2 text-[10px] text-gray-500">
        Ingresso, morte, attivabile e continui (turno). I parametri [X] usano i default nello script.
      </p>
      {entries.length === 0 && (
        <p className="text-[10px] text-gray-600">Nessun effetto sulla carta.</p>
      )}
      <ul className="space-y-1">
        {entries.map((e, idx) => {
          let eventLabel = '';
          try {
            const s = e.scriptText?.trim() ? parseScriptText(e.scriptText) : null;
            eventLabel = s?.trigger?.event || '';
          } catch {
            eventLabel = 'JSON errato';
          }
          return (
            <li
              key={`cfx-${idx}`}
              className={`flex flex-wrap items-center gap-1 rounded border px-2 py-1 text-xs ${
                activeIdx === idx ? 'border-violet-500 bg-gray-900' : 'border-gray-700'
              }`}
            >
              <button type="button" disabled={disabled} className="font-bold text-violet-200 disabled:opacity-60" onClick={() => openEditor(idx)}>
                {e.nome || e.codice || `Effetto ${idx + 1}`}
              </button>
              {eventLabel && (
                <span className="rounded bg-gray-800 px-1 text-[9px] text-gray-400">{eventLabel}</span>
              )}
              <button
                type="button"
                disabled={disabled}
                className="ml-auto text-red-400 disabled:opacity-50"
                onClick={() => removeEntry(idx)}
                aria-label="Rimuovi"
              >
                <Trash2 size={12} />
              </button>
            </li>
          );
        })}
      </ul>

      {activeIdx != null && entries[activeIdx] && (
        <div className="mt-3 space-y-2 border-t border-gray-800 pt-2">
          <p className="text-[10px] font-bold text-gray-400">
            Modifica effetto {activeIdx + 1}
          </p>
          <div className="grid grid-cols-2 gap-2">
            <input
              disabled={disabled}
              className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-xs"
              placeholder="Codice (es. RITO_KAEL)"
              value={entries[activeIdx].codice || ''}
              onChange={(ev) => updateMeta(activeIdx, 'codice', ev.target.value)}
            />
            <input
              disabled={disabled}
              className="rounded border border-gray-600 bg-gray-900 px-2 py-1 text-xs"
              placeholder="Nome UI (es. Rito delle ombre)"
              value={entries[activeIdx].nome || ''}
              onChange={(ev) => updateMeta(activeIdx, 'nome', ev.target.value)}
            />
          </div>
          <EffectScriptWizard
            mode="carta"
            effectScriptText={scriptText}
            setEffectScriptText={(t) => {
              setScriptText(t);
              syncEntryScript(activeIdx, t);
            }}
            triggerOptions={TRIGGER_OPTIONS}
            onMessage={onMessage}
            disabled={disabled}
          />
          <textarea
            disabled={disabled}
            className="h-32 w-full rounded border border-gray-700 bg-gray-950 p-2 font-mono text-[10px]"
            value={scriptText}
            onChange={(ev) => {
              setScriptText(ev.target.value);
              syncEntryScript(activeIdx, ev.target.value);
            }}
            placeholder='{"version":1,"trigger":{"event":"on_play"},"steps":[...]}'
          />
        </div>
      )}
    </div>
  );
}

export function effectScriptsFromApi(apiList) {
  if (!Array.isArray(apiList)) return [];
  return apiList.map((row) => ({
    codice: row.codice || '',
    nome: row.nome || '',
    scriptText: row.script && Object.keys(row.script).length
      ? JSON.stringify(row.script, null, 2)
      : '',
  }));
}

export function effectScriptsToApi(editorEntries) {
  const out = [];
  for (let i = 0; i < (editorEntries || []).length; i += 1) {
    const e = editorEntries[i];
    if (!e.scriptText?.trim()) continue;
    const script = JSON.parse(e.scriptText);
    out.push({
      codice: (e.codice || '').trim().toUpperCase(),
      nome: (e.nome || '').trim(),
      script,
    });
  }
  return out;
}
