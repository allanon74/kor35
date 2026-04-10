import React, { useState, useEffect, memo, useCallback } from 'react';
import { useCharacter } from './CharacterContext';
import { 
    ShoppingBag, Box, Shield, Zap, Loader2, Wrench, 
    Info, ChevronUp, ChevronDown, Activity, Power, Battery, 
    Clock, RefreshCw, Sparkles, Swords, Lock, User, Backpack, Weight
} from 'lucide-react';
import ShopModal from './ShopModal';
import ItemAssemblyModal from './ItemAssemblyModal';
import ModuloDetailModal from './ModuloDetailModal';
import PunteggioDisplay from './PunteggioDisplay';
import { useOptimisticEquip, useOptimisticRecharge } from '../hooks/useGameData';

// --- UTILS ---
const formatDuration = (seconds) => {
    if (!seconds) return "";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    
    const parts = [];
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    if (s > 0 || parts.length === 0) parts.push(`${s}s`);
    
    return parts.join(' ');
};

const LazyList = ({ items, renderItem, batchSize = 10 }) => {
    const [displayedItems, setDisplayedItems] = useState([]);
    
    useEffect(() => {
        // Reset quando cambiano gli items
        setDisplayedItems(items.slice(0, batchSize));
    }, [items, batchSize]);

    const showMore = () => {
        setDisplayedItems(prev => items.slice(0, prev.length + batchSize));
    };

    return (
        <div className="space-y-2">
            {displayedItems.map(renderItem)}
            
            {displayedItems.length < items.length && (
                <button 
                    onClick={showMore}
                    className="w-full py-3 mt-2 text-sm font-bold text-gray-400 bg-gray-800/50 hover:bg-gray-700 border border-dashed border-gray-600 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                    <ChevronDown size={16} /> Carica altri ({items.length - displayedItems.length})
                </button>
            )}
        </div>
    );
};

// --- COMPONENTE VISUALE CORPO (SVG ORGANICO 8 SLOT) - VARIANTE 1 MOBILE ---
const InventoryBodyWidget = ({ slots, onSlotClick, selectedItemId }) => {
    const paths = {
        'HD1': { d: "M85,15 C85,10 90,5 100,5 C110,5 115,10 115,15 C115,22 110,28 100,28 C90,28 85,22 85,15 Z", name: "Cranio (HD1)" },
        'HD2': { d: "M85,15 C85,22 90,28 100,28 C110,28 115,22 115,15 C115,25 112,38 100,42 C88,38 85,25 85,15 Z", name: "Volto (HD2)" },
        'TR1': { d: "M68,58 L68,100 L94,106 L106,106 L132,100 L132,58 L116,52 L84,52 Z", name: "Torace (TR1)" },
        'TR2': { d: "M68,100 L74,155 L88,162 L112,162 L126,155 L132,100 Z", name: "Addome (TR2)" },
        'LA': { d: "M68,58 L58,64 L50,82 L46,105 L44,130 L43,158 L46,162 L54,160 L56,130 L60,105 L66,76 Z", name: "Braccio Sx (LA)" },
        'RA': { d: "M132,58 L142,64 L150,82 L154,105 L156,130 L157,158 L154,162 L146,160 L144,130 L140,105 L134,76 Z", name: "Braccio Dx (RA)" },
        'LL': { d: "M74,155 L70,200 L68,255 L66,300 L74,306 L84,306 L86,300 L88,255 L90,200 L88,162 Z", name: "Gamba Sx (LL)" },
        'RL': { d: "M126,155 L130,200 L132,255 L134,300 L126,306 L116,306 L114,300 L112,255 L110,200 L112,162 Z", name: "Gamba Dx (RL)" }
    };

    return (
        <div className="relative w-full max-w-[280px] mx-auto drop-shadow-xl select-none">
            <svg viewBox="0 0 200 330" className="w-full h-auto filter drop-shadow-lg">
                <defs>
                    <filter id="glow-selected" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="2" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                </defs>
                
                {/* Collo (non cliccabile, solo visivo) */}
                <rect x="88" y="42" width="24" height="16" rx="4" fill="#1f2937" stroke="#374151" strokeWidth="1.5" opacity="0.5"/>
                
                {/* Shadow layer */}
                <g opacity="0.2">
                     {Object.values(paths).map((p, i) => <path key={i} d={p.d} fill="#1f2937" stroke="none" />)}
                </g>
                
                {Object.entries(paths).map(([code, { d, name }]) => {
                    const item = slots[code] && slots[code][0];
                    const isOccupied = !!item;
                    const isSelected = item && item.id === selectedItemId;
                    const auraColor = item?.aura?.colore || '#4b5563'; 
                    const fillColor = isOccupied ? auraColor : 'transparent';
                    const strokeColor = isOccupied ? (isSelected ? '#ffffff' : 'rgba(255,255,255,0.6)') : '#374151';
                    const opacity = isOccupied ? (isSelected ? 1 : 0.7) : 0.1;
                    const cursor = isOccupied ? 'cursor-pointer' : 'cursor-default';
                    const filter = isSelected ? 'url(#glow-selected)' : '';
                    const strokeW = isSelected ? '2.5px' : '2px';

                    return (
                        <g key={code} onClick={() => isOccupied && onSlotClick(item)} className={`transition-all duration-300 ${cursor}`}>
                            <path 
                                d={d} 
                                fill={fillColor} 
                                stroke={strokeColor} 
                                strokeWidth={strokeW}
                                fillOpacity={opacity} 
                                filter={filter} 
                                strokeLinejoin="round" 
                                className={`transition-all duration-300 ${isOccupied ? 'hover:fill-opacity-100 hover:stroke-white' : ''}`}
                                onMouseEnter={(e) => isOccupied && (e.currentTarget.style.strokeWidth = '3px')}
                                onMouseLeave={(e) => isOccupied && (e.currentTarget.style.strokeWidth = strokeW)}
                            />
                            <title>{name} {isOccupied ? `: ${item.nome}` : '(Vuoto)'}</title>
                        </g>
                    );
                })}
            </svg>
        </div>
    );
};

// --- COMPONENTE CARD INVENTARIO (MEMOIZED PER PERFORMANCE) ---
// Usa memo per evitare re-render dell'intera lista quando cambia lo stato di un solo elemento
const InventoryItemCard = memo(({ item, isExpanded, onToggleExpand, onEquip, onRecharge, onAssembly, onModuloClick }) => {
    const isPhysical = item.tipo_oggetto === 'FIS';
    const canBeModified = (isPhysical || ['INN', 'MUT'].includes(item.tipo_oggetto)) && (item.classe_oggetto_nome || item.tipo_oggetto === 'INN');
    const isActive = item.is_active;

    // Render Statistiche (Solo != 0)
    const renderStats = (statistiche) => {
        if (!statistiche || statistiche.length === 0) return null;
        // Filtra statistiche con valore 0 (inutile mostrarle come +0)
        const activeStats = statistiche.filter(s => s.valore !== 0);
        if (activeStats.length === 0) return null;

        return (
            <div className="flex flex-wrap gap-2 mt-2">
                {activeStats.map((stat, idx) => {
                    // Costruisce la condizione se presente
                    const hasCondition = stat.usa_limitazione_aura || stat.usa_limitazione_elemento || stat.usa_condizione_text;
                    const conditionTitle = stat.condizione_text || "Condizionale";
                    
                    return (
                        <div key={idx} className="flex items-center bg-gray-900 border border-gray-600 rounded px-2 py-1 text-xs shadow-sm">
                            <span className="font-bold text-gray-300 mr-1">{stat.statistica.nome}</span>
                            <span className={`font-mono font-bold ${stat.valore > 0 ? 'text-green-400' : 'text-red-400'}`}>
                                {stat.valore > 0 ? '+' : ''}{stat.valore}
                            </span>
                            {hasCondition && (
                                <div className="ml-1 text-amber-500" title={conditionTitle}>
                                    <Lock size={10} />
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        );
    };

    // Render Componenti (Mattoni) con PunteggioDisplay
    const renderComponents = (componenti) => {
        if (!componenti || componenti.length === 0) return null;
        return (
            <div className="flex flex-wrap gap-1 items-center justify-end">
                {componenti.map((comp, idx) => {
                    if (!comp.caratteristica) return null;
                    return (
                        <PunteggioDisplay
                            key={idx}
                            punteggio={comp.caratteristica}
                            value={comp.valore || 1}
                            displayText="abbr"
                            iconType="inv_circle"
                            size="badge"
                            readOnly={true}
                            className="shrink-0"
                        />
                    );
                })}
            </div>
        );
    };

    // Render Info Cariche
    const renderChargeInfo = () => {
        if (!item.cariche_massime && !item.durata_totale) return null;
        const isLow = item.cariche_attuali === 0;

        return (
            <div className="mt-2 bg-black/20 p-2 rounded border border-gray-600/50 flex flex-col gap-1">
                <div className="flex justify-between items-center text-xs">
                    <div className="flex items-center gap-2">
                        <span className={`flex items-center gap-1 font-bold ${isLow ? 'text-red-500' : 'text-yellow-500'}`}>
                            <Battery size={14} /> 
                            <span className="text-sm">{item.cariche_attuali}</span> 
                            <span className="text-gray-500">/</span> 
                            <span>{item.cariche_massime || '-'}</span>
                        </span>
                    </div>
                    {(item.cariche_massime > 0 && item.cariche_attuali < item.cariche_massime) && (
                        <button 
                            onClick={(e) => { e.stopPropagation(); onRecharge(item); }}
                            className="flex items-center gap-1 px-2 py-0.5 bg-yellow-900/50 hover:bg-yellow-800 text-yellow-200 border border-yellow-700 rounded text-[10px] uppercase font-bold tracking-wide transition-colors"
                        >
                            <RefreshCw size={10} /> {item.costo_ricarica} CR
                        </button>
                    )}
                </div>
                {item.durata_totale > 0 && (
                    <div className="text-[10px] text-blue-300 flex items-center gap-1 border-t border-gray-700/50 pt-1 mt-1">
                        <Clock size={10} /> Durata: {formatDuration(item.durata_totale)}
                    </div>
                )}
            </div>
        );
    };

    const getStatusStyle = () => {
        if (isActive) return 'border-2 border-green-500 shadow-[0_0_15px_rgba(34,197,94,0.2)] bg-green-900/10';
        if (item.is_equipaggiato) return 'border-2 border-yellow-600/60 bg-yellow-900/10'; 
        return 'border border-gray-700 bg-gray-800 hover:border-gray-600'; 
    };

    return (
        <div className={`relative p-3 mb-3 rounded-lg flex flex-col transition-all ${getStatusStyle()}`}>
            
            {/* HEADER CARD */}
            <div className="flex items-start justify-between cursor-pointer" onClick={() => onToggleExpand(item.id)}>
                <div className="flex items-center gap-3 w-full">
                    {/* Icona Aura con PunteggioDisplay */}
                    {item.aura ? (
                        <div className="shrink-0 flex items-center" title={item.aura.nome || "Oggetto"}>
                            <PunteggioDisplay
                                punteggio={item.aura}
                                value={null}
                                displayText="none"
                                iconType="inv_circle"
                                size="s"
                                readOnly={true}
                            />
                        </div>
                    ) : (
                        <div className="w-10 h-10 rounded bg-gray-900 border border-gray-600 flex items-center justify-center shrink-0 overflow-hidden shadow-inner" title="Oggetto">
                            <Sparkles size={20} color="#888"/>
                        </div>
                    )}
                    
                    <div className="flex flex-col w-full">
                        <div className="flex items-center justify-between w-full">
                            <h4 className={`font-bold text-sm sm:text-base leading-tight ${isActive ? 'text-green-400' : item.is_equipaggiato ? 'text-yellow-500' : 'text-gray-200'}`}>
                                {item.nome}
                            </h4>
                            
                            {/* Componenti (Mattoni) in alto a destra */}
                            <div className="ml-auto flex items-center">
                                {renderComponents(item.componenti)}
                                {/* Livello Badge */}
                                {item.livello > 0 && (
                                    <span className="ml-2 text-[9px] bg-gray-700 text-gray-300 px-1.5 py-0.5 rounded border border-gray-600 font-mono shrink-0">
                                        Lv.{item.livello}
                                    </span>
                                )}
                            </div>
                        </div>
                        
                        <div className="flex justify-between items-center mt-1">
                            <div className="text-[10px] text-gray-500 uppercase tracking-wider flex gap-2">
                                <span>{item.tipo_oggetto_display}</span>
                                {item.classe_oggetto_nome && <span>• {item.classe_oggetto_nome}</span>}
                            </div>
                            
                            {/* Icona Espandi */}
                            <div className="text-gray-500">
                                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            {/* EXPANDED CONTENT */}
            {isExpanded && (
                <div className="mt-3 animate-fadeIn space-y-3 border-t border-gray-700/50 pt-2">
                    
                    {/* Attacco Base */}
                    {item.attacco_formattato && (
                        <div className="bg-red-900/20 border border-red-900/40 p-2 rounded flex items-center gap-2 text-red-300 text-xs font-bold shadow-inner">
                            <Swords size={14} />
                            <span>ATTACCO: {item.attacco_formattato}</span>
                        </div>
                    )}

                    {/* Statistiche Base e Modificatori */}
                    {renderStats(item.statistiche)}

                    {/* Descrizione */}
                    <div className="text-xs text-gray-300 prose prose-invert prose-sm max-w-none leading-relaxed bg-black/10 p-2 rounded border border-gray-700/30">
                         <div dangerouslySetInnerHTML={{ __html: item.testo_formattato_personaggio || item.testo || item.descrizione || "Nessun dato disponibile." }} />
                         {item.data_fine_attivazione && (
                             <div className="mt-2 pt-2 border-t border-gray-700 text-[10px] text-orange-400 font-mono text-right">
                                 Scade: {new Date(item.data_fine_attivazione).toLocaleString()}
                             </div>
                         )}
                    </div>

                    {/* Info Cariche */}
                    {renderChargeInfo()}

                    {/* Potenziamenti Installati */}
                    {item.potenziamenti_installati && item.potenziamenti_installati.length > 0 && (
                        <div className="pl-2 border-l-2 border-indigo-500/30 mt-2 bg-indigo-900/5 p-2 rounded">
                            <p className="text-[10px] font-bold text-indigo-400 uppercase mb-2 flex items-center gap-1">
                                <Zap size={12} /> Moduli Installati:
                            </p>
                            <div className="space-y-2">
                                {item.potenziamenti_installati.map(mod => (
                                    <div key={mod.id} className={`p-2 rounded border text-xs ${mod.is_active !== false ? 'bg-indigo-900/20 border-indigo-500/20' : 'bg-red-900/10 border-red-900/30 opacity-70'}`}>
                                        <div className="flex justify-between items-start mb-1">
                                            <div className="flex flex-col">
                                                <button
                                                    onClick={(e) => { e.stopPropagation(); onModuloClick && onModuloClick(mod.id); }}
                                                    className="font-bold text-indigo-200 hover:text-indigo-100 text-left underline decoration-dotted decoration-indigo-400/50 hover:decoration-solid transition-all"
                                                    title="Clicca per vedere i dettagli completi"
                                                >
                                                    {mod.nome}
                                                </button>
                                                <span className="text-[9px] text-gray-500">{mod.tipo_oggetto_display}</span>
                                            </div>
                                            {/* Icone componenti mod */}
                                            {renderComponents(mod.componenti)}
                                        </div>
                                        {/* Statistiche Mod */}
                                        {renderStats(mod.statistiche)}
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                    
                    {/* Bottoni Azione */}
                    <div className="flex gap-2 mt-2 pt-2 border-t border-gray-700/30">
                        {canBeModified && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onAssembly(item); }}
                                className="flex-1 py-2 rounded text-xs font-bold bg-gray-700 hover:bg-gray-600 text-amber-400 border border-gray-600 flex items-center justify-center gap-2 shadow-sm"
                            >
                                <Wrench size={14} /> Modifica
                            </button>
                        )}
                        {isPhysical && (
                            <button 
                                onClick={(e) => { e.stopPropagation(); onEquip(item.id); }}
                                className={`flex-1 py-2 rounded text-xs font-bold transition-all active:scale-95 flex items-center justify-center gap-2 shadow-sm ${
                                    item.is_equipaggiato
                                    ? 'bg-red-900/80 hover:bg-red-800 text-red-100 border border-red-700'
                                    : 'bg-emerald-700 hover:bg-emerald-600 text-white border border-emerald-600'
                                }`}
                            >
                                {item.is_equipaggiato ? <><Power size={14}/> Rimuovi</> : <><Shield size={14}/> Equipaggia</>}
                            </button>
                        )}
                    </div>

                </div>
            )}
        </div>
    );
});

// --- CAPACITY DASHBOARD ---
const CapacityDashboard = ({ capacityUsed, capacityMax, capacityConsumers, heavyUsed, heavyMax, heavyConsumers }) => {
    const isOverloaded = capacityUsed > capacityMax;
    const isHeavyOverloaded = heavyUsed > heavyMax;

    return (
        <div className="w-full bg-gray-800 rounded-xl border border-gray-700 p-3 shadow-md mb-4 flex flex-col md:flex-row gap-4">
            <div className={`flex-1 flex flex-col gap-2 p-2 rounded-lg border bg-gray-900/30 ${isOverloaded ? 'border-red-500/50 bg-red-900/10' : 'border-gray-700/50'}`}>
                <div className="flex justify-between items-center border-b border-gray-700/50 pb-1">
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2"><Backpack size={12} className="text-indigo-400"/> Oggetti Speciali (COG)</span>
                    <span className={`text-xs font-bold font-mono ${isOverloaded ? 'text-red-400' : 'text-indigo-400'}`}>{capacityUsed} / {capacityMax}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                    {capacityConsumers.length > 0 ? capacityConsumers.map((item) => (
                        <div key={item.id} className="flex items-center gap-1.5 bg-gray-800 px-2 py-1 rounded border border-gray-600 shadow-sm"><div className="w-1.5 h-1.5 rounded-full bg-indigo-500 shrink-0"></div><span className="text-[10px] text-gray-300 truncate font-mono max-w-[120px]">{item.nome}</span></div>
                    )) : <span className="text-[10px] text-gray-600 italic px-1">Nessuno</span>}
                </div>
            </div>
            <div className={`flex-1 flex flex-col gap-2 p-2 rounded-lg border bg-gray-900/30 ${isHeavyOverloaded ? 'border-orange-500/50 bg-orange-900/10' : 'border-gray-700/50'}`}>
                <div className="flex justify-between items-center border-b border-gray-700/50 pb-1">
                    <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2"><Weight size={12} className="text-orange-400"/> Oggetti Pesanti (OGP)</span>
                    <span className={`text-xs font-bold font-mono ${isHeavyOverloaded ? 'text-orange-400' : 'text-green-400'}`}>{heavyUsed} / {heavyMax}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                    {heavyConsumers.length > 0 ? heavyConsumers.map((item) => (
                        <div key={item.id} className="flex items-center gap-1.5 bg-gray-800 px-2 py-1 rounded border border-gray-600 shadow-sm"><div className="w-1.5 h-1.5 rounded-full bg-orange-500 shrink-0"></div><span className="text-[10px] text-gray-300 truncate font-mono max-w-[120px]">{item.nome}</span></div>
                    )) : <span className="text-[10px] text-gray-600 italic px-1">Carico leggero</span>}
                </div>
            </div>
        </div>
    );
};

// --- MAIN INVENTORY TAB ---
const InventoryTab = ({ onLogout }) => {
  const { selectedCharacterData: characterData, isLoading: isContextLoading } = useCharacter();
  
  const [items, setItems] = useState([]);
  const [showShop, setShowShop] = useState(false);
  const [showAssembly, setShowAssembly] = useState(false);
  const [assemblyHost, setAssemblyHost] = useState(null);
  const [selectedBodyItem, setSelectedBodyItem] = useState(null);
  const [expandedItems, setExpandedItems] = useState({});
  const [showModuloDetail, setShowModuloDetail] = useState(false);
  const [selectedModuloId, setSelectedModuloId] = useState(null);

  const equipMutation = useOptimisticEquip();
  const rechargeMutation = useOptimisticRecharge();

  useEffect(() => {
    if (characterData?.oggetti) setItems(characterData.oggetti);
    else setItems([]);
  }, [characterData]);

  const handleToggleEquip = (itemId) => equipMutation.mutate({ itemId, charId: characterData.id });

  const handleRecharge = (item) => {
      const costo = item.costo_ricarica || 0;
      const metodo = item.testo_ricarica || "Standard";
      if (window.confirm(`Ricaricare ${item.nome}?\nCosto: ${costo} CR\nMetodo: ${metodo}`)) {
          rechargeMutation.mutate({ oggetto_id: item.id, charId: characterData.id });
      }
  };

  const handleOpenAssembly = (item) => { setAssemblyHost(item); setShowAssembly(true); };
  const handleAssemblyComplete = () => { setShowAssembly(false); setAssemblyHost(null); };
  
  const handleModuloClick = (moduloId) => {
      setSelectedModuloId(moduloId);
      setShowModuloDetail(true);
  };
  
  // Toggle ottimizzato
  const toggleExpand = useCallback((itemId) => {
      setExpandedItems(prev => ({ ...prev, [itemId]: !prev[itemId] }));
  }, []);

  if (isContextLoading) return <div className="p-8 text-center text-gray-500 flex justify-center"><Loader2 className="animate-spin" /></div>;
  if (!characterData) return <div className="p-4 text-center text-red-400">Nessun personaggio selezionato.</div>;

  const corpoItems = items.filter(i => ['INN', 'MUT'].includes(i.tipo_oggetto));
  const equipItems = items.filter(i => i.is_equipaggiato && i.tipo_oggetto === 'FIS');
  const zainoItems = items.filter(i => !i.is_equipaggiato && !['INN', 'MUT'].includes(i.tipo_oggetto));

  // Calcolo Capacità Oggetti
  const statCog = characterData?.statistiche_primarie?.find(s => s.sigla === 'COG');
  const capacityMax = statCog ? statCog.valore_max : 10;
  const capacityConsumers = items.filter(i => i.is_equipaggiato && i.tipo_oggetto === 'FIS');
  const capacityUsed = capacityConsumers.length;
  
  const statOgp = characterData?.statistiche_primarie?.find(s => s.sigla === 'OGP');
  const heavyMax = statOgp ? statOgp.valore_max : 0;
  const heavyConsumers = items.filter(i => i.is_equipaggiato && i.is_pesante);
  const heavyUsed = heavyConsumers.length;

  // Render Helper per liste (utilizza il componente Memoizzato)
    const renderList = (list) => (
        <LazyList 
            items={list} 
            batchSize={10} // Carica 10 elementi alla volta per fluidità immediata
            renderItem={(item) => (
                <InventoryItemCard 
                    key={item.id} 
                    item={item} 
                    isExpanded={!!expandedItems[item.id]}
                    onToggleExpand={toggleExpand}
                    onEquip={handleToggleEquip}
                    onRecharge={handleRecharge}
                    onAssembly={handleOpenAssembly}
                    onModuloClick={handleModuloClick}
                />
            )}
        />
    );
  
  const slots = {};
  const genericItems = [];
  corpoItems.forEach(item => {
      if (item.slot_corpo) {
          if (!slots[item.slot_corpo]) slots[item.slot_corpo] = [];
          slots[item.slot_corpo].push(item);
      } else genericItems.push(item);
  });

  return (
    <div className="pb-24 px-1 space-y-6 animate-fadeIn">
      <div className="flex justify-between items-center p-3 rounded-lg border border-gray-700 shadow-sm mb-4 sticky top-0 z-20 backdrop-blur-md bg-gray-800/90">
         <h2 className="text-xl font-bold text-white flex items-center gap-2"><Box className="text-indigo-400" /> Inventario</h2>
         <button onClick={() => setShowShop(true)} className="flex items-center gap-2 bg-yellow-600 hover:bg-yellow-500 text-white px-3 py-1.5 rounded-lg font-bold shadow-lg shadow-yellow-900/20 transition-all active:scale-95 text-xs sm:text-sm border border-yellow-500">
            <ShoppingBag size={16} /><span>Negozio</span>
         </button>
      </div>

      <CapacityDashboard 
        capacityUsed={capacityUsed} 
        capacityMax={capacityMax} 
        capacityConsumers={capacityConsumers}
        heavyUsed={heavyUsed} 
        heavyMax={heavyMax} 
        heavyConsumers={heavyConsumers}
      />

      <section>
        <h3 className="text-sm font-bold text-indigo-300 mb-3 flex items-center gap-2 uppercase tracking-wider pl-1"><Activity size={16} /> Diagnostica Corporea</h3>
        {corpoItems.length > 0 ? (
            <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700 mb-6 flex flex-col md:flex-row items-center md:items-start gap-6">
                <div className="w-full md:w-1/3 flex flex-col items-center">
                    <InventoryBodyWidget slots={slots} onSlotClick={setSelectedBodyItem} selectedItemId={selectedBodyItem?.id} />
                    <p className="text-xs text-gray-500 mt-2 text-center italic">Clicca sulle zone colorate per i dettagli</p>
                </div>
                <div className="w-full md:w-2/3 flex flex-col gap-4">
                    <div className={`transition-all duration-300 origin-top ${selectedBodyItem ? 'opacity-100 scale-100' : 'opacity-0 scale-95 h-0 overflow-hidden'}`}>
                        {selectedBodyItem && (
                            <div className="bg-gray-800/80 border border-indigo-500/50 rounded-lg p-2 shadow-lg shadow-indigo-900/20 relative animate-fadeIn">
                                <div className="absolute top-2 right-2 z-10">
                                    <button onClick={() => setSelectedBodyItem(null)} className="text-gray-400 hover:text-white bg-gray-900 rounded-full p-1 border border-gray-600"><Info size={14}/></button>
                                </div>
                                <h4 className="text-xs uppercase tracking-widest text-indigo-400 font-bold mb-2 pl-1 flex items-center gap-2"><Activity size={12}/> Dettaglio Impianto</h4>
                                <InventoryItemCard 
                                    item={selectedBodyItem} 
                                    isExpanded={true} 
                                    onToggleExpand={()=>{}} 
                                    onEquip={handleToggleEquip}
                                    onRecharge={handleRecharge}
                                    onAssembly={handleOpenAssembly}
                                    onModuloClick={handleModuloClick}
                                />
                            </div>
                        )}
                    </div>
                    {!selectedBodyItem && genericItems.length === 0 && <div className="hidden md:flex h-full items-center justify-center text-gray-600 italic text-sm p-8 border border-dashed border-gray-800 rounded-lg">Seleziona una parte del corpo per vedere l'innesto.</div>}
                    {genericItems.length > 0 && (
                        <div className="border-t border-gray-700 pt-4">
                            <h4 className="text-xs font-bold text-gray-500 uppercase mb-2">Potenziamenti Sistemici</h4>
                            {renderList(genericItems)}
                        </div>
                    )}
                </div>
            </div>
        ) : <p className="text-gray-600 italic text-sm p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">Sistemi organici standard.</p>}
      </section>

      <section>
        <h3 className="text-sm font-bold text-emerald-300 mb-3 flex items-center gap-2 uppercase tracking-wider pl-1"><Shield size={16} /> Equipaggiamento Attivo</h3>
        {equipItems.length > 0 ? renderList(equipItems) : <p className="text-gray-600 italic text-sm p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">Mani vuote.</p>}
      </section>

      <section>
        <h3 className="text-sm font-bold text-gray-400 mb-3 flex items-center gap-2 uppercase tracking-wider pl-1"><Box size={16} /> Zaino</h3>
        {zainoItems.length > 0 ? renderList(zainoItems) : <p className="text-gray-600 italic text-sm p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">Zaino vuoto.</p>}
      </section>

      {showShop && <ShopModal onClose={() => setShowShop(false)} />}
      {showAssembly && assemblyHost && <ItemAssemblyModal hostItem={assemblyHost} inventory={items} onClose={() => { setShowAssembly(false); setAssemblyHost(null); }} onRefresh={handleAssemblyComplete} />}
      {showModuloDetail && selectedModuloId && <ModuloDetailModal moduloId={selectedModuloId} onClose={() => { setShowModuloDetail(false); setSelectedModuloId(null); }} onLogout={onLogout} />}
    </div>
  );
};

export default memo(InventoryTab);