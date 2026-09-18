import React from 'react';
import SearchableSelect from '../SearchableSelect';

const CharacteristicInline = ({ items, options, onChange, onAdd, onRemove }) => (
  <div className="bg-gray-900/50 p-3 sm:p-4 rounded-lg border border-gray-700 min-w-0">
    <div className="flex flex-wrap justify-between items-center gap-2 mb-4">
      <h3 className="text-sm font-bold text-gray-300 uppercase min-w-0 break-words">Componenti (Caratteristiche)</h3>
      <button type="button" onClick={onAdd} className="shrink-0 text-xs bg-indigo-600 px-3 py-2 rounded min-h-11">+ Aggiungi</button>
    </div>
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="flex gap-2 min-w-0">
          <div className="flex-1 min-w-0">
            <SearchableSelect
              options={options}
              value={item.caratteristica || ''}
              onChange={(val) => onChange(i, 'caratteristica', val || '')}
              placeholder="Seleziona..."
              className="bg-gray-800 border-gray-700"
            />
          </div>
          <input 
            type="number" className="w-16 sm:w-20 shrink-0 bg-gray-800 p-2 rounded text-sm text-center border border-gray-700"
            value={item.valore} onChange={e => onChange(i, 'valore', e.target.value)} 
          />
          <button type="button" onClick={() => onRemove(i)} className="text-red-500 px-2 min-h-11 min-w-11 shrink-0">✕</button>
        </div>
      ))}
    </div>
  </div>
);

export default CharacteristicInline;