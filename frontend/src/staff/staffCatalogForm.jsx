import React from 'react';

export function isSiglaSistema(item) {
  return /^0[A-Z]/i.test(String(item?.sigla || ''));
}

export function fkId(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'object') return value.id ?? null;
  return value;
}

export function labeledStats(stats = []) {
  return stats.map((s) => ({ id: s.id, nome: `${s.sigla || '—'} — ${s.nome}` }));
}

export function labeledPunteggi(list = []) {
  return list.map((p) => ({
    id: p.id,
    nome: p.sigla ? `${p.sigla} — ${p.nome}` : p.nome,
  }));
}

export const Flag = ({ label, checked, onChange }) => (
  <label className="flex items-center gap-2 min-h-11 text-sm text-gray-200">
    <input type="checkbox" checked={!!checked} onChange={(e) => onChange(e.target.checked)} />
    {label}
  </label>
);

export const Section = ({ title, children }) => (
  <div className="space-y-2 rounded border border-gray-700 p-3 min-w-0">
    {title ? <h3 className="text-xs uppercase tracking-wider text-gray-400 font-bold break-words">{title}</h3> : null}
    {children}
  </div>
);

export const FieldLabel = ({ children }) => (
  <label className="text-xs text-gray-500 uppercase font-bold">{children}</label>
);

export const TextInput = ({ value, onChange, className = '', ...rest }) => (
  <input
    className={`w-full min-h-11 bg-gray-800 border border-gray-700 rounded p-2 text-white min-w-0 ${className}`}
    value={value ?? ''}
    onChange={(e) => onChange(e.target.value)}
    {...rest}
  />
);

export function ChipToggle({ items, selected, onToggle, labelOf }) {
  const [query, setQuery] = React.useState('');
  const selectedSet = new Set((selected || []).map((x) => String(x)));
  const needle = query.trim().toLowerCase();
  const filtered = (items || []).filter((item) => {
    if (!needle) return true;
    const label = labelOf ? labelOf(item) : item.nome;
    return String(label || '').toLowerCase().includes(needle);
  });
  const showSearch = (items || []).length > 8;

  return (
    <div className="space-y-2 min-w-0">
      {showSearch ? (
        <TextInput value={query} onChange={setQuery} placeholder="Filtra elenco…" />
      ) : null}
      <div className="flex flex-wrap gap-2 max-h-48 overflow-y-auto">
        {filtered.map((item) => {
          const id = item.id;
          const on = selectedSet.has(String(id));
          return (
            <button
              key={id}
              type="button"
              onClick={() => onToggle(id)}
              className={`min-h-11 px-3 py-2 rounded border text-sm break-words ${
                on ? 'bg-indigo-600 border-indigo-400 text-white' : 'bg-gray-900 border-gray-700 text-gray-300'
              }`}
            >
              {labelOf ? labelOf(item) : item.nome}
            </button>
          );
        })}
        {filtered.length === 0 ? (
          <p className="text-xs text-gray-500">Nessuna voce.</p>
        ) : null}
      </div>
    </div>
  );
}

export const PUNTEGGI_RESIDUI_TIPI = [
  { value: 'EL', label: 'Elemento' },
  { value: 'CO', label: 'Condizione' },
  { value: 'CU', label: 'Culto' },
  { value: 'VI', label: 'Via' },
  { value: 'AR', label: 'Arte' },
  { value: 'AT', label: 'Archetipo' },
  { value: 'CS', label: 'Castone' },
  { value: 'ND', label: 'Nodo' },
  { value: 'KA', label: 'Kata' },
];

export const METATALENTO_OPZIONI = [
  { value: 'NE', label: 'Nessun effetto' },
  { value: 'VP', label: 'Valore per punteggio' },
  { value: 'TX', label: 'Solo testo addizionale' },
  { value: 'LV', label: 'Abilità di livello pari o inferiore' },
];

export const MOSTRA_CLASSI_ARMA_OPZIONI = [
  { value: 'nessuno', label: 'Nessuno' },
  { value: 'materia', label: 'Classi arma per Materia' },
  { value: 'mod', label: 'Classi arma per Mod' },
];
