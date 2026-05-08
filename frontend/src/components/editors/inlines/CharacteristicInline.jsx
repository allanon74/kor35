import React from 'react';
import SearchableSelect from '../SearchableSelect';

const CharacteristicInline = ({ items, options, onChange, onAdd, onRemove }) => (
  <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700">
    <div className="flex justify-between items-center mb-4">
      <h3 className="text-sm font-bold text-gray-300 uppercase">Componenti (Caratteristiche)</h3>
      <button onClick={onAdd} className="text-xs bg-indigo-600 px-2 py-1 rounded">+ Aggiungi</button>
    </div>
    <div className="space-y-2">
      {items.map((item, i) => (
        <div key={i} className="flex gap-2">
          <div className="flex-1">
            <SearchableSelect
              options={options}
              value={item.caratteristica || ''}
              onChange={(val) => onChange(i, 'caratteristica', val || '')}
              placeholder="Seleziona..."
              className="bg-gray-800 border-gray-700"
            />
          </div>
          <input 
            type="number" className="w-20 bg-gray-800 p-2 rounded text-sm text-center border border-gray-700"
            value={item.valore} onChange={e => onChange(i, 'valore', e.target.value)} 
          />
          <button onClick={() => onRemove(i)} className="text-red-500 px-2">✕</button>
        </div>
      ))}
    </div>
  </div>
);

export default CharacteristicInline;