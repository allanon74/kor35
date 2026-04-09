import React, { useState, Fragment, useMemo, useCallback } from 'react';
import { Tab } from '@headlessui/react';
import { useCharacter } from './CharacterContext';
import { Loader2, ShoppingCart, Info, CheckCircle2, PlusCircle, FileEdit, Users, Trash2 } from 'lucide-react';

// --- COMPONENTS ---
import GenericGroupedList from './GenericGroupedList';
import PunteggioDisplay from './PunteggioDisplay';     
import IconaPunteggio from './IconaPunteggio';
import ProposalManager from './ProposalManager';
import ProposalEditorModal from './ProposalEditorModal';

// --- API & HOOKS ---
import { useOptimisticAcquireCerimoniale, useRevokeCerimoniale } from '../hooks/useGameData';

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const CerimonialiTab = ({ onLogout }) => {
  const {
    selectedCharacterData: char,
    selectedCharacterId, 
    acquirableCerimoniali, 
    refreshCharacterData,
    isLoadingAcquirable,
    isLoadingDetail
  } = useCharacter();
  
  const [modalItem, setModalItem] = useState(null);
  const [showProposals, setShowProposals] = useState(false);
  const acquireMutation = useOptimisticAcquireCerimoniale();
  const revokeMutation = useRevokeCerimoniale();

  // Recupero Valore Coralità (CCO)
  const ccoValue = useMemo(() => {
    const stat = char?.statistiche_primarie?.find(s => s.sigla === 'CCO');
    return stat ? stat.valore_corrente : (char?.statistiche_temporanee?.['CCO'] || 0);
  }, [char]);

  // Logica di Filtraggio Cerimoniali Acquistabili
  const filteredAcquirable = useMemo(() => {
    if (!acquirableCerimoniali || !char) return [];
    return acquirableCerimoniali.filter(cer => {
      const auraScore = char.punteggi_base?.[cer.aura_richiesta_nome] || 0;
      const limit = Math.min(ccoValue, auraScore);
      return cer.livello <= limit;
    });
  }, [acquirableCerimoniali, char, ccoValue]);

  const handleAcquire = useCallback(async (item, e) => {
    e.stopPropagation();
    if (acquireMutation.isPending || !selectedCharacterId) return;
    if (!window.confirm(`Apprendere il Cerimoniale "${item.nome}" per ${item.costo_crediti} Crediti?`)) return;
    
    try {
      await acquireMutation.mutateAsync({ 
        cerimonialeId: item.id, 
        charId: selectedCharacterId,
        onLogout 
      });
      refreshCharacterData();
    } catch (error) {
      alert(`Errore: ${error.message}`);
    }
  }, [acquireMutation, selectedCharacterId, onLogout, refreshCharacterData]);

  const handleRevoke = useCallback(
    async (item, e) => {
      e.stopPropagation();
      if (revokeMutation.isPending || !selectedCharacterId) return;
      if (!window.confirm(`Revocare l'acquisto del Cerimoniale "${item.nome}"?`)) return;
      try {
        await revokeMutation.mutateAsync({
          cerimonialeId: item.id,
          charId: selectedCharacterId,
          onLogout,
        });
        refreshCharacterData();
      } catch (error) {
        alert(`Errore: ${error.message}`);
      }
    },
    [revokeMutation, selectedCharacterId, onLogout, refreshCharacterData]
  );

  if (isLoadingAcquirable || isLoadingDetail || !char) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="animate-spin text-purple-500" size={48} />
      </div>
    );
  }

  const renderGroupHeader = (group) => (
    <PunteggioDisplay 
        punteggio={{ nome: group.name, colore: group.color, icona_url: group.icon }}
        value={group.items.length}
        displayText="name"
        iconType="inv_circle"
        size="s"
        className="rounded-b-none border-purple-500/30"
    />
  );

  const renderItem = (item, isOwned) => (
    <li className="flex justify-between items-center py-3 px-2 hover:bg-gray-700/30 transition-colors rounded-sm border-b border-gray-700/50 last:border-0 gap-2">
      <div className="flex items-center gap-3 cursor-pointer grow" onClick={() => setModalItem(item)}>
          <div className="shrink-0 relative">
              <IconaPunteggio url={item.aura_richiesta?.icona_url} color={item.aura_richiesta?.colore} mode="cerchio_inv" size="xs" />
              <span className="absolute -top-2 -right-2 bg-purple-900 text-purple-100 text-[9px] font-bold px-1 py-0.5 rounded-full border border-purple-500">
                  L{item.livello}
              </span>
          </div>
          <div className="flex flex-col">
            <span className="font-bold text-gray-200">{item.nome}</span>
            {!isOwned && <span className="text-[10px] text-yellow-500 font-mono">{item.costo_crediti} CR</span>}
          </div>
      </div>
      <div className="flex items-center gap-2">
        {!isOwned && (
          <button
            onClick={(e) => handleAcquire(item, e)}
            disabled={char.crediti < item.costo_crediti || acquireMutation.isPending}
            className="p-2 bg-purple-600 hover:bg-purple-500 disabled:bg-gray-700 text-white rounded-lg transition-all"
          >
            {acquireMutation.isPending ? <Loader2 size={16} className="animate-spin"/> : <ShoppingCart size={16} />}
          </button>
        )}
        {isOwned && item.is_modifiable && (
          <button
            onClick={(e) => handleRevoke(item, e)}
            disabled={revokeMutation.isPending}
            className="p-2 text-red-400 hover:text-red-200 hover:bg-red-900/20 rounded-full transition-colors"
            title="Revoca acquisto"
          >
            <Trash2 size={18} />
          </button>
        )}
        <button onClick={() => setModalItem(item)} className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-full">
          <Info size={18} />
        </button>
      </div>
    </li>
  );

  return (
    <div className="w-full p-4 max-w-6xl mx-auto pb-24">
      <div className="mb-6 flex justify-between items-center bg-gray-800 p-4 rounded-xl border border-purple-500/20 shadow-lg max-w-3xl mx-auto">
          <div className="flex items-center gap-3">
            <Users className="text-purple-400" size={24}/>
            <div>
              <div className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">Coralità (CCO)</div>
              <div className="text-xl font-black text-purple-300 leading-none">{ccoValue}</div>
            </div>
          </div>
          <div className="text-right">
              <div className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">Crediti</div>
              <div className="text-xl font-black text-yellow-500 leading-none">{char.crediti} CR</div>
          </div>
      </div>

      <div className="flex justify-end mb-6 max-w-3xl mx-auto">
          <button onClick={() => setShowProposals(true)} className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-purple-300 px-4 py-2 rounded-lg border border-purple-500/30 transition-all text-sm font-bold">
              <FileEdit size={16} /> Gestisci Proposte Cerimoniale
          </button>
      </div>

      <div className="hidden md:grid grid-cols-2 gap-6">
          <div>
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2 px-2"><CheckCircle2 className="text-green-500" size={20}/> Posseduti</h2>
              <GenericGroupedList items={char.cerimoniali_posseduti} groupByKey="aura_richiesta" renderItem={(i) => renderItem(i, true)} renderHeader={renderGroupHeader} itemSortFn={(a,b) => a.livello - b.livello} />
          </div>
          <div>
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2 px-2"><PlusCircle className="text-purple-500" size={20}/> Nuovi Cerimoniali</h2>
              <GenericGroupedList items={filteredAcquirable} groupByKey="aura_richiesta" renderItem={(i) => renderItem(i, false)} renderHeader={renderGroupHeader} itemSortFn={(a,b) => a.livello - b.livello} />
          </div>
      </div>

      {/* Dettaglio Modale */}
      {modalItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/90 backdrop-blur-md" onClick={() => setModalItem(null)}>
          <div className="bg-gray-900 border border-purple-500/30 rounded-2xl w-full max-w-lg max-h-[85vh] flex flex-col shadow-2xl overflow-hidden" onClick={e => e.stopPropagation()}>
             <div className="p-5 border-b border-gray-800 flex justify-between items-start bg-gray-800/50">
                <div>
                    <h3 className="text-xl font-black text-purple-400 uppercase">{modalItem.nome}</h3>
                    <p className="text-[10px] text-gray-500 uppercase font-bold">Livello {modalItem.livello} • {modalItem.aura_richiesta_nome}</p>
                </div>
                <button onClick={() => setModalItem(null)} className="text-gray-400 hover:text-white transition-colors">✕</button>
             </div>
             <div className="p-6 overflow-y-auto space-y-6 text-sm">
                <div><h4 className="text-[10px] font-black text-purple-500 uppercase mb-1">Prerequisiti</h4><p className="text-gray-300 italic">{modalItem.prerequisiti}</p></div>
                <div><h4 className="text-[10px] font-black text-gray-500 uppercase mb-1">Svolgimento</h4><div className="text-gray-300 whitespace-pre-wrap">{modalItem.svolgimento}</div></div>
                <div className="bg-purple-900/10 p-4 rounded-xl border border-purple-500/20"><h4 className="text-[10px] font-black text-purple-300 uppercase mb-1">Effetto</h4><div className="text-gray-200">{modalItem.effetto}</div></div>
             </div>
          </div>
        </div>
      )}

      {showProposals && <ProposalManager type="Cerimoniale" onClose={() => setShowProposals(false)} />}
    </div>
  );
};

export default CerimonialiTab;