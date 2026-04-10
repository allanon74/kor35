import React from 'react';

const StatBaseInline = ({ items, options, onChange }) => {
  return (
    <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700 w-full">
      <div className="mb-4 border-b border-gray-800 pb-2">
        <h3 className="text-sm font-bold uppercase tracking-widest text-indigo-400">Statistiche Base per l'abilità</h3>
        <p className="text-[9px] text-gray-500 italic uppercase font-medium">Parametri tecnici per la definizione dell'effetto</p>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-x-8 gap-y-2 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
        {options.map((stat) => {
          const existingRecord = items.find(it => (it.statistica?.id || it.statistica) === stat.id);
          
          let displayValue = existingRecord?.valore_base;
          
          // ORA IL BACKEND INVIA SEMPRE 'valore_base_predefinito'
          if (displayValue === null || displayValue === undefined || displayValue === "") {
            displayValue = stat.valore_base_predefinito;
          }

          return (
            <div key={stat.id} className="flex items-center gap-3 bg-gray-800/20 p-2 rounded hover:bg-gray-800/50 transition-all border border-transparent hover:border-gray-700/50 group">
              <div className="flex-1 flex items-baseline gap-2 overflow-hidden">
                <span className="text-[11px] font-bold text-gray-300 truncate">{stat.nome}</span>
                <span className="text-[9px] text-gray-600 font-mono group-hover:text-indigo-400 transition-colors">({stat.parametro})</span>
              </div>
              
              <div className="w-20 shrink-0">
                <input 
                  type="number" 
                  step="any"
                  className="w-full bg-gray-950 p-1.5 rounded text-xs text-center border border-gray-800 text-amber-500 focus:border-indigo-500 outline-none font-bold"
                  value={displayValue ?? ""} 
                  onChange={e => {
                    const newVal = e.target.value;
                    const recordIndex = items.findIndex(it => (it.statistica?.id || it.statistica) === stat.id);
                    
                    if (recordIndex !== -1) {
                      onChange(recordIndex, 'valore_base', newVal);
                    } else {
                      onChange(-1, 'statistica', { statId: stat.id, value: newVal });
                    }
                  }} 
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StatBaseInline;