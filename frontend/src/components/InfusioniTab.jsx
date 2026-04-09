import React, { useState, Fragment } from 'react';
import { Tab } from '@headlessui/react';
import { useCharacter } from './CharacterContext';
import { Loader2, ShoppingCart, Info, CheckCircle2, PlusCircle, FileEdit, Hammer, Trash2 } from 'lucide-react';

// --- COMPONENTS ---
import TecnicaDetailModal from './TecnicaDetailModal';
import GenericGroupedList from './GenericGroupedList';
import PunteggioDisplay from './PunteggioDisplay';     
import IconaPunteggio from './IconaPunteggio';
import ProposalManager from './ProposalManager';
import ForgingQueue from './ForgingQueue'; 
import ForgingModal from './ForgingModal'; // <--- NUOVO MODALE IMPORTATO

// --- API & HOOKS ---
import { useForgingQueue, useOptimisticAcquireInfusione, useRevokeInfusione } from '../hooks/useGameData'; 

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const InfusioniTab = ({ onLogout }) => {
  const {
    selectedCharacterData: char,
    selectedCharacterId, 
    acquirableInfusioni, 
    refreshCharacterData,
    isLoadingAcquirable,
    isLoadingDetail
  } = useCharacter();
  
  // Hook per la coda di forgiatura (aggiornamento automatico)
  const { data: forgingQueue, refetch: refetchQueue } = useForgingQueue(selectedCharacterId);
  
  // --- STATI LOCALI ---
  const [modalItem, setModalItem] = useState(null); // Per i dettagli (Info)
  const [showProposals, setShowProposals] = useState(false); // Gestione proposte

  // Stato per la modale di forgiatura avanzata
  const [selectedInfusioneForgia, setSelectedInfusioneForgia] = useState(null);

  const acquireMutation = useOptimisticAcquireInfusione();
  const revokeMutation = useRevokeInfusione();

  // --- HANDLERS ---

  const handleOpenModal = (item) => setModalItem(item);

  const handleRevoke = async (item, e) => {
    e.stopPropagation();
    if (!selectedCharacterId || revokeMutation.isPending) return;
    if (!window.confirm(`Revocare l'acquisto dell'infusione "${item.nome}"?`)) return;
    try {
      await revokeMutation.mutateAsync({ infusioneId: item.id, charId: selectedCharacterId, onLogout });
      refreshCharacterData();
    } catch (error) {
      alert(`Errore: ${error.message}`);
    }
  };

  // Gestione Acquisto Nuova Infusione (Apprendimento)
  const handleAcquire = async (item, e) => {
    e.stopPropagation();
    if (acquireMutation.isPending || !selectedCharacterId) return;
    
    const costoFinale = item.costo_effettivo ?? (item.costo_crediti || item.livello * 100);
    
    if (!window.confirm(`Apprendere l'Infusione "${item.nome}" per ${costoFinale} Crediti?`)) return;
    
    try {
      await acquireMutation.mutateAsync({ infusioneId: item.id, charId: selectedCharacterId, onLogout });
      refreshCharacterData();
    } catch (error) {
      alert(`Errore: ${error.message}`);
    }
  };

  // Gestione Apertura Forgiatura (MODIFICATO)
  // Invece di avviare subito, apriamo la modale per scegliere il metodo
  const handleForgeClick = (item, e) => {
    e.stopPropagation();
    setSelectedInfusioneForgia(item);
  };

  // Callback quando la forgiatura viene avviata dalla modale
  const onForgingStarted = () => {
      refetchQueue();       // Aggiorna la coda visuale
      refreshCharacterData(); // Aggiorna i crediti spesi
      setSelectedInfusioneForgia(null); // Chiudi modale
  };

  // --- LOGICA UI ---

  const sortItems = (items) => [...items].sort((a, b) => a.livello - b.livello);
  
  const possessed = sortItems(char?.infusioni_possedute || []);
  const acquirable = sortItems(acquirableInfusioni || []);

  if (isLoadingAcquirable || isLoadingDetail || !char) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={48} />
      </div>
    );
  }

  // Render Header Gruppo (es. per Aura)
  const renderGroupHeader = (group) => {
    const fakePunteggio = {
        nome: group.name,
        colore: group.color,
        icona_url: group.icon 
    };

    return (
        <PunteggioDisplay 
            punteggio={fakePunteggio}
            value={group.items.length}
            displayText="name"
            iconType="inv_circle"
            size="s"
            className="rounded-b-none"
        />
    );
  };

  // Render Elemento Lista (Posseduto)
  const renderPossessedItem = (item) => {
    const iconUrl = item.aura_richiesta?.icona_url;
    const iconColor = item.aura_richiesta?.colore;

    return (
      <li className="flex justify-between items-center py-2 px-2 hover:bg-gray-700/50 transition-colors rounded-sm border-b border-gray-700/50 last:border-0 gap-2">
        <div className="flex items-center gap-3 cursor-pointer grow" onClick={() => handleOpenModal(item)}>
            <div className="shrink-0 mt-0.5 relative">
                <IconaPunteggio url={iconUrl} color={iconColor} mode="cerchio_inv" size="xs" />
                <span className="absolute -top-2 -right-2 bg-gray-900 text-gray-200 text-[9px] font-bold px-1 py-0.5 rounded-full border border-gray-600 leading-none">
                    L{item.livello}
                </span>
            </div>
            <span className="font-bold text-gray-200 text-base">{item.nome}</span>
        </div>
        
        {/* Tasto Forgia (Apre Modale) */}
        <button
            onClick={(e) => handleForgeClick(item, e)}
            className="flex items-center gap-1 px-3 py-1.5 bg-orange-700 hover:bg-orange-600 text-white rounded text-xs font-bold uppercase tracking-wider transition-all shadow-sm hover:shadow-orange-500/20 active:scale-95"
        >
            <Hammer size={14} /> 
            <span className="hidden sm:inline">Forgia</span>
        </button>

        {item.is_modifiable && (
          <button
            onClick={(e) => handleRevoke(item, e)}
            disabled={revokeMutation.isPending}
            className="p-2 text-red-400 hover:text-red-200 hover:bg-red-900/20 rounded-full transition-colors ml-1"
            title="Revoca acquisto"
          >
            <Trash2 size={18} />
          </button>
        )}

        <button
            onClick={(e) => {e.stopPropagation(); handleOpenModal(item)}}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-full transition-colors ml-1"
        >
            <Info size={18} />
        </button>
      </li>
    );
  };

  // Render Elemento Lista (Acquistabile)
  const renderAcquirableItem = (item) => {
    const iconUrl = item.aura_richiesta?.icona_url;
    const iconColor = item.aura_richiesta?.colore;
    
    const costoPieno = item.costo_pieno ?? (item.costo_crediti || item.livello * 100);
    const costoEffettivo = item.costo_effettivo ?? costoPieno;
    const hasDiscount = costoEffettivo < costoPieno;
    const canAfford = char.crediti >= costoEffettivo;

    return (
      <li className="flex flex-col sm:flex-row sm:items-center justify-between py-3 px-2 hover:bg-gray-700/50 transition-colors rounded-sm border-b border-gray-700/50 last:border-0 gap-2">
        <div className="flex items-center gap-3 cursor-pointer grow" onClick={() => handleOpenModal(item)}>
            <div className="shrink-0 mt-0.5 relative">
                <IconaPunteggio url={iconUrl} color={iconColor} mode="cerchio_inv" size="xs" />
                <span className="absolute -top-2 -right-2 bg-gray-900 text-gray-200 text-[9px] font-bold px-1 py-0.5 rounded-full border border-gray-600 leading-none">
                    L{item.livello}
                </span>
            </div>
            
            <div className="flex flex-col">
                <span className="font-bold text-gray-200 text-base">{item.nome}</span>
                <div className="text-xs text-gray-400 flex gap-2 mt-0.5 sm:hidden">
                    {hasDiscount ? (
                        <div className="flex items-center gap-1">
                             <span className="text-red-500 line-through decoration-red-500 opacity-70">{costoPieno}</span>
                             <span className={canAfford ? "text-green-400 font-bold" : "text-red-400 font-bold"}>{costoEffettivo} CR</span>
                        </div>
                    ) : (
                        <span className={canAfford ? "text-yellow-300" : "text-red-400"}>{costoEffettivo} CR</span>
                    )}
                </div>
            </div>
        </div>

        <div className="flex items-center justify-end gap-3 w-full sm:w-auto">
            <div className="hidden sm:flex flex-col items-end text-xs font-mono mr-1">
                {hasDiscount ? (
                    <div className="flex flex-col items-end leading-none mt-1">
                        <span className="text-[10px] text-red-500 line-through decoration-red-500 opacity-80">{costoPieno}</span>
                        <span className="text-green-400 font-bold">{costoEffettivo} CR</span>
                    </div>
                ) : (
                    <span className={canAfford ? "text-yellow-300" : "text-red-400 font-bold"}>{costoEffettivo} CR</span>
                )}
            </div>

            <button
                onClick={(e) => handleAcquire(item, e)}
                disabled={!canAfford || acquireMutation.isPending}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold transition-all shadow-md ml-auto sm:ml-0 ${
                    canAfford 
                    ? 'bg-indigo-600 hover:bg-indigo-500 text-white hover:shadow-indigo-500/20' 
                    : 'bg-gray-700 text-gray-500 cursor-not-allowed opacity-50'
                }`}
            >
                {acquireMutation.isPending ? (
                    <Loader2 className="animate-spin" size={16} />
                ) : (
                    <>
                        <ShoppingCart size={16} />
                        <span className="hidden sm:inline">Apprendi</span>
                    </>
                )}
            </button>
            
            <button
                onClick={(e) => {e.stopPropagation(); handleOpenModal(item)}}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-full transition-colors"
            >
                <Info size={18} />
            </button>
        </div>
      </li>
    );
  };

  const PossessedList = (
      <GenericGroupedList 
        items={possessed} 
        groupByKey="aura_richiesta"
        orderKey="ordine"
        titleKey="nome"
        colorKey="colore"
        iconKey="icona_url"
        renderItem={renderPossessedItem}
        renderHeader={renderGroupHeader}
        itemSortFn={(a, b) => a.livello - b.livello} 
      />
  );

  const AcquirableList = (
      <GenericGroupedList 
        items={acquirable} 
        groupByKey="aura_richiesta"
        orderKey="ordine"
        titleKey="nome"
        colorKey="colore"
        iconKey="icona_url"
        renderItem={renderAcquirableItem}
        renderHeader={renderGroupHeader}
        itemSortFn={(a, b) => a.livello - b.livello}
      />
  );

  return (
    <>
      <div className="w-full p-4 max-w-6xl mx-auto pb-24">
        {/* Header Crediti */}
        <div className="mb-4 flex justify-between items-center bg-gray-800 p-3 rounded-lg border border-gray-700 shadow-sm max-w-3xl mx-auto">
            <div className="text-sm text-gray-400">Disponibilità:</div>
            <div className="flex gap-4">
                <div className="flex items-center gap-1 text-yellow-400 font-bold">
                    <span>{char.crediti}</span> <span className="text-xs font-normal text-gray-400">CR</span>
                </div>
            </div>
        </div>

        {/* Coda di Forgiatura Attiva */}
        <div className="max-w-3xl mx-auto">
            <ForgingQueue queue={forgingQueue} refetchQueue={refetchQueue} />
        </div>

        {/* Bottone Gestione Proposte */}
        <div className="flex justify-end mb-6 max-w-3xl mx-auto">
            <button 
                onClick={() => setShowProposals(true)}
                className="flex items-center gap-2 bg-gray-800 hover:bg-gray-700 text-indigo-300 hover:text-white px-4 py-2 rounded-lg border border-gray-600 transition-all shadow-sm text-sm font-medium"
            >
                <FileEdit size={16} />
                Gestisci Proposte Infusione
            </button>
        </div>

        {/* Visualizzazione Mobile (Tabs) */}
        <div className="md:hidden">
            <Tab.Group>
              <Tab.List className="flex space-x-1 rounded-xl bg-gray-800/80 p-1 mb-6 shadow-inner">
                {['Possedute', 'Nuove'].map((category, idx) => (
                  <Tab as={Fragment} key={category}>
                    {({ selected }) => (
                      <button className={classNames(
                          'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                          selected ? 'bg-indigo-600 text-white shadow' : 'text-gray-400 hover:bg-gray-700/50 hover:text-white'
                      )}>
                        {category} <span className="ml-1 opacity-60 text-xs">
                            ({idx === 0 ? possessed.length : acquirable.length})
                        </span>
                      </button>
                    )}
                  </Tab>
                ))}
              </Tab.List>
              <Tab.Panels>
                <Tab.Panel className="focus:outline-none animate-fadeIn">{PossessedList}</Tab.Panel>
                <Tab.Panel className="focus:outline-none animate-fadeIn">{AcquirableList}</Tab.Panel>
              </Tab.Panels>
            </Tab.Group>
        </div>

        {/* Visualizzazione Desktop (Griglia) */}
        <div className="hidden md:grid grid-cols-2 gap-6">
            <div>
                <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-700">
                    <CheckCircle2 className="w-6 h-6 text-green-500" />
                    <h2 className="text-xl font-bold text-white">
                        Infusioni Possedute 
                        <span className="ml-2 text-sm font-normal text-gray-400">({possessed.length})</span>
                    </h2>
                </div>
                {PossessedList}
            </div>
            <div>
                <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-700">
                    <PlusCircle className="w-6 h-6 text-indigo-500" />
                    <h2 className="text-xl font-bold text-white">
                        Nuove Infusioni
                        <span className="ml-2 text-sm font-normal text-gray-400">({acquirable.length})</span>
                    </h2>
                </div>
                {AcquirableList}
            </div>
        </div>
      </div>
      
      {/* Modale Dettagli Infusione */}
      {modalItem && (
        <TecnicaDetailModal tecnica={modalItem} type="Infusione" onClose={() => setModalItem(null)} />
      )}

      {/* Modale Gestione Proposte */}
      {showProposals && (
        <ProposalManager type="Infusione" onClose={() => setShowProposals(false)} />
      )}

      {/* Modale Forgiatura Avanzata (NUOVA) */}
      {selectedInfusioneForgia && (
        <ForgingModal 
            infusione={selectedInfusioneForgia}
            onClose={() => setSelectedInfusioneForgia(null)}
            onRefresh={onForgingStarted}
        />
      )}
    </>
  );
};

export default InfusioniTab;