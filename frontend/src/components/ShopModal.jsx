import React, { useState, useCallback } from 'react';
import { Dialog } from '@headlessui/react';
import { X, ShoppingBag, Loader2, Info } from 'lucide-react';
import { useShopItems, useOptimisticBuyShopItem } from '../hooks/useGameData';
import { useCharacter } from './CharacterContext';

const ShopModal = ({ onClose }) => {
  const { onLogout, selectedCharacterData: char, refreshCharacterData } = useCharacter();
  const { data: items, isLoading } = useShopItems(onLogout);
  const buyMutation = useOptimisticBuyShopItem();

  const handleBuy = useCallback(async (item) => {
    // Nota: OggettoBase usa 'costo', non 'costo_acquisto'
    if (char.crediti < item.costo) {
        alert("Crediti insufficienti!");
        return;
    }
    if (!window.confirm(`Acquistare ${item.nome} per ${item.costo} CR?`)) return;

    try {
        // L'API si aspetta 'oggetto_id' che qui è l'ID del template OggettoBase
        await buyMutation.mutateAsync({ 
            oggettoId: item.id, 
            charId: char.id,
            costo: item.costo
        });
        await refreshCharacterData(); // Ricarica inventario e crediti
        // Non chiudiamo il modale per permettere acquisti multipli
    } catch (error) {
        alert("Errore acquisto: " + error.message);
    }
  }, [buyMutation, char, refreshCharacterData]);

  return (
    <Dialog open={true} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />
      
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-2xl bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-h-[90vh] flex flex-col animate-fadeIn">
            {/* Header */}
            <div className="flex justify-between items-center p-4 border-b border-gray-700 bg-gray-800/50 rounded-t-xl">
                <Dialog.Title className="text-xl font-bold text-white flex items-center gap-2">
                    <ShoppingBag className="text-yellow-500" />
                    Negozio Base
                </Dialog.Title>
                <div className="flex items-center gap-4">
                    <div className="text-sm font-mono text-yellow-400 bg-yellow-900/20 px-3 py-1 rounded-full border border-yellow-700/30">
                        {char?.crediti || 0} CR
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white transition-colors">
                        <X size={24} />
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="p-4 overflow-y-auto grow custom-scrollbar">
                {isLoading ? (
                    <div className="flex justify-center p-8"><Loader2 className="animate-spin text-indigo-500" size={32} /></div>
                ) : (
                    <div className="grid gap-3 sm:grid-cols-2">
                        {items?.map((item) => (
                            <div key={item.id} className="bg-gray-800 p-3 rounded-lg border border-gray-700 flex flex-col justify-between hover:border-gray-600 transition-colors group">
                                <div>
                                    <div className="flex justify-between items-start mb-1">
                                        <h4 className="font-bold text-gray-200">{item.nome}</h4>
                                        <span className="text-[10px] uppercase bg-gray-900 px-2 py-0.5 rounded text-gray-400 border border-gray-700 font-bold tracking-wider">
                                            {item.classe_oggetto_nome || "Oggetto"}
                                        </span>
                                    </div>
                                    
                                    {/* Descrizione e Stats */}
                                    <div className="text-xs text-gray-400 mb-2 line-clamp-2">
                                        {item.descrizione || <i>Nessuna descrizione</i>}
                                    </div>
                                    
                                    {/* Statistiche Tecniche (es. Danni, Bonus) */}
                                    {item.stats_text && (
                                        <div className="mb-3 text-[10px] text-indigo-300 bg-indigo-900/20 px-2 py-1 rounded border border-indigo-500/20 flex items-start gap-1">
                                            <Info size={12} className="shrink-0 mt-0.5" />
                                            <span>{item.stats_text}</span>
                                        </div>
                                    )}
                                </div>
                                
                                <div className="flex justify-between items-center mt-auto pt-3 border-t border-gray-700/50">
                                    <span className="font-mono font-bold text-yellow-500">{item.costo} CR</span>
                                    <button
                                        onClick={() => handleBuy(item)}
                                        disabled={buyMutation.isPending || char.crediti < item.costo}
                                        className={`px-3 py-1.5 rounded text-sm font-bold flex items-center gap-2 transition-all ${
                                            char.crediti >= item.costo
                                                ? 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20'
                                                : 'bg-gray-700 text-gray-500 cursor-not-allowed opacity-50'
                                        }`}
                                    >
                                        {buyMutation.isPending ? <Loader2 className="animate-spin" size={16} /> : "Compra"}
                                    </button>
                                </div>
                            </div>
                        ))}
                        {(!items || items.length === 0) && (
                            <div className="col-span-full text-center text-gray-500 py-12 border border-dashed border-gray-700 rounded-xl">
                                Nessun oggetto attualmente in vendita.
                            </div>
                        )}
                    </div>
                )}
            </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default ShopModal;