import React, { useState, Fragment, useMemo, useCallback, useEffect } from 'react';
import { Tab } from '@headlessui/react';
import { useCharacter } from './CharacterContext';
import { Loader2, ShoppingCart, Info, CheckCircle2, PlusCircle, Trash2, Clock } from 'lucide-react'; 
import AbilitaDetailModal from './AbilitaDetailModal.jsx';
import GenericGroupedList from './GenericGroupedList';
import PunteggioDisplay from './PunteggioDisplay';     
import IconaPunteggio from './IconaPunteggio';
import { useOptimisticAcquireAbilita, useRevokeAbilita } from '../hooks/useGameData';         

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const AbilitaTab = ({ onLogout }) => {
  const {
    selectedCharacterData: char,
    selectedCharacterId, 
    acquirableSkills,     
    isLoadingAcquirable,  
    isLoadingDetail,
    refreshCharacterData,
  } = useCharacter();
  
  const [modalSkill, setModalSkill] = useState(null);
  const [nowTs, setNowTs] = useState(() => Date.now());
  const acquireMutation = useOptimisticAcquireAbilita();
  const revokeMutation = useRevokeAbilita();

  const handleOpenModal = useCallback((skill) => setModalSkill(skill), []);
  useEffect(() => {
    const timer = window.setInterval(() => setNowTs(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, []);

  const handleAcquire = useCallback(async (skill, e) => {
    e.stopPropagation(); 
    if (acquireMutation.isPending || !selectedCharacterId) return;
    
    const pcCostString = skill.costo_pc_calc > 0 ? `${skill.costo_pc_calc} PC` : '';
    const creditCostString = skill.costo_crediti_calc > 0 ? `${skill.costo_crediti_calc} Crediti` : '';
    const joiner = pcCostString && creditCostString ? ' e ' : '';
    
    const confirmMessage = `Sei sicuro di voler acquisire "${skill.nome}" per ${pcCostString}${joiner}${creditCostString}?`;
    
    if (!window.confirm(confirmMessage)) {
      return;
    }
    
    try {
      await acquireMutation.mutateAsync({ 
        abilitaId: skill.id, 
        charId: selectedCharacterId 
      });
      // Refetch in background per allineare i dati reali lato server.
      refreshCharacterData();
    } catch (error) {
      console.error("Errore acquisto:", error);
      alert(`Errore durante l'acquisto: ${error.message}`);
    }
  }, [acquireMutation, selectedCharacterId, refreshCharacterData]);

  const handleRevoke = useCallback(
    async (skill, e) => {
      e.stopPropagation();
      if (revokeMutation.isPending || !selectedCharacterId) return;
      if (!window.confirm(`Revocare l'acquisto di "${skill.nome}"? PC e Crediti verranno restituiti.`)) return;
      try {
        await revokeMutation.mutateAsync({
          abilitaId: skill.id,
          charId: selectedCharacterId,
          onLogout,
        });
        // Refetch in background per allineare i dati reali lato server.
        refreshCharacterData();
      } catch (error) {
        alert(`Errore: ${error.message}`);
      }
    },
    [revokeMutation, selectedCharacterId, onLogout, refreshCharacterData]
  );

  const runtimeAbilityIds = useMemo(() => {
    const ids = new Set();
    (char?.tessiture_attive_runtime || []).forEach((rt) => {
      if (rt?.abilita_temporanea) ids.add(String(rt.abilita_temporanea));
    });
    return ids;
  }, [char?.tessiture_attive_runtime]);

  const temporaryAbilities = useMemo(() => {
    const byId = new Map((char?.abilita_possedute || []).map((s) => [String(s.id), s]));
    return (char?.tessiture_attive_runtime || [])
      .filter((rt) => !!rt?.abilita_temporanea)
      .map((rt) => {
        const skill = byId.get(String(rt.abilita_temporanea));
        const fallbackSeconds = Number(rt?.secondi_rimanenti || 0);
        const seconds = rt?.fine
          ? Math.max(0, Math.floor((new Date(rt.fine).getTime() - nowTs) / 1000))
          : fallbackSeconds;
        const mm = String(Math.floor(seconds / 60)).padStart(2, '0');
        const ss = String(seconds % 60).padStart(2, '0');
        return {
          id: String(rt.id),
          nome: skill?.nome || rt?.abilita_temporanea_nome || 'Abilita temporanea',
          tessituraNome: rt?.tessitura_nome || 'Tessitura',
          descrizioneHtml:
            skill?.testo_formattato_personaggio ||
            skill?.TestoFormattato ||
            skill?.descrizione ||
            skill?.testo ||
            '<em>Nessuna descrizione disponibile.</em>',
          countdown: `${mm}:${ss}`,
        };
      });
  }, [char?.abilita_possedute, char?.tessiture_attive_runtime, nowTs]);

  // Rimuovi i tratti d'aura. Le abilita "nascoste" si vedono solo se sono temporanee attive.
  const possessedSkills = useMemo(
    () =>
      (char?.abilita_possedute || []).filter(
        (s) =>
          !s?.is_tratto_aura &&
          !runtimeAbilityIds.has(String(s?.id)) &&
          !s?.nascondi_in_scheda_abilita
      ),
    [char?.abilita_possedute, runtimeAbilityIds]
  );

  // --- FILTRO MODIFICA: Rimuovo i tratti speciali e le abilità nascoste dalla lista acquistabili ---
  // Questi verranno gestiti tramite il modale in PunteggioDisplay
  const filteredAcquirableSkills = useMemo(() => 
    acquirableSkills 
      ? acquirableSkills.filter(
          (skill) => !skill.is_tratto_aura && !skill.nascondi_in_scheda_abilita
        )
      : [],
    [acquirableSkills]
  );
  // --------------------------------------------------------------------------

  if (isLoadingAcquirable || isLoadingDetail || !char) {
    return (
      <div className="flex justify-center items-center h-64">
        <Loader2 className="animate-spin text-indigo-500" size={48} />
      </div>
    );
  }

  // --- RENDERERS ---

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

  const renderPossessedItem = (skill) => {
    const iconUrl = skill.caratteristica?.icona_url;
    const iconColor = skill.caratteristica?.colore;

    return (
      <li className="flex justify-between items-center py-2 px-2 hover:bg-gray-700/50 transition-colors rounded-sm border-b border-gray-700/50 last:border-0">
        <div 
            className="flex items-center gap-3 cursor-pointer grow" 
            onClick={() => handleOpenModal(skill)}
        >
            <div className="shrink-0 mt-0.5">
                <IconaPunteggio 
                    url={iconUrl}
                    color={iconColor}
                    mode="cerchio_inv"
                    size="xs"
                />
            </div>
            <span className="font-bold text-gray-200 text-base">{skill.nome}</span>
        </div>
        <button
            onClick={() => handleOpenModal(skill)}
            className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-full transition-colors ml-2"
            title="Dettagli"
        >
            <Info size={18} />
        </button>

        {skill.is_modifiable && (
          <button
            onClick={(e) => handleRevoke(skill, e)}
            disabled={revokeMutation.isPending}
            className="p-2 text-red-400 hover:text-red-200 hover:bg-red-900/20 rounded-full transition-colors ml-2"
            title="Revoca acquisto"
          >
            <Trash2 size={18} />
          </button>
        )}
      </li>
    );
  };

  const renderAcquirableItem = (skill) => {
    const canAffordPC = char.punti_caratteristica >= skill.costo_pc_calc;
    const canAffordCrediti = char.crediti >= skill.costo_crediti_calc;
    const canAfford = canAffordPC && canAffordCrediti;
    const isDiscounted = skill.costo_crediti > skill.costo_crediti_calc;
    
    const iconUrl = skill.caratteristica?.icona_url;
    const iconColor = skill.caratteristica?.colore;

    return (
      <li className="flex flex-col sm:flex-row sm:items-center justify-between py-3 px-2 hover:bg-gray-700/50 transition-colors rounded-sm border-b border-gray-700/50 last:border-0 gap-2">
        
        {/* Parte Sinistra */}
        <div 
            className="flex items-center gap-3 cursor-pointer grow"
            onClick={() => handleOpenModal(skill)}
        >
            <div className="shrink-0 mt-0.5">
                <IconaPunteggio 
                    url={iconUrl}
                    color={iconColor}
                    mode="cerchio_inv"
                    size="xs"
                />
            </div>
            <div className="flex flex-col">
                <span className="font-bold text-gray-200 text-base">{skill.nome}</span>
                <div className="text-xs text-gray-400 flex gap-2 mt-0.5 sm:hidden">
                    {skill.costo_pc_calc > 0 && (
                        <span className={canAffordPC ? "text-blue-300" : "text-red-400"}>
                            {skill.costo_pc_calc} PC
                        </span>
                    )}
                    {skill.costo_crediti_calc > 0 && (
                        <span className={canAffordCrediti ? "text-yellow-300" : "text-red-400"}>
                            {skill.costo_crediti_calc} CR
                        </span>
                    )}
                </div>
            </div>
        </div>

        {/* Parte Destra */}
        <div className="flex items-center justify-end gap-3 w-full sm:w-auto">
            <div className="hidden sm:flex flex-col items-end text-xs font-mono mr-1">
                 {skill.costo_pc_calc > 0 && (
                     <span className={canAffordPC ? "text-blue-300" : "text-red-400 font-bold"}>
                        {skill.costo_pc_calc} PC
                     </span>
                 )}

                 {skill.costo_crediti_calc > 0 && (
                     isDiscounted ? (
                        <div className="flex flex-col items-end leading-none mt-1">
                            <span className="text-[10px] text-red-500 line-through decoration-red-500 opacity-80">
                                {skill.costo_crediti}
                            </span>
                            <span className="text-green-400 font-bold">
                                {skill.costo_crediti_calc} CR
                            </span>
                        </div>
                     ) : (
                        <span className={canAffordCrediti ? "text-yellow-300" : "text-red-400 font-bold"}>
                            {skill.costo_crediti_calc} CR
                        </span>
                     )
                 )}
            </div>

            <button
              onClick={(e) => handleAcquire(skill, e)}
              disabled={!canAfford || acquireMutation.isPending}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-bold transition-all shadow-md ml-auto sm:ml-0 ${
                !canAfford 
                  ? 'bg-gray-700 text-gray-500 cursor-not-allowed opacity-50' 
                  : 'bg-indigo-600 hover:bg-indigo-500 text-white hover:shadow-indigo-500/20'
              }`}
            >
              {acquireMutation.isPending ? (
                <Loader2 className="animate-spin" size={16} />
              ) : (
                <>
                    <ShoppingCart size={16} />
                    <span className="hidden sm:inline">Acquista</span>
                </>
              )}
            </button>
            
            <button
                onClick={(e) => { e.stopPropagation(); handleOpenModal(skill); }}
                className="p-2 text-gray-400 hover:text-white hover:bg-gray-600 rounded-full transition-colors"
            >
                <Info size={18} />
            </button>
        </div>
      </li>
    );
  };

  // --- DEFINIZIONE DELLE DUE LISTE ---
  
  const PossessedListComponent = (
    <GenericGroupedList 
      items={possessedSkills} 
      groupByKey="caratteristica"
      orderKey="ordine"
      titleKey="nome"
      colorKey="colore"
      iconKey="icona_url"
      renderItem={renderPossessedItem}
      renderHeader={renderGroupHeader}
      compact={false}
      itemSortFn={(a, b) => a.nome.localeCompare(b.nome)}
    />
  );

  const AcquirableListComponent = (
    <GenericGroupedList 
      // USO LA LISTA FILTRATA QUI
      items={filteredAcquirableSkills} 
      groupByKey="caratteristica"
      orderKey="ordine"
      titleKey="nome"
      colorKey="colore"
      iconKey="icona_url"
      renderItem={renderAcquirableItem}
      renderHeader={renderGroupHeader}
      compact={false}
      itemSortFn={(a, b) => a.nome.localeCompare(b.nome)}
    />
  );

  return (
    <>
      <div className="w-full p-4 max-w-6xl mx-auto pb-24">
        
        {/* Riepilogo Valute (Comune) */}
        <div className="mb-6 flex justify-between items-center bg-gray-800 p-3 rounded-lg border border-gray-700 shadow-sm max-w-3xl mx-auto">
            <div className="text-sm text-gray-400">Disponibilità:</div>
            <div className="flex gap-4">
                <div className="flex items-center gap-1 text-blue-400 font-bold">
                    <span>{char.punti_caratteristica}</span> <span className="text-xs font-normal text-gray-400">PC</span>
                </div>
                <div className="flex items-center gap-1 text-yellow-400 font-bold">
                    <span>{char.crediti}</span> <span className="text-xs font-normal text-gray-400">CR</span>
                </div>
            </div>
        </div>

        {temporaryAbilities.length > 0 && (
          <div className="mb-6 rounded-lg border border-sky-500/50 bg-sky-950/20 p-3 shadow-[0_0_16px_rgba(56,189,248,0.14)]">
            <div className="flex items-center gap-2 text-sky-200 font-bold uppercase tracking-wider text-xs mb-2">
              <Clock size={14} className="text-sky-300" />
              Abilita temporanee
            </div>
            <div className="space-y-2">
              {temporaryAbilities.map((tmp) => (
                <div key={tmp.id} className="rounded-lg border border-sky-500/50 bg-gray-900/50 p-3">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <div className="text-sky-100 font-bold">{tmp.nome}</div>
                      <div className="text-[11px] text-sky-300/80">Origine: {tmp.tessituraNome}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] uppercase tracking-wide text-sky-300">Timer</div>
                      <div className="font-mono text-sky-100">{tmp.countdown}</div>
                    </div>
                  </div>
                  <div
                    className="mt-2 text-xs text-sky-50/90 rounded border border-sky-700/40 bg-sky-950/20 p-2 prose prose-invert prose-sm max-w-none"
                    dangerouslySetInnerHTML={{ __html: tmp.descrizioneHtml }}
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* --- LAYOUT MOBILE: TABS --- */}
        <div className="md:hidden">
            <Tab.Group>
            <Tab.List className="flex space-x-1 rounded-xl bg-gray-800/80 p-1 mb-4 shadow-inner">
                <Tab as={Fragment}>
                {({ selected }) => (
                    <button className={classNames(
                        'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                        'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-indigo-400 ring-white ring-opacity-60',
                        selected 
                            ? 'bg-indigo-600 text-white shadow-lg scale-[1.02]' 
                            : 'text-gray-400 hover:bg-gray-700/50 hover:text-white'
                    )}>
                    Possedute <span className="ml-1 opacity-70 text-xs">({possessedSkills.length})</span>
                    </button>
                )}
                </Tab>
                <Tab as={Fragment}>
                {({ selected }) => (
                    <button className={classNames(
                        'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all',
                        'focus:outline-none focus:ring-2 ring-offset-2 ring-offset-indigo-400 ring-white ring-opacity-60',
                        selected 
                            ? 'bg-indigo-600 text-white shadow-lg scale-[1.02]' 
                            : 'text-gray-400 hover:bg-gray-700/50 hover:text-white'
                    )}>
                    Nuove <span className="ml-1 opacity-70 text-xs">({filteredAcquirableSkills.length})</span>
                    </button>
                )}
                </Tab>
            </Tab.List>
            
            <Tab.Panels>
                <Tab.Panel className="focus:outline-none animate-fadeIn">
                    {PossessedListComponent}
                </Tab.Panel>
                <Tab.Panel className="focus:outline-none animate-fadeIn">
                    {AcquirableListComponent}
                </Tab.Panel>
            </Tab.Panels>
            </Tab.Group>
        </div>

        {/* --- LAYOUT DESKTOP: DUE COLONNE --- */}
        <div className="hidden md:grid grid-cols-2 gap-6">
            
            <div>
                <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-700">
                    <CheckCircle2 className="w-6 h-6 text-green-500" />
                    <h2 className="text-xl font-bold text-white">
                        Abilità Possedute 
                        <span className="ml-2 text-sm font-normal text-gray-400">({possessedSkills.length})</span>
                    </h2>
                </div>
                {PossessedListComponent}
            </div>

            <div>
                <div className="flex items-center gap-2 mb-4 pb-2 border-b border-gray-700">
                    <PlusCircle className="w-6 h-6 text-indigo-500" />
                    <h2 className="text-xl font-bold text-white">
                        Nuove Abilità
                        <span className="ml-2 text-sm font-normal text-gray-400">({filteredAcquirableSkills.length})</span>
                    </h2>
                </div>
                {AcquirableListComponent}
            </div>

        </div>

      </div>
      
      {modalSkill && (
        <AbilitaDetailModal
          skill={modalSkill}
          onClose={() => setModalSkill(null)}
          onLogout={onLogout}
          onPurchaseSuccess={() => {
             setModalSkill(null);
             refreshCharacterData();
          }}
        />
      )}
    </>
  );
};

export default AbilitaTab;