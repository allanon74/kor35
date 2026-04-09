import React from 'react';
import SearchableSelect from '../SearchableSelect';

const StatModInline = ({ items, options, auraOptions, elementOptions, onChange, onAdd, onRemove }) => {
  const toggleM2M = (index, field, id) => {
    const currentList = items[index][field] || [];
    const newList = currentList.includes(id)
      ? currentList.filter(item => item !== id)
      : [...currentList, id];
    onChange(index, field, newList);
  };

  return (
    <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-sm font-bold text-emerald-400 uppercase tracking-widest">Modifica Generale alle statistiche</h3>
        <button onClick={onAdd} className="text-xs bg-emerald-600 hover:bg-emerald-500 px-3 py-1 rounded font-bold transition-all shadow-md">+ AGGIUNGI MODIFICATORE</button>
      </div>
      
      <div className="space-y-4">
        {items.map((item, i) => (
          <div key={i} className="bg-gray-800/80 p-4 rounded border border-gray-700 space-y-4 shadow-xl">
            <div className="flex flex-wrap gap-3">
              <div className="flex-1 min-w-[200px]">
                <label className="text-[9px] uppercase text-gray-500 font-black block mb-1">Statistica</label>
                <SearchableSelect
                  options={options.filter(o => {
                    const isUsed = items.some((it, idx) => idx !== i && (it.statistica?.id || it.statistica) === o.id);
                    const isCurrent = (item.statistica?.id || item.statistica) === o.id;
                    return isCurrent || !isUsed;
                  })}
                  value={item.statistica?.id || item.statistica || ""} 
                  onChange={val => onChange(i, 'statistica', val ? parseInt(val, 10) : null)}
                  placeholder="Seleziona..."
                />
              </div>
              <div className="w-32">
                <label className="text-[9px] uppercase text-gray-500 font-black block mb-1">Tipo</label>
                <select className="w-full bg-gray-900 p-2 rounded text-sm border border-gray-600 text-white"
                  value={item.tipo_modificatore} onChange={e => onChange(i, 'tipo_modificatore', e.target.value)}>
                  <option value="ADD">Additivo (+)</option>
                  <option value="MOL">Moltiplicatore (x)</option>
                </select>
              </div>
              <div className="w-24">
                <label className="text-[9px] uppercase text-gray-500 font-black block mb-1">Valore</label>
                <input type="number" step="any" className="w-full bg-gray-900 p-2 rounded text-sm text-center border border-gray-600 text-white"
                  value={item.valore} onChange={e => onChange(i, 'valore', e.target.value)} />
              </div>
              <button onClick={() => onRemove(i)} className="self-end mb-1 text-red-500 hover:bg-red-500/10 p-2 rounded transition-colors text-xl">✕</button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 bg-black/30 p-3 rounded border border-gray-800">
              <div className="space-y-2">
                <ConditionToggle label="Usa Limite Aura" checked={item.usa_limitazione_aura} onChange={v => onChange(i, 'usa_limitazione_aura', v)} color="indigo" />
                {item.usa_limitazione_aura && <M2MSelector options={auraOptions} selected={item.limit_a_aure} onToggle={id => toggleM2M(i, 'limit_a_aure', id)} color="indigo" />}
              </div>
              <div className="space-y-2 border-x border-gray-800/50 px-4">
                <ConditionToggle label="Usa Limite Elemento" checked={item.usa_limitazione_elemento} onChange={v => onChange(i, 'usa_limitazione_elemento', v)} color="emerald" />
                {item.usa_limitazione_elemento && <M2MSelector options={elementOptions} selected={item.limit_a_elementi} onToggle={id => toggleM2M(i, 'limit_a_elementi', id)} color="emerald" />}
              </div>
              <div className="space-y-2">
                <ConditionToggle label="Usa Condizione Testo" checked={item.usa_condizione_text} onChange={v => onChange(i, 'usa_condizione_text', v)} color="amber" />
                {item.usa_condizione_text && (
                  <input placeholder="Formula o condizione..." className="w-full bg-gray-900 p-2 rounded text-[10px] border border-gray-700 text-amber-500 font-mono"
                    value={item.condizione_text || ''} onChange={e => onChange(i, 'condizione_text', e.target.value)} />
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

const ConditionToggle = ({ label, checked, onChange, color }) => (
    <label className="flex items-center gap-2 cursor-pointer group">
      <input type="checkbox" className={`accent-${color}-500`} checked={checked} onChange={e => onChange(e.target.checked)} />
      <span className="text-[10px] font-black text-gray-500 group-hover:text-gray-300 uppercase">{label}</span>
    </label>
);

const M2MSelector = ({ options, selected = [], onToggle, color }) => (
    <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto p-1">
      {options.map(o => (
        <button key={o.id} onClick={() => onToggle(o.id)}
          className={`text-[9px] px-2 py-0.5 rounded border transition-all ${selected.includes(o.id) ? `bg-${color}-600 border-${color}-400 text-white` : 'bg-gray-900 border-gray-700 text-gray-600'}`}>
          {o.nome}
        </button>
      ))}
    </div>
);

export default StatModInline;