import React from 'react';
import { Edit, Trash2, Layers, ListOrdered } from 'lucide-react';

const TabellaList = ({ tiers, onEdit, onDelete }) => {
    return (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3 p-4">
            {tiers.map(tier => (
                <div key={tier.id} className="bg-gray-800 border border-gray-700 rounded-lg p-3 shadow-md hover:border-gray-500 transition-all flex flex-col group relative overflow-hidden h-24">
                    
                    {/* Header Row: Tipo, Nome e Azioni */}
                    <div className="flex justify-between items-start z-10">
                        <div className="flex-1 min-w-0 pr-2">
                            <div className="flex items-center gap-2 mb-0.5">
                                <span className="text-[9px] uppercase tracking-widest font-bold text-indigo-300 bg-indigo-900/40 px-1.5 py-px rounded border border-indigo-500/20 truncate">
                                    {tier.tipo || 'Generico'}
                                </span>
                            </div>
                            <h3 className="text-sm font-bold text-gray-100 leading-tight truncate" title={tier.nome}>
                                {tier.nome}
                            </h3>
                        </div>

                        {/* Actions (Icone compatte) */}
                        <div className="flex items-center gap-1 shrink-0 bg-gray-900/80 rounded-md p-0.5 border border-gray-700/50 backdrop-blur-sm">
                            <button 
                                onClick={() => onEdit(tier)}
                                className="p-1.5 text-gray-400 hover:text-white hover:bg-indigo-600 rounded transition-all"
                                title="Modifica"
                            >
                                <Edit size={14} />
                            </button>
                            <div className="w-px h-3 bg-gray-700"></div>
                            <button 
                                onClick={() => onDelete(tier.id)}
                                className="p-1.5 text-gray-400 hover:text-white hover:bg-red-600 rounded transition-all"
                                title="Elimina"
                            >
                                <Trash2 size={14} />
                            </button>
                        </div>
                    </div>

                    {/* Footer Row: Conteggio Abilità */}
                    <div className="mt-auto flex items-end justify-between z-10">
                        <div className="flex items-center gap-1.5 text-xs text-gray-500">
                            <ListOrdered size={14} className="text-emerald-500/80" />
                            <span className="font-mono font-bold text-gray-300">{tier.abilita_count || 0}</span>
                            <span className="text-[10px] uppercase">Abilità</span>
                        </div>
                    </div>

                    {/* Sfondo decorativo molto leggero e piccolo */}
                    <Layers className="absolute -bottom-3 -right-3 text-white/3 w-16 h-16 rotate-12 pointer-events-none group-hover:scale-110 group-hover:text-white/5 transition-all" />
                </div>
            ))}

            {/* Empty State compatto */}
            {tiers.length === 0 && (
                <div className="col-span-full flex flex-col items-center justify-center py-8 text-gray-500 border-2 border-dashed border-gray-700 rounded-lg bg-gray-800/30">
                    <Layers size={32} className="mb-2 opacity-50" />
                    <p className="text-sm font-medium">Nessuna tabella trovata</p>
                </div>
            )}
        </div>
    );
};

export default TabellaList;