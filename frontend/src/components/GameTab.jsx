import React, { useState, useEffect, useMemo } from 'react'; 
import { useCharacter } from './CharacterContext';
import { 
    Heart, Zap, Crosshair, Clock, Battery, RefreshCw, 
    Star, MessageSquare, Briefcase, Backpack, AlertCircle, Plus, Minus,
    ChevronDown, ChevronUp, Hexagon, Activity, Weight, Sparkles
} from 'lucide-react';

import { 
    useOptimisticStatChange,
    useConsumaRisorsa,
} from '../hooks/useGameData';
import { gameComaControl } from '../api';

import ActiveItemWidget from './ActiveItemWidget'; 

/** Etichetta rango difesa: resa visiva stabile in base al livello */
const RankDefLabel = ({ x, y, rankValue, fill, fontSize = '11', textAnchor = 'middle' }) => {
    if (rankValue === undefined || rankValue === null) return null;
    const rankNum = Number(rankValue) || 0;
    const rankStyle =
        rankNum <= 0
            ? { opacity: 0.16 }
            : rankNum === 1
                ? { opacity: 0.58 }
                : rankNum === 2
                    ? { filter: 'drop-shadow(0 0 4px rgba(255, 255, 255, 0.65))', opacity: 0.94 }
                    : rankNum === 3
                        ? { filter: 'drop-shadow(0 0 6px rgba(250, 204, 21, 0.82))', opacity: 1 }
                        : { filter: 'drop-shadow(0 0 8px rgba(250, 204, 21, 0.95))', opacity: 1 };
    return (
        <text
            x={x}
            y={y}
            fill={fill}
            fontSize={fontSize}
            textAnchor={textAnchor}
            pointerEvents="none"
            className="transition-all duration-300"
            style={rankStyle}
        >
            <tspan fontWeight="bold">Rango: {rankValue}</tspan>
        </text>
    );
};

// --- WIDGET DANNI (corpo delocalizzato: PV singolo) ---
const BodyDamageWidget = ({
    stats,
    maxHp,
    maxArmor,
    maxShell,
    rankPV,
    rankArmor,
    rankShell,
    onHit,
}) => {
    const getZoneColor = (current) => {
        if (current <= 0) return '#ef4444';
        if (current < maxHp / 2) return '#eab308';
        return '#3b82f6';
    };

    // Calcolo opacità barre
    const armorOpacity = maxArmor > 0 ? (stats['PA_CUR'] / maxArmor) : 0;
    const shellOpacity = maxShell > 0 ? (stats['PS_CUR'] / maxShell) : 0;

    return (
        <div className="relative w-full max-w-[260px] mx-auto select-none">
            <svg viewBox="0 0 200 348" className="w-full h-full drop-shadow-2xl">
                <defs>
                    <filter id="glow-shell" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="3" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                </defs>

                {/* LAYER 1: GUSCIO (PS) */}
                <g
                    opacity={Math.max(0.1, shellOpacity)}
                    className="transition-all duration-500"
                    style={{ pointerEvents: maxShell > 0 ? 'auto' : 'none', cursor: maxShell > 0 ? 'pointer' : 'default' }}
                    onClick={() => maxShell > 0 && onHit('PS_CUR', maxShell)}
                    filter="url(#glow-shell)"
                >
                    <ellipse cx="100" cy="165" rx="95" ry="155" fill="transparent" stroke="#8b5cf6" strokeWidth="3" strokeDasharray={shellOpacity === 0 ? "4 4" : "0"} />
                    {maxShell > 0 && <text x="100" y="16" fill="#a78bfa" fontSize="13" textAnchor="middle" fontWeight="bold">GUSCIO {stats['PS_CUR']}/{maxShell}</text>}
                    <RankDefLabel x="100" y="30" rankValue={rankShell} fill="#c4b5fd" fontSize="11.5" />
                </g>

                {/* LAYER 2: ARMATURA (PA) */}
                <g
                    opacity={Math.max(0.1, armorOpacity)}
                    className="transition-all duration-500"
                    style={{ pointerEvents: maxArmor > 0 ? 'auto' : 'none', cursor: maxArmor > 0 ? 'pointer' : 'default' }}
                    onClick={() => maxArmor > 0 && onHit('PA_CUR', maxArmor)}
                >
                    <path d="M100,20 C135,20 170,60 170,165 C170,260 145,315 100,315 C55,315 30,260 30,165 C30,60 65,20 100,20 Z" fill="rgba(16, 185, 129, 0.1)" stroke="#10b981" strokeWidth="2" strokeDasharray={armorOpacity === 0 ? "2 2" : "0"} />
                    {maxArmor > 0 && <text x="100" y="326" fill="#34d399" fontSize="13" textAnchor="middle" fontWeight="bold">ARM {stats['PA_CUR']}/{maxArmor}</text>}
                    <RankDefLabel x="100" y="342" rankValue={rankArmor} fill="#6ee7b7" fontSize="11.5" />
                </g>

                {/* LAYER 3: CORPO (ominio rimpicciolito — armatura/guscio invariati sopra e sotto) */}
                <g className="filter drop-shadow-md">
                    <g transform="translate(100,168) scale(0.66) translate(-100,-168)">
                        <g onClick={() => onHit('PV_CUR', maxHp)} className="cursor-pointer transition-all">
                            {/* Testa */}
                            <circle cx="100" cy="25" r="20" fill={getZoneColor(stats['PV_CUR'])} stroke="#e5e7eb" strokeWidth="2" />
                            {/* Collo */}
                            <rect x="88" y="42" width="24" height="16" rx="4" fill={getZoneColor(stats['PV_CUR'])} stroke="#e5e7eb" strokeWidth="1.5" />
                            {/* Tronco */}
                            <path d="M68,58 L68,100 L94,106 L106,106 L132,100 L132,58 L116,52 L84,52 Z M68,100 L74,155 L88,162 L112,162 L126,155 L132,100 Z" fill={getZoneColor(stats['PV_CUR'])} stroke="rgba(255,255,255,0.65)" strokeWidth="2" strokeLinejoin="round" />
                            {/* Braccia */}
                            <path d="M132,58 L142,64 L150,82 L154,105 L156,130 L157,158 L154,162 L146,160 L144,130 L140,105 L134,76 Z" fill={getZoneColor(stats['PV_CUR'])} stroke="rgba(255,255,255,0.65)" strokeWidth="2" strokeLinejoin="round" />
                            <path d="M68,58 L58,64 L50,82 L46,105 L44,130 L43,158 L46,162 L54,160 L56,130 L60,105 L66,76 Z" fill={getZoneColor(stats['PV_CUR'])} stroke="rgba(255,255,255,0.65)" strokeWidth="2" strokeLinejoin="round" />
                            {/* Gambe */}
                            <path d="M126,155 L130,200 L132,255 L134,300 L126,306 L116,306 L114,300 L112,255 L110,200 L112,162 Z" fill={getZoneColor(stats['PV_CUR'])} stroke="rgba(255,255,255,0.65)" strokeWidth="2" strokeLinejoin="round" />
                            <path d="M74,155 L70,200 L68,255 L66,300 L74,306 L84,306 L86,300 L88,255 L90,200 L88,162 Z" fill={getZoneColor(stats['PV_CUR'])} stroke="rgba(255,255,255,0.65)" strokeWidth="2" strokeLinejoin="round" />
                        </g>
                    </g>
                    {/* Fuori dallo scale: stessa dimensione visiva di GUSCIO/ARM e ranghi */}
                    <text
                        x="100"
                        y="178"
                        fontSize="30"
                        textAnchor="middle"
                        pointerEvents="none"
                        fontWeight="bold"
                        style={{ textShadow: '0px 2px 6px black' }}
                    >
                        <tspan fill="#ffffff">{stats['PV_CUR']}</tspan>
                        <tspan fill="#e5e7eb">{' PV'}</tspan>
                    </text>
                    <RankDefLabel x="100" y="194" rankValue={rankPV} fill="#93c5fd" fontSize="11.5" />
                </g>
            </svg>
            {stats['PV_CUR'] <= 0 && (
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-red-900/90 text-white px-4 py-2 rounded-xl border-2 border-red-500 animate-pulse text-center shadow-2xl z-20">
                    <AlertCircle className="mx-auto mb-1 text-red-400" />
                    <span className="font-black text-lg uppercase tracking-widest">COMA</span>
                </div>
            )}
        </div>
    );
};

const DamageControlPanel = ({ stats, maxHp, maxArmor, maxShell, onChange }) => {
    const [isOpen, setIsOpen] = useState(false);

    const rows = [
        { id: 'PS_CUR', label: 'Guscio (PS)', max: maxShell, color: 'text-purple-400' },
        { id: 'PA_CUR', label: 'Armatura', max: maxArmor, color: 'text-emerald-400' },
        { id: 'PV_CUR', label: 'Punti Vita', max: maxHp, color: 'text-blue-400' },
    ];

    return (
        <div className="bg-gray-800 rounded-xl border border-gray-700 overflow-hidden">
            <button onClick={() => setIsOpen(!isOpen)} className="w-full flex justify-between items-center p-3 bg-gray-900/50 hover:bg-gray-700 transition-colors">
                <span className="text-xs font-bold uppercase tracking-wider text-gray-400 flex items-center gap-2"><Crosshair size={14}/> Controlli Manuali</span>
                {isOpen ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
            </button>
            {isOpen && (
                <div className="p-2 space-y-1 animate-in slide-in-from-top-2">
                    {rows.map(r => {
                        if (r.max <= 0 && (r.id === 'PS_CUR' || r.id === 'PA_CUR')) return null;
                        const val = stats[r.id];
                        return (
                            <div key={r.id} className="flex items-center justify-between bg-gray-900/30 p-2 rounded">
                                <span className={`text-xs font-bold ${r.color} w-20`}>{r.label}</span>
                                <div className="flex items-center gap-2">
                                    <span className="text-xs font-mono text-white w-8 text-right">{val}/{r.max}</span>
                                    <div className="flex gap-1">
                                        <button onClick={() => onChange(r.id, 'add', r.max)} className="p-1 bg-green-900/50 hover:bg-green-700 rounded text-green-200"><Plus size={12}/></button>
                                        <button onClick={() => onChange(r.id, 'consuma', r.max)} className="p-1 bg-red-900/50 hover:bg-red-700 rounded text-red-200"><Minus size={12}/></button>
                                        <button onClick={() => onChange(r.id, 'reset', r.max)} className="p-1 bg-blue-900/50 hover:bg-blue-700 rounded text-blue-200"><RefreshCw size={12}/></button>
                                    </div>
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    );
};

const RisorsaPoolWidget = ({ pool, onConsume, isPending }) => {
    const [nowTs, setNowTs] = useState(Date.now());
    useEffect(() => {
        const id = window.setInterval(() => setNowTs(Date.now()), 1000);
        return () => window.clearInterval(id);
    }, []);
    const canConsume = (pool.valore_corrente || 0) >= 1;
    const rec = pool?.recupero_auto || {};
    const nextTickMs = rec?.next_tick_at ? new Date(rec.next_tick_at).getTime() : null;
    const countdownSeconds = nextTickMs != null ? Math.max(0, Math.ceil((nextTickMs - nowTs) / 1000)) : null;
    const mm = countdownSeconds != null ? Math.floor(countdownSeconds / 60) : 0;
    const ss = countdownSeconds != null ? countdownSeconds % 60 : 0;
    return (
        <div className="bg-gray-800 rounded-xl p-3 border border-amber-900/40 shadow-md">
            <div className="flex justify-between items-start mb-2 gap-2">
                <span className="text-[10px] font-bold text-amber-200/90 uppercase tracking-widest flex items-center gap-2">
                    <Sparkles size={12} className="text-amber-400" /> {pool.nome}
                </span>
                <button
                    type="button"
                    disabled={!canConsume || isPending}
                    onClick={() => {
                        if (
                            !window.confirm(
                                `Consumare 1 punto di ${pool.nome} (${pool.sigla})?`
                            )
                        ) {
                            return;
                        }
                        onConsume(pool.sigla);
                    }}
                    className="text-sm font-bold px-4 py-2.5 min-h-[44px] rounded-lg bg-amber-900/40 text-amber-100 hover:bg-amber-800/60 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
                >
                    Consuma 1
                </button>
            </div>
            <div className="text-2xl font-black text-white font-mono">
                {pool.valore_corrente}
                <span className="text-[10px] text-gray-500 font-normal ml-2">
                    / max {pool.valore_max}
                </span>
            </div>
            {rec.active ? (
                <div className="mt-1 text-[10px] text-emerald-300/90 font-mono">
                    Recupero auto +{rec.step || 1} ogni {rec.interval_seconds || 0}s · prossimo tick {String(mm).padStart(2, '0')}:
                    {String(ss).padStart(2, '0')}
                </div>
            ) : null}
            {pool.descrizione ? (
                <div
                    className="mt-2 text-[11px] text-gray-400 prose prose-invert prose-sm max-w-none leading-snug"
                    dangerouslySetInnerHTML={{ __html: pool.descrizione }}
                />
            ) : null}
        </div>
    );
};

const ChakraWidget = ({ current, max, onChange }) => {
    return (
        <div className="bg-gray-800 rounded-xl p-3 border border-gray-700 shadow-md">
            <div className="flex justify-between items-center mb-2">
                <span className="text-[10px] font-bold text-gray-400 uppercase tracking-widest flex items-center gap-2"><Hexagon size={12} className="text-pink-500" /> Chakra</span>
                <div className="flex gap-2">
                    <button onClick={() => onChange('CHK_CUR', 'add', max)} className="text-xs text-green-400 hover:text-green-300 font-bold px-2 bg-green-900/20 rounded">+1</button>
                    <button onClick={() => onChange('CHK_CUR', 'reset', max)} className="text-gray-500 hover:text-white"><RefreshCw size={12}/></button>
                </div>
            </div>
            <div className="flex flex-wrap gap-1.5">
                {[...Array(max)].map((_, i) => (
                    <button key={i} onClick={() => onChange('CHK_CUR', 'consuma', max)} disabled={i >= current} className={`w-5 h-5 rounded-full border flex items-center justify-center transition-all ${i < current ? 'bg-pink-600 border-pink-400 shadow-[0_0_8px_#db2777] scale-100' : 'bg-gray-900 border-gray-700 scale-90 opacity-50'}`}>
                        {i < current && <div className="w-1.5 h-1.5 bg-white rounded-full animate-pulse" />}
                    </button>
                ))}
            </div>
            <div className="text-right mt-1 text-[9px] text-gray-500 font-mono">{current} / {max}</div>
        </div>
    );
};

const RigenerazioneTimerWidget = ({ rows }) => {
    const [nowTs, setNowTs] = useState(Date.now());
    useEffect(() => {
        const id = window.setInterval(() => setNowTs(Date.now()), 1000);
        return () => window.clearInterval(id);
    }, []);

    if (!Array.isArray(rows) || rows.length === 0) return null;
    return (
        <div className="bg-gray-900/50 rounded-lg p-2 border border-emerald-800/40 text-[10px] text-gray-300">
            <span className="font-bold text-emerald-300 uppercase tracking-wider">Rigenerazioni attive</span>
            <ul className="mt-1 space-y-1">
                {rows.map((r) => {
                    const nextMs = r?.next_tick_at ? new Date(r.next_tick_at).getTime() : null;
                    const left = nextMs != null ? Math.max(0, Math.ceil((nextMs - nowTs) / 1000)) : 0;
                    const mm = String(Math.floor(left / 60)).padStart(2, '0');
                    const ss = String(left % 60).padStart(2, '0');
                    const fonte = (r.abilita_nomi || []).length > 0 ? r.abilita_nomi.join(', ') : 'Regola automatica';
                    return (
                        <li key={`regen-${r.sigla}`} className="font-mono">
                            <span className="text-emerald-200">{r.nome || r.sigla}</span>{' '}
                            <span className="text-gray-500">({r.sigla})</span>{' '}
                            <span
                                className={`inline-block rounded px-1.5 py-0.5 text-[9px] font-bold uppercase tracking-wide ${
                                    r.paused
                                        ? 'bg-amber-900/60 text-amber-200 border border-amber-700/60'
                                        : 'bg-emerald-900/60 text-emerald-200 border border-emerald-700/60'
                                }`}
                            >
                                {r.paused ? 'in pausa' : `${mm}:${ss}`}
                            </span>{' '}
                            <span className="text-gray-400">· {fonte}</span>
                        </li>
                    );
                })}
            </ul>
        </div>
    );
};

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

const LiveComaCountdown = ({ endAtIso, pausedAtIso, isPaused, fallbackSeconds = 0 }) => {
    const [tick, setTick] = useState(Date.now());

    useEffect(() => {
        const id = window.setInterval(() => setTick(Date.now()), 1000);
        return () => window.clearInterval(id);
    }, []);

    const endAtMs = endAtIso ? new Date(endAtIso).getTime() : 0;
    const pausedAtMs = pausedAtIso ? new Date(pausedAtIso).getTime() : 0;
    const computed = isPaused
        ? Math.max(0, Math.floor((endAtMs - pausedAtMs) / 1000))
        : Math.max(0, Math.ceil((endAtMs - tick) / 1000));
    const seconds = Number.isFinite(computed) ? computed : Math.max(0, Number(fallbackSeconds || 0));

    return (
        <span>
            {String(Math.floor(seconds / 60)).padStart(2, '0')}:{String(seconds % 60).padStart(2, '0')}
        </span>
    );
};

// --- MAIN GAMETAB ---
const GameTab = ({ onNavigate }) => {
    const { selectedCharacterData: char, unreadCount, refreshCharacterData, onLogout } = useCharacter();
    const [favorites, setFavorites] = useState([]);
    const [comaBusy, setComaBusy] = useState(false);
    
    const statMutation = useOptimisticStatChange();
    const risorsaMutation = useConsumaRisorsa();

    useEffect(() => {
        const savedFavs = JSON.parse(localStorage.getItem('kor35_favorites') || '[]');
        setFavorites(savedFavs);
    }, []);

    // --- FUNZIONI HELPER PER VISUALIZZAZIONE ---
    const isActiveByTime = (item) => {
        if (!item.data_fine_attivazione) return true;
        const now = new Date().getTime();
        const end = new Date(item.data_fine_attivazione).getTime();
        return end >= now;
    };

    const isActiveByCharges = (item) => {
        if (item.spegne_a_zero_cariche) {
             const hasCharges = (item.cariche_attuali || 0) > 0;
             if (!hasCharges && !isActiveByTime(item)) return false;
        }
        return true;
    };

    // --- FILTRO OGGETTI ATTIVI (LOGICA GAME TAB) ---
    const activeItems = useMemo(() => {
        // Protezione anti-crash: se char non è ancora caricato, ritorna array vuoto
        if (!char || !char.oggetti) return [];
        
        const activatables = [];

        // 1. Identifica gli Host Attivi (Equipaggiati o Installati)
        const activeHosts = char.oggetti.filter(item => {
             const isPhysEquipped = (item.tipo_oggetto === 'FIS' && item.is_equipaggiato);
             const isInnateInstalled = (['INN', 'MUT'].includes(item.tipo_oggetto) && item.slot_corpo);
             return isPhysEquipped || isInnateInstalled;
        });

        // 2. Estrai tutto ciò che è attivabile (Host e le loro Mod)
        activeHosts.forEach(host => {
             // A. Aggiungi l'Host se ha meccaniche proprie (cariche/durata)
             if (host.cariche_massime > 0 || host.durata_totale > 0) {
                 activatables.push(host);
             }

             // B. Aggiungi i Potenziamenti (Mod/Materia) installati nell'Host
             if (host.potenziamenti_installati && host.potenziamenti_installati.length > 0) {
                 host.potenziamenti_installati.forEach(mod => {
                     if (mod.cariche_massime > 0 || mod.durata_totale > 0) {
                         activatables.push(mod);
                     }
                 });
             }
        });

        return activatables;
    }, [char]); // Dipendenza da 'char' completa

    // --- NUOVA LOGICA: Verifica se un oggetto è attivo secondo le regole specificate ---
    const isObjectActive = (item) => {
        // Un oggetto è attivo se non ha cariche_massime (non si spegne mai)
        // OPPURE se ha cariche_massime ma la data_fine_attivazione non è passata (o non è impostata)
        if (!item.cariche_massime || item.cariche_massime === 0) {
            return true; // Nessun limite di cariche, sempre attivo
        }
        // Ha cariche_massime, controlla la data
        return isActiveByTime(item);
    };

    // --- RACCOLTA ATTACCHI DA TUTTE LE FONTI ATTIVE ---
    const allAttacks = useMemo(() => {
        if (!char) return [];
        
        const attacks = [];

        // 1. Attacchi da oggetti equipaggiati e innesti/mutazioni
        if (char.oggetti) {
            const activeHosts = char.oggetti.filter(item => {
                const isPhysEquipped = (item.tipo_oggetto === 'FIS' && item.is_equipaggiato);
                const isInnateInstalled = (['INN', 'MUT'].includes(item.tipo_oggetto) && item.slot_corpo);
                return isPhysEquipped || isInnateInstalled;
            });

            activeHosts.forEach(host => {
                // A. Aggiungi l'Host se ha attacco ed è attivo
                if (host.attacco_base && isObjectActive(host)) {
                    attacks.push({
                        type: 'oggetto',
                        source: host,
                        isHost: true,
                        hostName: host.nome,
                    });
                }

                // B. Aggiungi i Potenziamenti (Mod/Materia) installati nell'Host che hanno attacco
                if (host.potenziamenti_installati && host.potenziamenti_installati.length > 0) {
                    host.potenziamenti_installati.forEach(mod => {
                        if (mod.attacco_base && isObjectActive(mod)) {
                            attacks.push({
                                type: 'modulo',
                                source: mod,
                                isHost: false,
                                hostName: host.nome,
                            });
                        }
                    });
                }
            });
        }

        // 2. Attacchi da tessiture favorite
        if (char.tessiture_possedute) {
            const favoriteTessiture = char.tessiture_possedute.filter(t => t.is_favorite);
            favoriteTessiture.forEach(tessitura => {
                // Le tessiture hanno sempre una formula di attacco se sono favorite
                if (tessitura.formula || tessitura.testo_formattato_personaggio) {
                    attacks.push({
                        type: 'tessitura',
                        source: tessitura,
                        isHost: true,
                        hostName: tessitura.nome,
                    });
                }
            });
        }

        return attacks;
    }, [char]);

    // --- COMPATIBILITÀ: Mantieni la variabile weapons per il vecchio codice (deprecata) ---
    const weapons = allAttacks.filter(a => a.isHost).map(a => a.source);

    const handleStatChange = (key, mode, maxOverride) => {
        statMutation.mutate({ charId: char.id, stat_sigla: key, mode, max_override: maxOverride || 0 });
    };

    const toggleFavorite = (item) => {
        let newFavs;
        if (favorites.find(f => f.id === item.id)) {
            newFavs = favorites.filter(f => f.id !== item.id);
        } else {
            newFavs = [...favorites, { id: item.id, nome: item.nome, testo: item.TestoFormattato }];
        }
        setFavorites(newFavs);
        localStorage.setItem('kor35_favorites', JSON.stringify(newFavs));
    };

    if (!char) return <div className="p-8 text-center text-white">Caricamento...</div>;

    // Statistiche Tattiche
    const primary = char.statistiche_primarie || [];
    const maxHP = primary.find((x) => x.sigla === 'PV')?.valore_max || 0;
    const maxArmor = primary.find((x) => x.sigla === 'PA')?.valore_max || 0;
    const maxShell = primary.find((x) => x.sigla === 'PS')?.valore_max || 0;
    const maxChakra = primary.find((x) => x.sigla === 'CHA')?.valore_max || 1;
    const pickPrimaryRank = (sigla) => {
        const e = primary.find((x) => x.sigla === sigla);
        return e?.valore_corrente ?? e?.valore_max;
    };
    const rankPV = pickPrimaryRank('RPV');
    const rankArmor = pickPrimaryRank('RPA');
    const rankShell = pickPrimaryRank('RPG');

    const tempStats = char.statistiche_temporanee || {};
    const tacticalStats = {
        'PV_CUR': tempStats['PV_CUR'] !== undefined ? tempStats['PV_CUR'] : maxHP,
        'PA_CUR': tempStats['PA_CUR'] !== undefined ? tempStats['PA_CUR'] : maxArmor,
        'PS_CUR': tempStats['PS_CUR'] !== undefined ? tempStats['PS_CUR'] : maxShell,
        'CHK_CUR': tempStats['CHK_CUR'] !== undefined ? tempStats['CHK_CUR'] : maxChakra,
    };
    const comaState = char?.impostazioni_ui?.coma_state || null;
    const isDead = !!char?.data_morte || comaState?.status === 'dead';
    const hasComaCountdown = tacticalStats['PV_CUR'] <= 0 && !!comaState && !isDead;

    const handleComaControl = async (actionName) => {
        if (!char?.id) return;
        setComaBusy(true);
        try {
            await gameComaControl(char.id, actionName, onLogout);
            await refreshCharacterData();
        } catch (e) {
            alert(e?.message || 'Errore controllo coma.');
        } finally {
            setComaBusy(false);
        }
    };

    // Logica Capacità
    const statCog = primary.find((s) => s.sigla === 'COG');
    const capacityMax = statCog ? statCog.valore_max : 10;
    const capacityConsumers = char.oggetti.filter(i => i.is_equipaggiato && i.tipo_oggetto === 'FIS');
    const capacityUsed = capacityConsumers.length;
    
    const statOgp = primary.find((s) => s.sigla === 'OGP');
    const heavyMax = statOgp ? statOgp.valore_max : 0;
    const heavyConsumers = char.oggetti.filter(i => i.is_equipaggiato && i.is_pesante);
    const heavyUsed = heavyConsumers.length;

    return (
        <div className="pb-24 px-2 space-y-6 animate-fadeIn text-gray-100 pt-2">
            
            <CapacityDashboard 
                capacityUsed={capacityUsed} capacityMax={capacityMax} capacityConsumers={capacityConsumers}
                heavyUsed={heavyUsed} heavyMax={heavyMax} heavyConsumers={heavyConsumers}
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-900 rounded-xl p-4 border border-gray-700 shadow-lg flex flex-col items-center">
                    <h3 className="text-[10px] uppercase tracking-widest text-gray-500 mb-3 font-bold w-full flex items-center gap-2"><Activity size={12} /> Status Fisico</h3>
                    <BodyDamageWidget
                        stats={tacticalStats}
                        maxHp={maxHP}
                        maxArmor={maxArmor}
                        maxShell={maxShell}
                        rankPV={rankPV}
                        rankArmor={rankArmor}
                        rankShell={rankShell}
                        onHit={(id, max) => handleStatChange(id, 'consuma', max)}
                    />
                    {hasComaCountdown && (
                        <div className="mt-3 w-full max-w-[280px] bg-red-950/50 border border-red-700 rounded-xl p-3 text-center">
                            <div className="text-xs uppercase tracking-widest text-red-300 font-bold">Coma</div>
                            <div className="text-3xl font-mono font-black text-red-100 mt-1">
                                <LiveComaCountdown
                                    endAtIso={comaState?.end_at}
                                    pausedAtIso={comaState?.paused_at}
                                    isPaused={!!comaState?.is_paused}
                                    fallbackSeconds={comaState?.remaining_seconds}
                                />
                            </div>
                            <button
                                type="button"
                                disabled={comaBusy}
                                onClick={() => handleComaControl(comaState?.is_paused ? 'stabilize_stop' : 'stabilize_start')}
                                className="mt-2 w-full py-2 rounded-lg bg-red-800 hover:bg-red-700 disabled:opacity-50 text-xs font-bold uppercase tracking-wide"
                            >
                                {comaState?.is_paused ? 'Termina stabilizzazione' : 'Stabilizzato'}
                            </button>
                            <button
                                type="button"
                                disabled={comaBusy}
                                onClick={() => handleComaControl('fatal_hit')}
                                className={`mt-2 w-full py-2 rounded-lg disabled:opacity-50 text-xs font-bold uppercase tracking-wide ${
                                    String(comaState?.death_mode || 'none') === 'fatale'
                                        ? 'bg-amber-600 text-black'
                                        : 'bg-amber-900 hover:bg-amber-800 text-amber-100'
                                }`}
                            >
                                Colpo Fatale (3 ranghi superiori ai PV)
                            </button>
                            <button
                                type="button"
                                disabled={comaBusy}
                                onClick={() => {
                                    if (window.confirm('Confermi colpo mortale? Il personaggio morira istantaneamente.')) {
                                        handleComaControl('mortal_hit');
                                    }
                                }}
                                className="mt-2 w-full py-2 rounded-lg bg-black/80 border border-red-500 hover:bg-black disabled:opacity-50 text-xs font-bold uppercase tracking-wide text-red-200"
                            >
                                Colpo Mortale (4+ ranghi superiori ai PV)
                            </button>
                        </div>
                    )}
                    {isDead && (
                        <div className="mt-3 w-full max-w-[360px] bg-red-950/70 border border-red-500 rounded-xl p-3 text-center">
                            <div className="text-red-200 font-black uppercase tracking-wide">
                                Il personaggio e morto. Contatta lo staff.
                            </div>
                        </div>
                    )}
                </div>
                <div className="flex flex-col gap-4">
                    <DamageControlPanel stats={tacticalStats} maxHp={maxHP} maxArmor={maxArmor} maxShell={maxShell} onChange={handleStatChange} />
                    {(maxChakra > 0) && <ChakraWidget current={tacticalStats['CHK_CUR']} max={maxChakra} onChange={handleStatChange} />}
                    <RigenerazioneTimerWidget rows={char.rigenerazioni_auto_ui || []} />
                    {(char.risorse_pool_ui || []).filter((p) => p.valore_max > 0).map((pool) => (
                        <RisorsaPoolWidget
                            key={pool.sigla}
                            pool={pool}
                            isPending={risorsaMutation.isPending}
                            onConsume={(sigla) =>
                                risorsaMutation.mutate({ charId: char.id, statSigla: sigla })
                            }
                        />
                    ))}
                    {Array.isArray(char.effetti_risorsa_attivi) && char.effetti_risorsa_attivi.length > 0 && (
                        <div className="bg-gray-900/50 rounded-lg p-2 border border-gray-700 text-[10px] text-gray-400">
                            <span className="font-bold text-gray-500 uppercase tracking-wider">Effetti risorsa attivi</span>
                            <ul className="mt-1 space-y-1">
                                {char.effetti_risorsa_attivi.map((e) => (
                                    <li key={e.id} className="font-mono text-gray-300">
                                        {e.abilita_nome || 'Effetto'} · fino a {new Date(e.scadenza).toLocaleString()}
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}
                </div>
            </div>

            {/* 2. ATTACCHI DA TUTTE LE FONTI ATTIVE */}
            {allAttacks.length > 0 && (
                <section>
                    <h3 className="text-[10px] uppercase tracking-widest text-red-400 mb-2 font-bold flex items-center gap-2 ml-1">
                        <Crosshair size={12} /> Attacchi
                    </h3>
                    <div className="grid grid-cols-1 gap-2">
                        {allAttacks.map((attack, idx) => {
                            // Render Tessitura
                            if (attack.type === 'tessitura') {
                                const tessitura = attack.source;
                                return (
                                    <div key={`tessitura-${tessitura.id}`} className="bg-linear-to-r from-purple-900/20 to-gray-900/20 border border-purple-500/30 p-3 rounded-lg shadow-sm">
                                        <div className="flex justify-between items-start mb-2">
                                            <div>
                                                <div className="font-bold text-purple-100 text-sm flex items-center gap-2">
                                                    <Star size={14} className="text-yellow-400" fill="currentColor" />
                                                    {tessitura.nome}
                                                </div>
                                                <div className="text-[10px] text-purple-300/60 uppercase">Tessitura • Lv.{tessitura.livello}</div>
                                            </div>
                                        </div>
                                        <div className="bg-black/30 rounded p-2 mt-2 border-l-2 border-purple-500">
                                            <div 
                                                className="text-xs text-purple-200 prose prose-invert prose-sm max-w-none"
                                                dangerouslySetInnerHTML={{ 
                                                    __html: tessitura.testo_formattato_personaggio || tessitura.TestoFormattato || tessitura.formula || 'Formula non disponibile' 
                                                }} 
                                            />
                                        </div>
                                    </div>
                                );
                            }

                            // Render Oggetti raggruppati per host
                            return null; // Gli oggetti vengono renderizzati dopo, raggruppati
                        })}

                        {/* Raggruppa gli attacchi da oggetti per host */}
                        {(() => {
                            const objectAttacks = allAttacks.filter(a => a.type === 'oggetto' || a.type === 'modulo');
                            const hostGroups = {};
                            
                            objectAttacks.forEach(attack => {
                                const key = attack.hostName;
                                if (!hostGroups[key]) {
                                    hostGroups[key] = { host: null, mods: [] };
                                }
                                if (attack.isHost) {
                                    hostGroups[key].host = attack.source;
                                } else {
                                    hostGroups[key].mods.push(attack.source);
                                }
                            });

                            return Object.entries(hostGroups).map(([hostName, group]) => (
                                <div key={`obj-${hostName}`} className="bg-linear-to-r from-red-900/20 to-gray-900/20 border border-red-500/30 p-3 rounded-lg shadow-sm">
                                    {/* Attacco Host (se presente) */}
                                    {group.host && (
                                        <div className="flex justify-between items-start mb-2">
                                            <div>
                                                <div className="font-bold text-red-100 text-sm flex items-center gap-2">
                                                    {group.host.nome}
                                                    {group.host.is_pesante && <Weight size={12} className="text-orange-500" title="Oggetto Pesante"/>}
                                                </div>
                                                <div className="text-[10px] text-red-300/60 uppercase">{group.host.tipo_oggetto_display}</div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-lg font-mono font-bold text-red-400 drop-shadow-sm">
                                                    {group.host.attacco_formattato || group.host.attacco_base}
                                                </div>
                                            </div>
                                        </div>
                                    )}

                                    {/* Attacchi dei Moduli */}
                                    {group.mods.length > 0 && (
                                        <div className={group.host ? "mt-2 space-y-1" : "space-y-1"}>
                                            {!group.host && (
                                                <div className="text-xs text-gray-400 mb-2">
                                                    Host: <span className="font-bold text-gray-300">{hostName}</span>
                                                </div>
                                            )}
                                            {group.mods.map(mod => (
                                                <div key={mod.id} className="flex justify-between items-center bg-black/30 rounded px-2 py-1 border-l-2 border-yellow-500">
                                                    <div className="flex items-center gap-2">
                                                        <Zap size={10} className="text-yellow-500" />
                                                        <span className="text-xs text-gray-300 font-medium">{mod.nome}</span>
                                                        <span className="text-[9px] text-gray-500">({mod.tipo_oggetto_display})</span>
                                                    </div>
                                                    <span className="font-mono text-xs font-bold text-yellow-100">
                                                        {mod.attacco_formattato || mod.attacco_base}
                                                    </span>
                                                </div>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            ));
                        })()}
                    </div>
                </section>
            )}

            {/* 3. DISPOSITIVI ATTIVI (Ora mostra tutto) */}
            <section>
                <h3 className="text-[10px] uppercase tracking-widest text-emerald-400 font-bold flex items-center gap-2 mb-2 ml-1">
                    <Zap size={12} /> Dispositivi Attivi
                </h3>
                <div className="flex flex-wrap gap-3">
                    {activeItems.map(item => (
                        <ActiveItemWidget 
                            key={item.id} 
                            item={item} 
                            // IMPORTANTE: Assicura il refresh dei dati al click
                            onUpdate={refreshCharacterData} 
                        />
                    ))}
                    {activeItems.length === 0 && <p className="text-gray-600 text-xs italic w-full text-center py-4">Nessun dispositivo attivo.</p>}
                </div>
            </section>

            {/* Link Navigazione */}
            <div className="grid grid-cols-3 gap-3 mt-4">
                <button onClick={() => onNavigate('messaggi')} className="bg-gray-800 p-3 rounded-lg border border-gray-700 flex justify-between shadow items-center hover:bg-gray-750 transition-colors">
                    <div className="flex gap-2 text-indigo-400 font-bold text-xs"><MessageSquare size={16} /> Messaggi</div>
                    {unreadCount > 0 ? <span className="bg-red-500 text-white text-xs font-bold px-2 py-0.5 rounded-full animate-pulse">{unreadCount}</span> : <span className="text-gray-600 text-xs">-</span>}
                </button>
                <button onClick={() => onNavigate('transazioni')} className="bg-gray-800 p-3 rounded-lg border border-gray-700 flex justify-between shadow items-center hover:bg-gray-750 transition-colors">
                    <div className="flex gap-2 text-amber-400 font-bold text-xs"><Briefcase size={16} /> Lavori</div>
                    {char.lavori_pendenti_count > 0 ? <span className="bg-amber-500 text-black text-xs font-bold px-2 py-0.5 rounded-full animate-bounce">{char.lavori_pendenti_count}</span> : <span className="text-gray-600 text-xs">-</span>}
                </button>
                <button onClick={() => onNavigate('social')} className="bg-gray-800 p-3 rounded-lg border border-gray-700 flex justify-between shadow items-center hover:bg-gray-750 transition-colors">
                    <div className="flex gap-2 text-pink-400 font-bold text-xs"><Sparkles size={16} /> Social</div>
                    <span className="text-gray-600 text-xs">↗</span>
                </button>
            </div>

            {favorites.length > 0 && (
                <section className="mt-6 pt-4 border-t border-gray-800">
                    <h3 className="text-[10px] uppercase tracking-widest text-yellow-500 mb-3 font-bold flex items-center gap-2 ml-1"><Star size={12} /> Prontuario Rapido</h3>
                    <div className="space-y-3">
                        {favorites.map(fav => (
                            <div key={fav.id} className="bg-yellow-900/5 border border-yellow-700/20 p-3 rounded-lg relative group">
                                <div className="flex justify-between items-start mb-1">
                                    <span className="font-bold text-yellow-200/80 text-sm">{fav.nome}</span>
                                    <button onClick={() => toggleFavorite(fav)} className="text-yellow-800 hover:text-red-400"><Star size={12} fill="currentColor"/></button>
                                </div>
                                <div className="text-[11px] text-gray-400 leading-snug prose prose-invert max-w-none" dangerouslySetInnerHTML={{ __html: fav.testo }} />
                            </div>
                        ))}
                    </div>
                </section>
            )}
        </div>
    );
};

export default GameTab;