import React, { useState, useEffect, memo, useCallback, useRef } from 'react';
import { useCharacter } from './CharacterContext';
import { 
    ShoppingBag, Box, Shield, Zap, Loader2, Wrench, 
    Info, ChevronUp, ChevronDown, Activity, Power, Battery, 
    Clock, RefreshCw, Sparkles, Swords, Lock, User, Backpack, Weight, X, Trash2
} from 'lucide-react';
import ShopModal from './ShopModal';
import ItemAssemblyModal from './ItemAssemblyModal';
import ModuloDetailModal from './ModuloDetailModal';
import PunteggioDisplay from './PunteggioDisplay';
import { useOptimisticEquip, useOptimisticRecharge, useOptimisticDamage, useOptimisticRepair, useOptimisticDiscard } from '../hooks/useGameData';
import { emitToast } from '../utils/toastBus';

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

const formatCountdown = (totalSeconds) => {
    const safe = Math.max(0, Number(totalSeconds || 0));
    const minutes = Math.floor(safe / 60);
    const seconds = safe % 60;
    return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`;
};

const PHYSICAL_SLOT_CONFIG = [
    { key: 'head', label: 'Testa', shortLabel: 'TES', capacity: 1, aliases: ['testa', 'elmo', 'helm', 'head'] },
    { key: 'neck', label: 'Collo', shortLabel: 'COL', capacity: 1, aliases: ['collo', 'neck', 'collana', 'amulet'] },
    { key: 'vest', label: 'Veste', shortLabel: 'VES', capacity: 1, aliases: ['veste', 'vest', 'robe', 'abito'] },
    { key: 'shoulders', label: 'Spalle', shortLabel: 'SPA', capacity: 1, aliases: ['spalle', 'shoulder'] },
    { key: 'arms', label: 'Braccia', shortLabel: 'BRA', capacity: 2, aliases: ['braccia', 'bracciale', 'arm'] },
    { key: 'fingers', label: 'Dita', shortLabel: 'DIT', capacity: 2, aliases: ['dita', 'anello', 'ring', 'finger'] },
    { key: 'feet', label: 'Piedi', shortLabel: 'PIE', capacity: 1, aliases: ['piedi', 'stivali', 'feet', 'boots'] },
    { key: 'belt', label: 'Cintura', shortLabel: 'CIN', capacity: 1, aliases: ['cintura', 'belt'] },
    { key: 'armor', label: 'Armatura', shortLabel: 'ARM', capacity: 1, aliases: ['armatura', 'armor', 'corazza'] },
    { key: 'melee', label: 'Armi Mischia', shortLabel: 'MIS', capacity: 1, aliases: ['mischia', 'melee', 'spada', 'arma'] },
    { key: 'ranged', label: 'Armi Distanza', shortLabel: 'DIS', capacity: 1, aliases: ['distanza', 'ranged', 'arco', 'fucile'] },
    { key: 'focus', label: 'Focus', shortLabel: 'FOC', capacity: 1, aliases: ['focus'] },
    { key: 'shield', label: 'Scudo', shortLabel: 'SCD', capacity: 1, aliases: ['scudo', 'shield'] },
];

const SLOT_STAT_SIGLE = {
    head: 'SHD',
    neck: 'SNK',
    vest: 'SVE',
    shoulders: 'SSH',
    arms: 'SAR',
    fingers: 'SFI',
    feet: 'SFT',
    belt: 'SBL',
    armor: 'SAM',
    melee: 'SLM',
    ranged: 'SLR',
    focus: 'SLF',
    shield: 'SLS',
};

const SLOT_ICON = {
    head: '🪖',
    neck: '📿',
    vest: '🧥',
    shoulders: '🛡️',
    arms: '💪',
    fingers: '💍',
    feet: '🥾',
    belt: '🧷',
    armor: '🛡',
    melee: '🗡️',
    ranged: '🏹',
    focus: '✨',
    shield: '🛡️',
};

const normalizeText = (value) => (value || '').toString().toLowerCase();

const inferPhysicalSlots = (item) => {
    const explicit = Array.isArray(item?.slot_fisici_possibili) ? item.slot_fisici_possibili : [];
    if (explicit.length > 0) {
        if (explicit.includes('focus') || explicit.includes('shield')) {
            return Array.from(new Set([...explicit, 'melee', 'ranged']));
        }
        return explicit;
    }

    const haystack = `${normalizeText(item?.classe_oggetto_nome)} ${normalizeText(item?.nome)} ${normalizeText(item?.tipo_oggetto_display)}`;
    const matched = PHYSICAL_SLOT_CONFIG.filter((slot) => slot.aliases.some((alias) => haystack.includes(alias))).map((slot) => slot.key);
    if (matched.includes('focus') || matched.includes('shield')) {
        return Array.from(new Set([...matched, 'melee', 'ranged']));
    }
    if (matched.length > 0) return matched;
    return ['vest'];
};

const SLOT_BTN_SIZE = 'w-[4.5rem] h-[4.5rem] sm:w-20 sm:h-20 md:w-[5.25rem] md:h-[5.25rem]';
const SLOT_BTN_TEXT = 'text-[11px] sm:text-xs';

const jewelryCellLabel = (slotKey, index) => {
    if (slotKey === 'fingers') return `Dito ${index + 1}`;
    if (slotKey === 'arms') return index === 0 ? 'Braccio Sx' : 'Braccio Dx';
    return null;
};

const PhysicalBodySlotsWidget = ({ slots, selectedSlotKey, onSelectSlot, onSlotDrop, onSlotDragOver, dragHintBySlot, isDragging, onTouchSlotSelect, runtimeBySlot = {} }) => {
    const bodySlots = slots.filter((s) => !['melee', 'ranged', 'focus', 'shield'].includes(s.key));
    const weaponSlots = slots.filter((s) => ['melee', 'ranged', 'focus', 'shield'].includes(s.key));
    const slotByKey = Object.fromEntries(bodySlots.map((s) => [s.key, s]));

    const bodyCells = ['arms', 'fingers'].flatMap((slotKey) => {
        const slot = slotByKey[slotKey];
        if (!slot) return [];
        const total = Math.max(1, Number(slot.capacity || 1));
        return Array.from({ length: total }, (_, idx) => ({
            slot,
            index: idx,
            key: `${slot.key}#${idx + 1}`,
            item: slot.equippedInSlot[idx] || null,
        }));
    });

    const weaponCells = weaponSlots.flatMap((slot) => {
        const total = Math.max(1, Number(slot.capacity || 1));
        return Array.from({ length: total }, (_, idx) => ({
            slot,
            index: idx,
            key: `${slot.key}#${idx + 1}`,
            item: slot.equippedInSlot[idx] || null,
        }));
    });

    const getBodyCell = (slotKey, index) => bodyCells.find((c) => c.slot.key === slotKey && c.index === index);

    const renderSingleSlot = (slotKey, labelOverride = null) => {
        const slot = slotByKey[slotKey];
        if (!slot) return null;
        const occupied = slot.equippedInSlot.length;
        const runtimeOccupied = (runtimeBySlot[slot.key] || []).length;
        const occupiedTotal = occupied + runtimeOccupied;
        const isSelected = selectedSlotKey === slot.key;
        const isFull = occupiedTotal >= slot.capacity;
        const hasRuntime = runtimeOccupied > 0;
        const dragHint = dragHintBySlot?.[slot.key] || null;
        const canDrop = dragHint?.canDrop === true;
        const isBlockedByDrag = dragHint && !dragHint.canDrop;
        const label = labelOverride || (slot.key === 'neck' ? 'Collana' : (slot.shortLabel || slot.label));

        return (
            <button
                key={slot.key}
                type="button"
                onClick={() => {
                    if (onTouchSlotSelect && onTouchSlotSelect(slot) === true) return;
                    onSelectSlot(slot);
                }}
                onDrop={(e) => onSlotDrop(e, slot)}
                onDragOver={(e) => onSlotDragOver(e, slot)}
                className={`${SLOT_BTN_SIZE} px-1 py-1 rounded-xl border text-center ${SLOT_BTN_TEXT} font-bold transition-colors shrink-0 ${
                    canDrop ? `ring-2 ring-emerald-400 border-emerald-400 bg-emerald-900/40 text-emerald-100 ${isDragging ? 'animate-pulse' : ''}` :
                    isBlockedByDrag ? 'ring-2 ring-red-500/70 border-red-600 bg-red-900/25 text-red-100' :
                    isSelected ? 'border-indigo-400 bg-indigo-900/40 text-indigo-100' :
                    hasRuntime ? 'border-sky-500/80 bg-sky-900/35 text-sky-100 shadow-[0_0_10px_rgba(56,189,248,0.25)]' :
                    occupied > 0 ? 'border-emerald-700 bg-emerald-900/25 text-emerald-200' :
                    'border-gray-700 bg-gray-900/80 text-gray-300'
                }`}
                title={dragHint?.reason || 'Clicca o trascina un oggetto compatibile'}
            >
                <div className="leading-tight flex flex-col items-center justify-center gap-0.5">
                    <span className="text-base sm:text-lg">{SLOT_ICON[slot.key] || '◻'}</span>
                    <span>{label}</span>
                </div>
                <div className={`font-mono ${isFull ? (hasRuntime ? 'text-sky-200' : 'text-emerald-300') : 'text-gray-500'}`}>
                    {occupiedTotal}/{slot.capacity}
                </div>
            </button>
        );
    };

    const renderMultiCell = (slotKey, index) => {
        const cell = getBodyCell(slotKey, index);
        if (!cell) return null;
        const { slot, key, item } = cell;
        const occupied = slot.equippedInSlot.length;
        const runtimeOccupied = (runtimeBySlot[slot.key] || []).length;
        const occupiedTotal = occupied + runtimeOccupied;
        const isSelected = selectedSlotKey === slot.key;
        const dragHint = dragHintBySlot?.[slot.key] || null;
        const canDropInSlot = dragHint?.canDrop === true;
        const cellIsFilled = !!item;
        const runtimeCellFilled = !cellIsFilled && index < occupiedTotal;
        const canDropInThisCell = canDropInSlot && !cellIsFilled && index >= occupied;
        const isBlockedByDrag = dragHint && !canDropInThisCell;

        return (
            <button
                key={key}
                type="button"
                onClick={() => onSelectSlot(slot)}
                onDrop={(e) => onSlotDrop(e, slot)}
                onDragOver={(e) => {
                    if (canDropInThisCell) onSlotDragOver(e, slot);
                }}
                className={`${SLOT_BTN_SIZE} px-1 py-1 rounded-xl border text-center ${SLOT_BTN_TEXT} font-bold transition-colors shrink-0 ${
                    canDropInThisCell ? `ring-2 ring-emerald-400 border-emerald-400 bg-emerald-900/40 text-emerald-100 ${isDragging ? 'animate-pulse' : ''}` :
                    isBlockedByDrag ? 'ring-2 ring-red-500/70 border-red-600 bg-red-900/25 text-red-100' :
                    isSelected ? 'border-indigo-400 bg-indigo-900/40 text-indigo-100' :
                    runtimeCellFilled ? 'border-sky-500/80 bg-sky-900/35 text-sky-100 shadow-[0_0_10px_rgba(56,189,248,0.25)]' :
                    cellIsFilled ? 'border-emerald-700 bg-emerald-900/25 text-emerald-200' :
                    'border-gray-700 bg-gray-900/80 text-gray-300'
                }`}
                title={dragHint?.reason || 'Clicca o trascina un oggetto compatibile'}
            >
                <div className="leading-tight flex flex-col items-center justify-center gap-0.5">
                    <span className="text-base sm:text-lg">{SLOT_ICON[slot.key] || '◻'}</span>
                    <span>{jewelryCellLabel(slot.key, index) || `${slot.shortLabel || slot.label} #${index + 1}`}</span>
                </div>
                <div className={`font-mono ${runtimeCellFilled ? 'text-sky-200' : cellIsFilled ? 'text-emerald-300' : 'text-gray-500'}`}>
                    {runtimeCellFilled ? 'AZZ' : cellIsFilled ? 'OK' : 'VUOTO'}
                </div>
            </button>
        );
    };

    return (
        <div className="mx-auto w-full max-w-[620px] rounded-xl border border-gray-700 bg-gray-950/60 overflow-hidden p-3">
            <div className="flex gap-3 sm:gap-4 items-stretch">
                <div className="flex-1 min-w-0 relative">
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                        <User size={190} className="text-gray-800" />
                    </div>
                    <div className="relative flex flex-col items-center gap-2.5 py-2">
                        {renderSingleSlot('head')}
                        {renderSingleSlot('shoulders')}
                        <div className="flex items-center justify-center gap-2 sm:gap-2.5">
                            {renderMultiCell('arms', 0)}
                            <div className="flex gap-2 sm:gap-2.5">
                                {renderSingleSlot('armor')}
                                {renderSingleSlot('vest')}
                            </div>
                            {renderMultiCell('arms', 1)}
                        </div>
                        {renderSingleSlot('belt')}
                        {renderSingleSlot('feet')}
                    </div>
                </div>

                <div className="flex flex-col items-center gap-2.5 shrink-0 border-l border-gray-800/80 pl-3 sm:pl-4">
                    <div className="text-[9px] uppercase tracking-wider text-gray-600 -mb-0.5">Gioielli</div>
                    {renderSingleSlot('neck')}
                    {renderMultiCell('fingers', 0)}
                    {renderMultiCell('fingers', 1)}
                </div>
            </div>

            <div className="mt-3">
                <div className="text-[10px] uppercase tracking-wider text-gray-500 mb-2 text-center">Slot armi / mano</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2.5">
                    {weaponCells.map((cell) => {
                        const { slot, index, key, item } = cell;
                        const occupied = slot.equippedInSlot.length;
                        const runtimeOccupied = (runtimeBySlot[slot.key] || []).length;
                        const occupiedTotal = occupied + runtimeOccupied;
                        const isSelected = selectedSlotKey === slot.key;
                        const dragHint = dragHintBySlot?.[slot.key] || null;
                        const canDropInSlot = dragHint?.canDrop === true;
                        const cellIsFilled = !!item;
                        const runtimeCellFilled = !cellIsFilled && index < occupiedTotal;
                        const canDropInThisCell = canDropInSlot && !cellIsFilled && index >= occupied;
                        const isBlockedByDrag = dragHint && !canDropInThisCell;
                        return (
                            <button
                                key={key}
                                type="button"
                                onClick={() => {
                                    if (onTouchSlotSelect && onTouchSlotSelect(slot) === true) return;
                                    onSelectSlot(slot);
                                }}
                                onDrop={(e) => onSlotDrop(e, slot)}
                                onDragOver={(e) => {
                                    if (canDropInThisCell) onSlotDragOver(e, slot);
                                }}
                                className={`w-full h-[4.5rem] sm:h-20 px-1 py-1 rounded-xl border text-center ${SLOT_BTN_TEXT} font-bold transition-colors ${
                                    canDropInThisCell ? `ring-2 ring-emerald-400 border-emerald-400 bg-emerald-900/40 text-emerald-100 ${isDragging ? 'animate-pulse' : ''}` :
                                    isBlockedByDrag ? 'ring-2 ring-red-500/70 border-red-600 bg-red-900/25 text-red-100' :
                                    isSelected ? 'border-indigo-400 bg-indigo-900/40 text-indigo-100' :
                                    runtimeCellFilled ? 'border-sky-500/80 bg-sky-900/35 text-sky-100 shadow-[0_0_10px_rgba(56,189,248,0.25)]' :
                                    cellIsFilled ? 'border-emerald-700 bg-emerald-900/25 text-emerald-200' :
                                    'border-gray-700 bg-gray-900/80 text-gray-300'
                                }`}
                                title={dragHint?.reason || "Clicca o trascina un oggetto compatibile"}
                            >
                                <div className="leading-tight flex flex-col items-center justify-center gap-0.5">
                                    <span className="text-base sm:text-lg">{SLOT_ICON[slot.key] || '◻'}</span>
                                    <span>{slot.shortLabel || slot.label} #{index + 1}</span>
                                </div>
                                <div className={`font-mono ${runtimeCellFilled ? 'text-sky-200' : cellIsFilled ? 'text-emerald-300' : 'text-gray-500'}`}>
                                    {runtimeCellFilled ? 'AZZ' : cellIsFilled ? 'OK' : 'VUOTO'}
                                </div>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
};

const LazyList = ({ items, renderItem, batchSize = 10 }) => {
    const itemsKey = items.map((item) => item.id).join(',');
    const [visibleCount, setVisibleCount] = useState(batchSize);

    useEffect(() => {
        setVisibleCount(batchSize);
    }, [itemsKey, batchSize]);

    const displayedItems = items.slice(0, visibleCount);
    const showMore = () => {
        setVisibleCount((prev) => Math.min(prev + batchSize, items.length));
    };

    return (
        <div className="space-y-2">
            {displayedItems.map(renderItem)}
            
            {visibleCount < items.length && (
                <button 
                    type="button"
                    onClick={showMore}
                    className="w-full py-3 mt-2 text-sm font-bold text-gray-400 bg-gray-800/50 hover:bg-gray-700 border border-dashed border-gray-600 rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                    <ChevronDown size={16} /> Carica altri ({items.length - visibleCount})
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
const InventoryItemCard = memo(({ item, isExpanded, onToggleExpand, onEquip, onRecharge, onAssembly, onModuloClick, onDamage, onRepair, onDiscard, preferredSlotKey = null, isDraggable = false, onDragStartCard = null, onDragEndCard = null, onTouchPickCard = null, onTouchReleaseCard = null }) => {
    const isPhysical = item.tipo_oggetto === 'FIS';
    const canBeModified = (isPhysical || ['INN', 'MUT'].includes(item.tipo_oggetto)) && (item.classe_oggetto_nome || item.tipo_oggetto === 'INN');
    const isActive = item.is_active;
    const installedModsCount = item.potenziamenti_installati?.length || 0;
    const isModifiedObject = isPhysical && installedModsCount > 0;
    const availableEquipSlots = isPhysical && !item.is_equipaggiato ? inferPhysicalSlots(item).length : 0;

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
        if (item.is_danneggiato) return 'border-2 border-red-700/80 bg-red-900/20';
        if (item.is_equipaggiato) return 'border-2 border-yellow-600/60 bg-yellow-900/10';
        return 'border border-gray-700 bg-gray-800 hover:border-gray-600'; 
    };

    return (
        <div
            className={`relative p-3 mb-3 rounded-lg flex flex-col transition-all ${getStatusStyle()}`}
            draggable={isDraggable}
            onDragStart={(e) => onDragStartCard && onDragStartCard(e, item)}
            onDragEnd={() => onDragEndCard && onDragEndCard()}
            onTouchStart={() => onTouchPickCard && onTouchPickCard(item)}
            onTouchEnd={() => onTouchReleaseCard && onTouchReleaseCard()}
            onTouchCancel={() => onTouchReleaseCard && onTouchReleaseCard()}
        >
            
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
                    {isModifiedObject && (
                        <div className="ml-1 text-[10px] text-indigo-300 font-bold" title={`Oggetto modificato (${Math.min(4, installedModsCount)} mod)`}>
                            {'\u2699'.repeat(Math.min(4, installedModsCount))}
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
                                {item.slot_equip && <span>• slot {item.slot_equip}</span>}
                                {availableEquipSlots > 1 && <span className="text-indigo-300">• {availableEquipSlots} slot disp.</span>}
                                {item.is_danneggiato && <span className="text-red-400">• DANNEGGIATO</span>}
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
                                onClick={(e) => { e.stopPropagation(); onEquip(item.id, preferredSlotKey); }}
                                disabled={item.is_danneggiato && !item.is_equipaggiato}
                                className={`flex-1 py-2 rounded text-xs font-bold transition-all active:scale-95 flex items-center justify-center gap-2 shadow-sm ${
                                    item.is_equipaggiato
                                    ? 'bg-red-900/80 hover:bg-red-800 text-red-100 border border-red-700'
                                    : 'bg-emerald-700 hover:bg-emerald-600 text-white border border-emerald-600 disabled:opacity-50 disabled:cursor-not-allowed'
                                }`}
                            >
                                {item.is_equipaggiato ? <><Power size={14}/> Rimuovi</> : <><Shield size={14}/> Equipaggia</>}
                            </button>
                        )}
                        {!item.is_danneggiato && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onDamage(item.id); }}
                                className="py-2 px-2 rounded text-xs font-bold bg-red-950 hover:bg-red-900 text-red-200 border border-red-700"
                                title="Danneggia"
                            >
                                Danneggia
                            </button>
                        )}
                        {item.is_danneggiato && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onRepair(item.id); }}
                                className="py-2 px-2 rounded text-xs font-bold bg-blue-950 hover:bg-blue-900 text-blue-200 border border-blue-700"
                                title="Ripara"
                            >
                                Ripara
                            </button>
                        )}
                        {isPhysical && !item.is_danneggiato && (
                            <button
                                onClick={(e) => { e.stopPropagation(); onDiscard && onDiscard(item); }}
                                className="py-2 px-2 rounded text-xs font-bold bg-red-950 hover:bg-red-900 text-red-200 border border-red-700 flex items-center justify-center"
                                title="Scarta"
                            >
                                <Trash2 size={14} />
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
                        <div key={item.id} className="flex items-center gap-1.5 bg-gray-800 px-2 py-1 rounded border border-gray-600 shadow-sm">
                            <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${item.isRuntime ? 'bg-sky-400' : 'bg-indigo-500'}`}></div>
                            <span className={`text-[10px] truncate font-mono max-w-[120px] ${item.isRuntime ? 'text-sky-300' : 'text-gray-300'}`}>
                                {item.isRuntime ? `🕒 ${item.nome}` : item.nome}
                            </span>
                        </div>
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
  const [shopSearchTerm, setShopSearchTerm] = useState('');
  const [showAssembly, setShowAssembly] = useState(false);
  const [assemblyHost, setAssemblyHost] = useState(null);
  const [selectedBodyItem, setSelectedBodyItem] = useState(null);
  const [bodyViewTab, setBodyViewTab] = useState('physical');
  const [selectedPhysicalSlot, setSelectedPhysicalSlot] = useState(null);
  const [draggingItemId, setDraggingItemId] = useState(null);
  const [dragHintBySlot, setDragHintBySlot] = useState({});
  const touchPickTimerRef = useRef(null);
  const [touchDragMode, setTouchDragMode] = useState(false);
  const [expandedItems, setExpandedItems] = useState({});
  const [showModuloDetail, setShowModuloDetail] = useState(false);
  const [selectedModuloId, setSelectedModuloId] = useState(null);
  const [equipSlotModal, setEquipSlotModal] = useState({ open: false, itemId: null, itemName: '', slots: [] });
  const [nowTs, setNowTs] = useState(() => Date.now());

  const equipMutation = useOptimisticEquip();
  const rechargeMutation = useOptimisticRecharge();
  const damageMutation = useOptimisticDamage();
  const repairMutation = useOptimisticRepair();
  const discardMutation = useOptimisticDiscard();

  useEffect(() => {
    if (characterData?.oggetti) setItems(characterData.oggetti);
    else setItems([]);
  }, [characterData]);

  useEffect(() => {
      const timer = window.setInterval(() => setNowTs(Date.now()), 1000);
      return () => window.clearInterval(timer);
  }, []);

  const executeEquipMutation = (itemId, slotKey = null) => equipMutation.mutate(
      { itemId, slotKey, charId: characterData.id },
      {
          onError: (err) => {
              emitToast({
                  type: 'error',
                  title: 'Equip fallito',
                  message: err?.message || 'Verifica limiti slot/capacita/tecnologia.',
              });
          },
      }
  );
  const handleDamage = (itemId) => damageMutation.mutate({ itemId, charId: characterData.id });
  const handleRepair = (itemId) => repairMutation.mutate({ itemId, charId: characterData.id });
  const handleDiscard = (item) => {
      const isBase = !!item.oggetto_base_generatore;
      const rimborso = isBase ? Math.max(0, Math.floor((item.costo_acquisto || 0) / 2)) : 0;
      const confirmMsg = isBase
          ? `Scartare ${item.nome}?\nRiceverai ${rimborso} CR di rimborso (50% del costo base).`
          : `Scartare ${item.nome}?`;
      if (!window.confirm(confirmMsg)) return;
      discardMutation.mutate(
          { itemId: item.id, charId: characterData.id },
          {
              onSuccess: (res) => {
                  const refunded = Number(res?.rimborso_crediti || 0);
                  emitToast({
                      type: 'success',
                      title: 'Oggetto scartato',
                      message: refunded > 0 ? `Rimborso ricevuto: +${refunded} CR.` : 'Oggetto rimosso dall\'inventario.',
                  });
              },
              onError: (err) => {
                  emitToast({
                      type: 'error',
                      title: 'Scarto fallito',
                      message: err?.message || 'Impossibile scartare l\'oggetto.',
                  });
              },
          }
      );
  };

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

  const corpoItems = items.filter(i => ['INN', 'MUT'].includes(i.tipo_oggetto));
  const equipItems = items.filter(i => i.is_equipaggiato && i.tipo_oggetto === 'FIS');
  const zainoItems = items.filter(i => !i.is_equipaggiato && !['INN', 'MUT'].includes(i.tipo_oggetto));
  const runtimeObjects = (characterData?.tessiture_attive_runtime || [])
      .map((rt) => {
          const tessituraCfg = (characterData?.tessiture_possedute || []).find(
              (t) => String(t?.id) === String(rt?.tessitura)
          )?.oggetto_runtime_config;
          return { rt, tessituraCfg };
      })
      .map(({ rt, tessituraCfg }) => {
          const obj = rt?.oggetto_runtime;
          if (!obj || obj.equipaggiato === false) return null;
          const fineTs = rt?.fine ? new Date(rt.fine).getTime() : null;
          const secondiRimanenti = fineTs ? Math.max(0, Math.floor((fineTs - nowTs) / 1000)) : 0;
          return {
              runtimeId: rt.id,
              tessituraNome: rt.tessitura_nome || 'Tessitura',
              nome: obj.nome || 'Oggetto runtime',
              slotKey: obj.slot_key || 'vest',
              descrizione:
                  obj?.metadata?.descrizione_effetto ||
                  obj?.metadata?.descrizione ||
                  rt?.metadata?.descrizione_effetto ||
                  rt?.metadata?.descrizione ||
                  tessituraCfg?.descrizione_effetto ||
                  tessituraCfg?.descrizione ||
                  '',
              secondiRimanenti,
              fine: rt.fine || null,
          };
      })
      .filter(Boolean);
  const runtimeBySlot = runtimeObjects.reduce((acc, obj) => {
      const key = obj.slotKey || 'vest';
      if (!acc[key]) acc[key] = [];
      acc[key].push(obj);
      return acc;
  }, {});

  // Calcolo Capacità Oggetti
  const statCog = characterData?.statistiche_primarie?.find(s => s.sigla === 'COG');
  const capacityMax = statCog ? statCog.valore_max : 10;
  // COG consumata solo da oggetti fisici equipaggiati e realmente modificati (con mod/materia installate).
  const capacityConsumers = items.filter(
      (i) => i.is_equipaggiato && i.tipo_oggetto === 'FIS' && (i.potenziamenti_installati?.length || 0) > 0
  );
  const runtimeCogConsumers = (characterData?.tessiture_attive_runtime || []).map((rt) => ({
      id: `runtime-${rt.id}`,
      nome: `Runtime: ${rt.tessitura_nome || 'Tessitura'}`,
      isRuntime: true,
  }));
  const capacityConsumersAll = [...capacityConsumers, ...runtimeCogConsumers];
  const capacityUsed = capacityConsumersAll.length;
  
  const statOgp = characterData?.statistiche_primarie?.find(s => s.sigla === 'OGP');
  const heavyMax = statOgp ? statOgp.valore_max : 0;
  const heavyConsumers = items.filter(i => i.is_equipaggiato && i.is_pesante);
  const heavyUsed = heavyConsumers.length;

  const getSlotCapacity = (slotKey, defaultCap) => {
      const fromApi = characterData?.slot_capacities?.[slotKey];
      if (fromApi && fromApi > 0) return fromApi;
      const statSigla = SLOT_STAT_SIGLE[slotKey];
      if (!statSigla) return defaultCap;
      const stat = characterData?.statistiche_primarie?.find((s) => s.sigla === statSigla);
      const val = stat ? (stat.valore_corrente ?? stat.valore_max) : null;
      if (val && val > 0) return val;
      return defaultCap;
  };

  const handleToggleEquip = (itemId, preferredSlotKey = null) => {
      const item = items.find((i) => String(i.id) === String(itemId));
      if (!item) return;

      if (item.is_equipaggiato) {
          executeEquipMutation(item.id, item.slot_equip || preferredSlotKey || null);
          return;
      }

      if (preferredSlotKey) {
          executeEquipMutation(item.id, preferredSlotKey);
          return;
      }

      const possibleSlots = inferPhysicalSlots(item);
      const availableSlots = possibleSlots.filter((slotKey) => {
          const cfg = PHYSICAL_SLOT_CONFIG.find((s) => s.key === slotKey);
          const occupied = items.filter(
              (i) => i.is_equipaggiato && i.tipo_oggetto === 'FIS' && i.slot_equip === slotKey
          ).length;
          const cap = getSlotCapacity(slotKey, cfg?.capacity || 1);
          return occupied < cap;
      });

      if (availableSlots.length === 0) {
          emitToast({
              type: 'warning',
              title: 'Nessuno slot disponibile',
              message: 'Tutti gli slot compatibili risultano pieni.',
              durationMs: 1800,
          });
          return;
      }

      if (availableSlots.length === 1) {
          executeEquipMutation(item.id, availableSlots[0]);
          return;
      }

      setEquipSlotModal({
          open: true,
          itemId: item.id,
          itemName: item.nome,
          slots: availableSlots,
      });
  };

  // Render Helper per liste (utilizza il componente Memoizzato)
    const renderList = (list, preferredSlotKey = null) => (
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
                    onDamage={handleDamage}
                    onRepair={handleRepair}
                    onDiscard={handleDiscard}
                    preferredSlotKey={preferredSlotKey}
                    isDraggable={item.tipo_oggetto === 'FIS' && !item.is_equipaggiato}
                    onDragStartCard={(e, draggedItem) => {
                        e.dataTransfer.setData('application/x-kor35-item-id', String(draggedItem.id));
                        setDraggingItemId(draggedItem.id);
                    }}
                    onDragEndCard={() => setDraggingItemId(null)}
                    onTouchPickCard={(pickedItem) => {
                        if (pickedItem.tipo_oggetto !== 'FIS' || pickedItem.is_equipaggiato || pickedItem.is_danneggiato) return;
                        if (touchPickTimerRef.current) window.clearTimeout(touchPickTimerRef.current);
                        touchPickTimerRef.current = window.setTimeout(() => {
                            setTouchDragMode(true);
                            setDraggingItemId(pickedItem.id);
                            emitToast({
                                type: 'info',
                                title: 'Oggetto selezionato',
                                message: `Tocca uno slot compatibile per equipaggiare ${pickedItem.nome}.`,
                                durationMs: 1800,
                            });
                        }, 320);
                    }}
                    onTouchReleaseCard={() => {
                        if (touchPickTimerRef.current) {
                            window.clearTimeout(touchPickTimerRef.current);
                            touchPickTimerRef.current = null;
                        }
                    }}
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

  const physicalSlots = PHYSICAL_SLOT_CONFIG.map((slot) => {
      const equippedInSlot = equipItems.filter((item) => item.slot_equip === slot.key);
      const compatibleFromBackpack = zainoItems.filter((item) => item.tipo_oggetto === 'FIS' && inferPhysicalSlots(item).includes(slot.key));
      const runtimeInSlot = runtimeBySlot[slot.key] || [];
      return { ...slot, capacity: getSlotCapacity(slot.key, slot.capacity), equippedInSlot, compatibleFromBackpack, runtimeInSlot };
  });

  useEffect(() => {
      if (!selectedPhysicalSlot?.key) return;
      const refreshed = physicalSlots.find((s) => s.key === selectedPhysicalSlot.key) || null;
      setSelectedPhysicalSlot(refreshed);
  }, [selectedPhysicalSlot?.key, equipItems.length, zainoItems.length]);

  const handleSlotDragOver = (event, slot) => {
      // Permetti sempre il dragOver: il controllo reale viene fatto in drop.
      // Alcuni browser non espongono correttamente il payload custom durante il drag.
      event.preventDefault();
  };

  const handleSlotDrop = (event, slot) => {
      event.preventDefault();
      const droppedId = event.dataTransfer.getData('application/x-kor35-item-id') || draggingItemId;
      const dragged = zainoItems.find((i) => String(i.id) === String(droppedId) && i.tipo_oggetto === 'FIS' && !i.is_danneggiato);
      if (!dragged) return;
      if (!inferPhysicalSlots(dragged).includes(slot.key)) return;
      if (slot.equippedInSlot.length >= slot.capacity) return;
      handleToggleEquip(dragged.id, slot.key);
      setDraggingItemId(null);
      setTouchDragMode(false);
  };

  const handleTouchSlotSelect = (slot) => {
      if (!touchDragMode || !draggingItemId) return false;
      const dragged = zainoItems.find((i) => String(i.id) === String(draggingItemId) && i.tipo_oggetto === 'FIS' && !i.is_danneggiato);
      if (!dragged) {
          setTouchDragMode(false);
          setDraggingItemId(null);
          return true;
      }
      if (!inferPhysicalSlots(dragged).includes(slot.key) || slot.equippedInSlot.length >= slot.capacity) {
          emitToast({
              type: 'warning',
              title: 'Slot non valido',
              message: 'Seleziona uno slot compatibile e disponibile.',
              durationMs: 1400,
          });
          return true;
      }
      handleToggleEquip(dragged.id, slot.key);
      setTouchDragMode(false);
      setDraggingItemId(null);
      return true;
  };

  const cancelTouchSelection = () => {
      if (touchPickTimerRef.current) {
          window.clearTimeout(touchPickTimerRef.current);
          touchPickTimerRef.current = null;
      }
      setTouchDragMode(false);
      setDraggingItemId(null);
      setDragHintBySlot({});
  };

  useEffect(() => {
      if (!draggingItemId) {
          setDragHintBySlot({});
          setTouchDragMode(false);
          return;
      }
      const dragged = zainoItems.find((i) => String(i.id) === String(draggingItemId) && i.tipo_oggetto === 'FIS');
      if (!dragged) {
          setDragHintBySlot({});
          return;
      }
      const allowed = inferPhysicalSlots(dragged);
      const nextHints = {};
      for (const slot of physicalSlots) {
          if (dragged.is_danneggiato) {
              nextHints[slot.key] = { canDrop: false, reason: 'Oggetto danneggiato: ripara prima di equipaggiare.' };
              continue;
          }
          if (!allowed.includes(slot.key)) {
              nextHints[slot.key] = { canDrop: false, reason: 'Slot non compatibile con questo oggetto.' };
              continue;
          }
          if (slot.equippedInSlot.length >= slot.capacity) {
              nextHints[slot.key] = { canDrop: false, reason: `Slot pieno (${slot.equippedInSlot.length}/${slot.capacity}).` };
              continue;
          }
          nextHints[slot.key] = { canDrop: true, reason: 'Drop per equipaggiare in questo slot.' };
      }
      setDragHintBySlot(nextHints);
  }, [draggingItemId, zainoItems, equipItems.length]);

  if (isContextLoading) return <div className="p-8 text-center text-gray-500 flex justify-center"><Loader2 className="animate-spin" /></div>;
  if (!characterData) return <div className="p-4 text-center text-red-400">Nessun personaggio selezionato.</div>;

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
        capacityConsumers={capacityConsumersAll}
        heavyUsed={heavyUsed} 
        heavyMax={heavyMax} 
        heavyConsumers={heavyConsumers}
      />

      <section>
        <h3 className="text-sm font-bold text-indigo-300 mb-3 flex items-center gap-2 uppercase tracking-wider pl-1"><Activity size={16} /> Diagnostica Corporea</h3>
        <div className="flex gap-2 mb-3">
            <button
                type="button"
                onClick={() => setBodyViewTab('physical')}
                className={`px-3 py-2 rounded-lg text-xs font-bold border transition-colors ${bodyViewTab === 'physical' ? 'bg-indigo-700 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200'}`}
            >
                Slot Oggetti Fisici
            </button>
            <button
                type="button"
                onClick={() => setBodyViewTab('grafts')}
                className={`px-3 py-2 rounded-lg text-xs font-bold border transition-colors ${bodyViewTab === 'grafts' ? 'bg-indigo-700 border-indigo-500 text-white' : 'bg-gray-800 border-gray-700 text-gray-400 hover:text-gray-200'}`}
            >
                Innesti e Mutazioni
            </button>
        </div>
        {bodyViewTab === 'grafts' && corpoItems.length > 0 ? (
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
                                    onDamage={handleDamage}
                                    onRepair={handleRepair}
                                    onDiscard={handleDiscard}
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
        ) : null}
        {bodyViewTab === 'grafts' && corpoItems.length === 0 ? <p className="text-gray-600 italic text-sm p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">Sistemi organici standard.</p> : null}
        {bodyViewTab === 'physical' && (
            <div className="bg-gray-900/50 p-4 rounded-xl border border-gray-700 space-y-3">
                <div className="flex flex-wrap items-center gap-2 text-[10px]">
                    <span className="px-2 py-1 rounded border border-emerald-500/70 bg-emerald-900/30 text-emerald-200">Drop valido</span>
                    <span className="px-2 py-1 rounded border border-red-500/70 bg-red-900/25 text-red-200">Drop bloccato</span>
                    <span className="px-2 py-1 rounded border border-indigo-500/70 bg-indigo-900/25 text-indigo-200">Slot selezionato</span>
                    <span className="px-2 py-1 rounded border border-sky-500/70 bg-sky-900/30 text-sky-100">Oggetti temporanei</span>
                </div>
                <p className="text-xs text-gray-500">Trascina dall'inventario verso uno slot compatibile oppure clicca lo slot e usa “Equipaggia”.</p>
                {touchDragMode && (
                    <div className="flex items-center justify-between gap-2">
                        <p className="text-xs text-indigo-300 font-semibold">
                            Modalita touch attiva: tocca uno slot evidenziato per completare l'equip.
                        </p>
                        <button
                            type="button"
                            onClick={cancelTouchSelection}
                            className="text-[10px] px-2 py-1 rounded border border-gray-600 bg-gray-800 hover:bg-gray-700 text-gray-200 font-bold uppercase"
                        >
                            Annulla
                        </button>
                    </div>
                )}
                <PhysicalBodySlotsWidget
                    slots={physicalSlots}
                    selectedSlotKey={selectedPhysicalSlot?.key}
                    onSelectSlot={setSelectedPhysicalSlot}
                    onSlotDrop={handleSlotDrop}
                    onSlotDragOver={handleSlotDragOver}
                    dragHintBySlot={dragHintBySlot}
                    isDragging={!!draggingItemId}
                    onTouchSlotSelect={handleTouchSlotSelect}
                    runtimeBySlot={runtimeBySlot}
                />
                {selectedPhysicalSlot && (
                    <div className="border-t border-gray-700 pt-3">
                        <div className="text-xs uppercase tracking-wider text-indigo-300 font-bold mb-2">
                            Slot: {selectedPhysicalSlot.label}
                        </div>
                        {selectedPhysicalSlot.equippedInSlot.length > 0 || (selectedPhysicalSlot.runtimeInSlot?.length || 0) > 0 ? (
                            <div className="space-y-2">
                                {selectedPhysicalSlot.equippedInSlot.length > 0 && renderList(selectedPhysicalSlot.equippedInSlot, selectedPhysicalSlot.key)}
                                {(selectedPhysicalSlot.runtimeInSlot || []).map((rtObj) => (
                                    <div
                                        key={`runtime-slot-${rtObj.runtimeId}-${rtObj.slotKey}`}
                                        className="rounded-lg border border-sky-500/60 bg-sky-900/20 p-3 shadow-[0_0_14px_rgba(56,189,248,0.22)]"
                                    >
                                        <div className="flex items-center justify-between gap-2">
                                            <div>
                                                <div className="text-xs uppercase tracking-wider text-sky-200 font-bold">Placeholder oggetto temporaneo</div>
                                                <div className="text-sm font-semibold text-sky-50">{rtObj.nome}</div>
                                                <div className="text-[10px] text-sky-300/80">Origine: {rtObj.tessituraNome}</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-[10px] uppercase tracking-wider text-sky-300">Durata residua</div>
                                                <div className="font-mono text-sky-100">{formatCountdown(rtObj.secondiRimanenti)}</div>
                                            </div>
                                        </div>
                                        {rtObj.descrizione ? (
                                            <div className="mt-2 text-xs text-sky-100/90 border-t border-sky-600/30 pt-2">
                                                {rtObj.descrizione}
                                            </div>
                                        ) : null}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <div className="space-y-2">
                                <p className="text-xs text-gray-500">Slot vuoto. Oggetti compatibili nell'inventario:</p>
                                {selectedPhysicalSlot.compatibleFromBackpack.length > 0 ? (
                                    renderList(selectedPhysicalSlot.compatibleFromBackpack, selectedPhysicalSlot.key)
                                ) : (
                                    <p className="text-xs text-gray-600 italic">Nessun oggetto fisico compatibile.</p>
                                )}
                            </div>
                        )}
                    </div>
                )}
            </div>
        )}
      </section>

      <section>
        <h3 className="text-sm font-bold text-emerald-300 mb-3 flex items-center gap-2 uppercase tracking-wider pl-1"><Shield size={16} /> Equipaggiamento Attivo</h3>
        {equipItems.length > 0 || runtimeObjects.length > 0 ? (
            <div className="space-y-2">
                {equipItems.length > 0 ? renderList(equipItems) : null}
                {runtimeObjects.map((rtObj) => (
                    <div
                        key={`runtime-equipped-${rtObj.runtimeId}-${rtObj.slotKey}`}
                        className="rounded-lg border border-sky-500/60 bg-sky-900/20 p-3 shadow-[0_0_14px_rgba(56,189,248,0.22)]"
                    >
                        <div className="flex items-center justify-between gap-2">
                            <div>
                                <div className="text-xs uppercase tracking-wider text-sky-200 font-bold">Oggetto temporaneo</div>
                                <div className="text-sm font-semibold text-sky-50">{rtObj.nome}</div>
                                <div className="text-[10px] text-sky-300/80">Slot: {(PHYSICAL_SLOT_CONFIG.find((s) => s.key === rtObj.slotKey)?.label || rtObj.slotKey)} • Origine: {rtObj.tessituraNome}</div>
                            </div>
                            <div className="text-right">
                                <div className="text-[10px] uppercase tracking-wider text-sky-300">Countdown</div>
                                <div className="font-mono text-sky-100">{formatCountdown(rtObj.secondiRimanenti)}</div>
                            </div>
                        </div>
                        {rtObj.descrizione ? (
                            <div className="mt-2 text-xs text-sky-100/90 border-t border-sky-600/30 pt-2">
                                {rtObj.descrizione}
                            </div>
                        ) : null}
                    </div>
                ))}
            </div>
        ) : <p className="text-gray-600 italic text-sm p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">Mani vuote.</p>}
      </section>

      <section>
        <h3 className="text-sm font-bold text-gray-400 mb-3 flex items-center gap-2 uppercase tracking-wider pl-1"><Box size={16} /> Inventario</h3>
        {zainoItems.length > 0 ? renderList(zainoItems) : <p className="text-gray-600 italic text-sm p-4 text-center border border-dashed border-gray-700 rounded-lg bg-gray-800/30">Inventario vuoto.</p>}
      </section>

      {showShop && (
        <ShopModal
          onClose={() => setShowShop(false)}
          searchTerm={shopSearchTerm}
          onSearchTermChange={setShopSearchTerm}
        />
      )}
      {equipSlotModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div
            className="absolute inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setEquipSlotModal({ open: false, itemId: null, itemName: '', slots: [] })}
          />
          <div className="relative w-full max-w-md rounded-xl border border-gray-700 bg-gray-900 shadow-2xl p-4 space-y-3 animate-fadeIn">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-bold text-white uppercase tracking-wide">Scegli slot equip</h3>
              <button
                type="button"
                className="text-gray-400 hover:text-white"
                onClick={() => setEquipSlotModal({ open: false, itemId: null, itemName: '', slots: [] })}
              >
                <X size={18} />
              </button>
            </div>
            <p className="text-xs text-gray-300">
              <span className="font-semibold text-white">{equipSlotModal.itemName}</span> puo essere equipaggiato in piu slot.
              Seleziona dove montarlo:
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
              {equipSlotModal.slots.map((slotKey) => {
                const slotCfg = PHYSICAL_SLOT_CONFIG.find((s) => s.key === slotKey);
                return (
                  <button
                    key={slotKey}
                    type="button"
                    className="rounded-lg border border-indigo-500/40 bg-indigo-900/20 hover:bg-indigo-800/40 px-3 py-2 text-xs font-bold text-indigo-100 text-left"
                    onClick={() => {
                      executeEquipMutation(equipSlotModal.itemId, slotKey);
                      setEquipSlotModal({ open: false, itemId: null, itemName: '', slots: [] });
                    }}
                  >
                    {slotCfg?.label || slotKey}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      )}
      {showAssembly && assemblyHost && <ItemAssemblyModal hostItem={assemblyHost} inventory={items} onClose={() => { setShowAssembly(false); setAssemblyHost(null); }} onRefresh={handleAssemblyComplete} />}
      {showModuloDetail && selectedModuloId && <ModuloDetailModal moduloId={selectedModuloId} onClose={() => { setShowModuloDetail(false); setSelectedModuloId(null); }} onLogout={onLogout} />}
    </div>
  );
};

export default memo(InventoryTab);