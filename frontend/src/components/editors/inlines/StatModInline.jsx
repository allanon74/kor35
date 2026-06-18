import React from 'react';
import SearchableSelect from '../SearchableSelect';

const PHYSICAL_EQUIP_SLOTS = [
    { key: 'head', label: 'Testa' },
    { key: 'neck', label: 'Collo' },
    { key: 'vest', label: 'Veste' },
    { key: 'shoulders', label: 'Spalle' },
    { key: 'arms', label: 'Braccia' },
    { key: 'fingers', label: 'Dita' },
    { key: 'feet', label: 'Piedi' },
    { key: 'belt', label: 'Cintura' },
    { key: 'armor', label: 'Armatura' },
    { key: 'melee', label: 'Armi mischia' },
    { key: 'ranged', label: 'Armi distanza' },
    { key: 'focus', label: 'Focus' },
    { key: 'shield', label: 'Scudo' },
];

const SLOT_EQUIP_CONTEGGIO_OPTIONS = [
    {
        value: 'TUTTI_OGGETTI',
        label: 'Tutti gli oggetti equipaggiati',
        hint: 'Ogni oggetto fisico negli slot selezionati, modificato o meno.',
    },
    {
        value: 'OGNI_POTENZIAMENTO',
        label: 'Ogni Materia/Mod installata',
        hint: 'Conta ogni singola Materia o Mod montata su oggetti equipaggiati.',
    },
    {
        value: 'OGGETTI_MODIFICATI',
        label: 'Oggetti modificati',
        hint: 'Solo oggetti equipaggiati con almeno una Materia/Mod (max 1 per oggetto).',
    },
];

const EMPTY_SLOT_EQUIP_STAT = {
    usa_bonus_slot_equip: false,
    slot_equip_ammessi: [],
    modalita_conteggio_slot_equip: 'TUTTI_OGGETTI',
    valore_per_unita_slot_equip: 1,
};

const StatModInline = ({ items, options, auraOptions, elementOptions, onChange, onAdd, onRemove, showSlotEquipBonus = false }) => {
  const toggleM2M = (index, field, id) => {
    const currentList = items[index][field] || [];
    const newList = currentList.includes(id)
      ? currentList.filter(item => item !== id)
      : [...currentList, id];
    onChange(index, field, newList);
  };

  const toggleSlotEquip = (index, slotKey) => {
    const current = items[index].slot_equip_ammessi || [];
    const newList = current.includes(slotKey)
      ? current.filter((key) => key !== slotKey)
      : [...current, slotKey];
    onChange(index, 'slot_equip_ammessi', newList);
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
                <label className="text-[9px] uppercase text-gray-500 font-black block mb-1">
                  {item.usa_bonus_slot_equip ? 'Bonus fisso' : 'Valore'}
                </label>
                <input type="number" step="any" className="w-full bg-gray-900 p-2 rounded text-sm text-center border border-gray-600 text-white"
                  value={item.valore} onChange={e => onChange(i, 'valore', e.target.value)} />
              </div>
              <button onClick={() => onRemove(i)} className="self-end mb-1 text-red-500 hover:bg-red-500/10 p-2 rounded transition-colors text-xl">✕</button>
            </div>

            {showSlotEquipBonus && (
              <div className="bg-emerald-950/20 p-3 rounded border border-emerald-900/40 space-y-3">
                <ConditionToggle
                  label="Bonus per oggetti equipaggiati (solo con abilità)"
                  checked={!!item.usa_bonus_slot_equip}
                  onChange={(v) => onChange(i, 'usa_bonus_slot_equip', v)}
                  color="emerald"
                />
                {item.usa_bonus_slot_equip && (
                  <>
                    <div>
                      <label className="text-[9px] uppercase text-emerald-600 font-black block mb-2">Slot ammessi</label>
                      <div className="flex flex-wrap gap-1">
                        {PHYSICAL_EQUIP_SLOTS.map((slot) => (
                          <button
                            key={slot.key}
                            type="button"
                            onClick={() => toggleSlotEquip(i, slot.key)}
                            className={`text-[9px] px-2 py-0.5 rounded border transition-all ${
                              (item.slot_equip_ammessi || []).includes(slot.key)
                                ? 'bg-emerald-600 border-emerald-400 text-white'
                                : 'bg-gray-900 border-gray-700 text-gray-600'
                            }`}
                          >
                            {slot.label}
                          </button>
                        ))}
                      </div>
                    </div>
                    <div>
                      <label className="text-[9px] uppercase text-emerald-600 font-black block mb-2">Modalità conteggio</label>
                      <div className="space-y-2">
                        {SLOT_EQUIP_CONTEGGIO_OPTIONS.map((opt) => (
                          <label
                            key={opt.value}
                            className={`flex items-start gap-2 p-2 rounded border cursor-pointer transition-colors ${
                              (item.modalita_conteggio_slot_equip || 'TUTTI_OGGETTI') === opt.value
                                ? 'border-emerald-500 bg-emerald-950/40'
                                : 'border-gray-700 bg-gray-900/50 hover:border-gray-600'
                            }`}
                          >
                            <input
                              type="radio"
                              name={`slot-equip-mode-${i}`}
                              className="mt-0.5 accent-emerald-500"
                              checked={(item.modalita_conteggio_slot_equip || 'TUTTI_OGGETTI') === opt.value}
                              onChange={() => onChange(i, 'modalita_conteggio_slot_equip', opt.value)}
                            />
                            <span>
                              <span className="text-[11px] font-bold text-gray-200 block">{opt.label}</span>
                              <span className="text-[10px] text-gray-500">{opt.hint}</span>
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>
                    <div className="w-40">
                      <label className="text-[9px] uppercase text-gray-500 font-black block mb-1">Valore per unità</label>
                      <input
                        type="number"
                        className="w-full bg-gray-900 p-2 rounded text-sm text-center border border-gray-600 text-white"
                        value={item.valore_per_unita_slot_equip ?? 1}
                        onChange={(e) => onChange(i, 'valore_per_unita_slot_equip', parseInt(e.target.value, 10) || 0)}
                      />
                    </div>
                  </>
                )}
              </div>
            )}

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
export { EMPTY_SLOT_EQUIP_STAT, PHYSICAL_EQUIP_SLOTS, SLOT_EQUIP_CONTEGGIO_OPTIONS };
