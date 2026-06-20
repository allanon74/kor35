import React, { useState, useCallback, useMemo } from 'react';
import { Dialog } from '@headlessui/react';
import { X, ShoppingBag, Loader2, Info } from 'lucide-react';
import { useShopItems, useOptimisticBuyShopItem } from '../hooks/useGameData';
import { useCharacter } from './CharacterContext';

const TIPO_OGGETTO_CHOICES = [
  { id: 'FIS', label: 'Fisico' },
  { id: 'MAT', label: 'Materia' },
  { id: 'MOD', label: 'Mod' },
  { id: 'INN', label: 'Innesto' },
  { id: 'MUT', label: 'Mutazione' },
  { id: 'AUM', label: 'Aumento' },
  { id: 'POT', label: 'Potenziamento' },
];

const tipoLabel = (code) => TIPO_OGGETTO_CHOICES.find((t) => t.id === code)?.label || code || '—';

const ShopModal = ({ onClose, searchTerm: externalSearchTerm, onSearchTermChange }) => {
  const { onLogout, selectedCharacterData: char, refreshCharacterData } = useCharacter();
  const { data: items, isLoading } = useShopItems(onLogout, char?.id);
  const buyMutation = useOptimisticBuyShopItem();
  const [internalSearchTerm, setInternalSearchTerm] = useState('');
  const [filterTipo, setFilterTipo] = useState('');
  const [filterClasse, setFilterClasse] = useState('');
  const searchTerm = typeof externalSearchTerm === 'string' ? externalSearchTerm : internalSearchTerm;
  const setSearchTerm = onSearchTermChange || setInternalSearchTerm;

  const classeOptions = useMemo(() => {
    const list = Array.isArray(items) ? items : [];
    const names = new Set();
    list.forEach((item) => {
      const nome = String(item?.classe_oggetto_nome || '').trim();
      if (nome) names.add(nome);
    });
    return [...names].sort((a, b) => a.localeCompare(b, 'it'));
  }, [items]);

  const tipoOptionsInList = useMemo(() => {
    const list = Array.isArray(items) ? items : [];
    const codes = new Set(list.map((item) => item?.tipo_oggetto).filter(Boolean));
    return TIPO_OGGETTO_CHOICES.filter((t) => codes.has(t.id));
  }, [items]);

  const filteredItems = useMemo(() => {
    const list = Array.isArray(items) ? items : [];
    const q = searchTerm.trim().toLowerCase();
    return list.filter((item) => {
      if (filterTipo && item?.tipo_oggetto !== filterTipo) return false;
      if (filterClasse && String(item?.classe_oggetto_nome || '') !== filterClasse) return false;
      if (!q) return true;
      const nome = String(item?.nome || '').toLowerCase();
      const classe = String(item?.classe_oggetto_nome || '').toLowerCase();
      const descrizione = String(item?.descrizione || '').toLowerCase();
      const tipo = tipoLabel(item?.tipo_oggetto).toLowerCase();
      return nome.includes(q) || classe.includes(q) || descrizione.includes(q) || tipo.includes(q);
    });
  }, [items, searchTerm, filterTipo, filterClasse]);

  const handleBuy = useCallback(async (item) => {
    if (char.crediti < item.costo) {
      alert('Crediti insufficienti!');
      return;
    }
    if (!window.confirm(`Acquistare ${item.nome} per ${item.costo} CR?`)) return;

    try {
      await buyMutation.mutateAsync({
        oggettoId: item.id,
        charId: char.id,
        costo: item.costo,
      });
      await refreshCharacterData();
    } catch (error) {
      alert(`Errore acquisto: ${error.message}`);
    }
  }, [buyMutation, char, refreshCharacterData]);

  const clearFilters = () => {
    setSearchTerm('');
    setFilterTipo('');
    setFilterClasse('');
  };

  const hasActiveFilters = Boolean(searchTerm.trim() || filterTipo || filterClasse);

  return (
    <Dialog open={true} onClose={onClose} className="relative z-50">
      <div className="fixed inset-0 bg-black/70 backdrop-blur-sm" aria-hidden="true" />

      <div className="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel className="w-full max-w-2xl bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-h-[90vh] flex flex-col animate-fadeIn">
          <div className="flex justify-between items-center p-4 border-b border-gray-700 bg-gray-800/50 rounded-t-xl">
            <Dialog.Title className="text-xl font-bold text-white flex items-center gap-2">
              <ShoppingBag className="text-yellow-500" />
              Accademia — Oggetti
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

          <div className="p-4 overflow-y-auto grow custom-scrollbar">
            <div className="mb-4 space-y-3">
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                placeholder="Filtra per nome, classe, tipologia o descrizione..."
                className="w-full bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500"
              />

              <div className="flex flex-wrap gap-2 items-center">
                <select
                  value={filterTipo}
                  onChange={(e) => setFilterTipo(e.target.value)}
                  className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500"
                >
                  <option value="">Tutte le tipologie</option>
                  {tipoOptionsInList.map((t) => (
                    <option key={t.id} value={t.id}>{t.label}</option>
                  ))}
                </select>

                <select
                  value={filterClasse}
                  onChange={(e) => setFilterClasse(e.target.value)}
                  className="bg-gray-950 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:border-indigo-500 min-w-[160px]"
                >
                  <option value="">Tutte le categorie</option>
                  {classeOptions.map((nome) => (
                    <option key={nome} value={nome}>{nome}</option>
                  ))}
                </select>

                {hasActiveFilters && (
                  <button
                    type="button"
                    onClick={clearFilters}
                    className="text-xs text-gray-400 hover:text-white px-2 py-1 rounded border border-gray-700"
                  >
                    Azzera filtri
                  </button>
                )}

                <span className="text-[11px] text-gray-500 ml-auto tabular-nums">
                  {filteredItems.length} / {(items || []).length}
                </span>
              </div>
            </div>

            {isLoading ? (
              <div className="flex justify-center p-8"><Loader2 className="animate-spin text-indigo-500" size={32} /></div>
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                {filteredItems.map((item) => (
                  <div key={item.id} className="bg-gray-800 p-3 rounded-lg border border-gray-700 flex flex-col justify-between hover:border-gray-600 transition-colors group">
                    <div>
                      <div className="flex justify-between items-start mb-1 gap-2">
                        <h4 className="font-bold text-gray-200">{item.nome}</h4>
                        <div className="flex flex-col items-end gap-1 shrink-0">
                          <span className="text-[10px] uppercase bg-gray-900 px-2 py-0.5 rounded text-gray-400 border border-gray-700 font-bold tracking-wider">
                            {item.classe_oggetto_nome || 'Oggetto'}
                          </span>
                          <span className="text-[9px] uppercase text-indigo-300/80">
                            {tipoLabel(item.tipo_oggetto)}
                          </span>
                        </div>
                      </div>

                      <div className="text-xs text-gray-400 mb-2 line-clamp-2">
                        {item.descrizione || <i>Nessuna descrizione</i>}
                      </div>

                      {item.attacco_formattato && (
                        <div className="mb-2 text-[10px] text-emerald-200 bg-emerald-900/20 px-2 py-1 rounded border border-emerald-500/20 flex items-start gap-1">
                          <Info size={12} className="shrink-0 mt-0.5" />
                          <span>Attacco: {item.attacco_formattato}</span>
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
                        {buyMutation.isPending ? <Loader2 className="animate-spin" size={16} /> : 'Compra'}
                      </button>
                    </div>
                  </div>
                ))}
                {filteredItems.length === 0 && (
                  <div className="col-span-full text-center text-gray-500 py-12 border border-dashed border-gray-700 rounded-xl">
                    Nessun oggetto trovato con questi filtri.
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
