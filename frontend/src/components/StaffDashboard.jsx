import React, { useState, useMemo, useCallback, memo, lazy, Suspense, useEffect } from 'react';
import GenericHeader from './GenericHeader';
import Sidebar from './Sidebar';
import { socialGetNotifications, generateWikiManualPdfSnapshot, getWikiManualLatestPdfUrl, getStaffDashboardLayout } from '../api';
import StaffDashboardLayoutEditor from './StaffDashboardLayoutEditor';
import { useCharacter } from './CharacterContext';
import {
    LayoutGrid, LogOut, Menu, ChevronRight, ChevronDown, Globe, Users, BookOpen, Sparkles, LayoutList,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import BuildVersions from './BuildVersions';
import MaintenanceModePanel from './MaintenanceModePanel';
import {
    buildVisibleStaffTools,
    DEFAULT_STAFF_DASHBOARD_LAYOUT,
} from '../staff/staffToolsRegistry';
import {
    applyStaffDashboardLayout,
    buildStaffSidebarItems,
} from '../staff/staffDashboardLayout';

import PlotTab from './PlotTab';
import QrDebugTab from './QrDebugTab';
import TabellaManager from './editors/TabellaManager';

const AdminMessageTab = lazy(() => import('./AdminMessageTab'));
const CerimonialeManager = lazy(() => import('./editors/CerimonialeManager'));
const InfusioneManager = lazy(() => import('./editors/InfusioneManager'));
const TessituraManager = lazy(() => import('./editors/TessituraManager'));
const OggettoBaseManager = lazy(() => import('./editors/OggettoBaseManager'));
const OggettoManager = lazy(() => import('./editors/OggettoManager'));
const StaffProposalTab = lazy(() => import('./editors/StaffProposalTab'));
const MostroManager = lazy(() => import('./editors/MostroManager'));
const AbilitaManager = lazy(() => import('./editors/AbilitaManager'));
const ImmagineManager = lazy(() => import('./editors/ImmagineManager'));
const InventarioManager = lazy(() => import('./editors/InventarioManager'));
const EffettiCasualiManager = lazy(() => import('./editors/EffettiCasualiManager'));
const SocialEventReportTab = lazy(() => import('./editors/SocialEventReportTab'));
const StaffRisorsaPoolTab = lazy(() => import('./StaffRisorsaPoolTab'));
const EraManager = lazy(() => import('./editors/EraManager'));
const CarriereKorpsManager = lazy(() => import('./editors/CarriereKorpsManager'));
const DichiarazioniGlossarioManager = lazy(() => import('./editors/DichiarazioniGlossarioManager'));
const ArcanaProfilesTab = lazy(() => import('./editors/ArcanaProfilesTab'));
const CampaignManager = lazy(() => import('./editors/CampaignManager'));
const ManifestoManager = lazy(() => import('./editors/ManifestoManager'));
const NodoManager = lazy(() => import('./editors/NodoManager'));
const InnescoTimerManager = lazy(() => import('./editors/InnescoTimerManager'));
const PilotaggioManager = lazy(() => import('./editors/PilotaggioManager'));
const CreazioneGuidataStaffManager = lazy(() => import('./editors/CreazioneGuidataStaffManager'));
const ScommesseManager = lazy(() => import('./editors/ScommesseManager'));

const STAFF_COMPONENT_MAP = {
    plot: PlotTab,
    'qr-debug': QrDebugTab,
    tabelle: TabellaManager,
    mostri: MostroManager,
    abilita: AbilitaManager,
    cerimoniali: CerimonialeManager,
    tessiture: TessituraManager,
    infusioni: InfusioneManager,
    proposte: StaffProposalTab,
    oggetti: OggettoManager,
    'oggetti-base': OggettoBaseManager,
    immagini: ImmagineManager,
    inventari: InventarioManager,
    manifesti: ManifestoManager,
    nodi: NodoManager,
    'innesco-timer': InnescoTimerManager,
    pilotaggio: PilotaggioManager,
    'effetti-casuali': EffettiCasualiManager,
    'social-report': SocialEventReportTab,
    'risorse-pool': StaffRisorsaPoolTab,
    'ere-prefetture': EraManager,
    'carriere-korps': CarriereKorpsManager,
    'creazione-guidata': CreazioneGuidataStaffManager,
    'dichiarazioni-glossario': DichiarazioniGlossarioManager,
    'arcana-profiles': ArcanaProfilesTab,
    campagne: CampaignManager,
    maintenance: MaintenanceModePanel,
    messaggi: AdminMessageTab,
    scommesse: ScommesseManager,
};

const DIRECT_LOAD_TOOLS = new Set(['plot', 'qr-debug']);

const LoadingSpinner = () => (
    <div className="h-full flex items-center justify-center bg-gray-900">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-indigo-500"></div>
    </div>
);

const StaffDashboard = ({ onLogout, onSwitchToPlayer, initialTool = 'home', onToolChange }) => {
    const [activeTool, setActiveTool] = useState(initialTool);
    const [isMenuOpen, setIsMenuOpen] = useState(false);
    const [socialUnreadCount, setSocialUnreadCount] = useState(0);
    const [pdfGenerating, setPdfGenerating] = useState(false);
    const [pdfGenMessage, setPdfGenMessage] = useState('');
    const [dashboardLayout, setDashboardLayout] = useState(DEFAULT_STAFF_DASHBOARD_LAYOUT);
    const [expandedGroups, setExpandedGroups] = useState({});
    const [layoutEditorOpen, setLayoutEditorOpen] = useState(false);
    const {
        selectedCharacterId,
        isGlobalSuperuser,
        isCampaignStaffer,
        isCampaignMaster,
        isCampaignHeadMaster,
    } = useCharacter();

    const roleFlags = useMemo(() => ({
        isGlobalSuperuser,
        isCampaignStaffer,
        isCampaignMaster,
        isCampaignHeadMaster,
    }), [isGlobalSuperuser, isCampaignStaffer, isCampaignMaster, isCampaignHeadMaster]);

    const canEditDashboardLayout = isCampaignHeadMaster || isGlobalSuperuser;

    useEffect(() => {
        setActiveTool(initialTool);
    }, [initialTool]);

    useEffect(() => {
        let cancelled = false;
        const loadLayout = async () => {
            try {
                const data = await getStaffDashboardLayout(onLogout);
                if (!cancelled && data?.staff_dashboard_layout) {
                    setDashboardLayout(data.staff_dashboard_layout);
                }
            } catch (e) {
                console.warn('Layout dashboard staff non disponibile, uso default.', e);
            }
        };
        loadLayout();
        return () => { cancelled = true; };
    }, [onLogout]);

    useEffect(() => {
        let interval;
        if (!selectedCharacterId) {
            setSocialUnreadCount(0);
            return undefined;
        }
        const notificationsSeenKey = `social_notifications_seen_at:${selectedCharacterId}`;
        const checkSocialNotifications = async () => {
            try {
                const since = localStorage.getItem(notificationsSeenKey);
                const data = await socialGetNotifications(selectedCharacterId, onLogout, {
                    limit: 30,
                    since: since || undefined,
                });
                const unread = Number(data?.unread_count || 0);
                setSocialUnreadCount(Number.isFinite(unread) ? unread : 0);
            } catch (e) {
                console.error('Errore check notifiche social (staff)', e);
            }
        };
        checkSocialNotifications();
        interval = setInterval(checkSocialNotifications, 60000);
        return () => clearInterval(interval);
    }, [selectedCharacterId, onLogout]);

    const visibleTools = useMemo(
        () => buildVisibleStaffTools(roleFlags, STAFF_COMPONENT_MAP),
        [roleFlags],
    );

    const menuStructure = useMemo(
        () => applyStaffDashboardLayout(visibleTools, dashboardLayout),
        [visibleTools, dashboardLayout],
    );

    useEffect(() => {
        const initial = {};
        for (const section of menuStructure.sections) {
            if (section.tools.length > 1) {
                initial[section.id] = !section.collapsed_default;
            }
        }
        setExpandedGroups(initial);
    }, [menuStructure.sections]);

    const handleToolSelect = useCallback((id) => {
        setActiveTool(id);
        if (onToolChange) onToolChange(id);
        setIsMenuOpen(false);
    }, [onToolChange]);

    const sidebarItems = useMemo(() => buildStaffSidebarItems({
        activeTool,
        menuStructure,
        handleToolSelect,
        onSwitchToPlayer,
        socialUnreadCount,
        hubIcon: <LayoutGrid size={18} />,
        shortcutIcons: {
            globe: <Globe size={18} />,
            sparkles: <Sparkles size={18} />,
            users: <Users size={18} />,
        },
    }), [activeTool, menuStructure, handleToolSelect, onSwitchToPlayer, socialUnreadCount]);

    useEffect(() => {
        if (activeTool === 'home') return;
        const stillVisible = visibleTools.some((t) => t.id === activeTool);
        if (!stillVisible) setActiveTool('home');
    }, [activeTool, visibleTools]);

    const renderSidebarItem = useCallback((item, idx) => {
        if (item.label.includes('---')) {
            return <div key={idx} className="h-px bg-gray-900 my-2 mx-4" />;
        }

        const hasSubItems = item.subItems && item.subItems.length > 0;
        const groupKey = item.groupId || item.label;
        const isExpanded = expandedGroups[groupKey] ?? !item.collapsed_default;

        const baseClasses = `w-full flex items-center justify-between p-3 rounded-xl font-bold transition-all group ${
            item.active
                ? 'bg-indigo-600 text-white shadow-lg'
                : 'text-gray-400 hover:bg-gray-900 hover:text-white'
        }`;

        const content = (
            <>
                <div className="flex items-center gap-3">
                    <div className={`transition-transform duration-200 ${item.active ? '' : 'group-hover:scale-110'}`}>
                        {item.icon}
                    </div>
                    <span className="text-xs uppercase tracking-wide truncate">{item.label}</span>
                </div>
                <div className="flex items-center gap-2">
                    {Number(item.badgeCount || 0) > 0 && (
                        <span className="px-1.5 py-0.5 text-[10px] font-bold text-white rounded-full bg-pink-600">
                            {item.badgeCount}
                        </span>
                    )}
                    {hasSubItems ? (
                        isExpanded ? <ChevronDown size={14} className="opacity-50" /> : <ChevronRight size={14} className="opacity-50" />
                    ) : (
                        item.active && <ChevronRight size={14} className="opacity-50" />
                    )}
                </div>
            </>
        );

        if (item.link) {
            return (
                <Link key={idx} to={item.link} className={baseClasses} title={item.label}>
                    {content}
                </Link>
            );
        }

        if (hasSubItems) {
            return (
                <div key={idx} className="flex flex-col">
                    <button
                        type="button"
                        onClick={() => setExpandedGroups((prev) => ({ ...prev, [groupKey]: !isExpanded }))}
                        className={baseClasses}
                    >
                        {content}
                    </button>
                    {isExpanded && (
                        <div className="ml-4 pl-3 border-l-2 border-gray-800 mt-1 space-y-1 mb-2">
                            {item.subItems.map((sub, sIdx) => (
                                <button
                                    key={sIdx}
                                    type="button"
                                    onClick={sub.action}
                                    className={`w-full text-left p-2.5 rounded-lg text-xs font-bold uppercase tracking-wider transition-colors ${
                                        sub.active ? 'text-indigo-300 bg-indigo-500/10' : 'text-gray-500 hover:text-gray-300'
                                    }`}
                                >
                                    {sub.label}
                                </button>
                            ))}
                        </div>
                    )}
                </div>
            );
        }

        return (
            <button key={idx} type="button" onClick={item.action} className={baseClasses}>
                {content}
            </button>
        );
    }, [expandedGroups]);

    const handleGenerateWikiPdf = useCallback(async () => {
        setPdfGenerating(true);
        setPdfGenMessage('');
        try {
            await generateWikiManualPdfSnapshot(onLogout);
            setPdfGenMessage('Manuale PDF generato con successo.');
        } catch (e) {
            console.error('Errore generazione manuale PDF:', e);
            setPdfGenMessage('Errore durante la generazione del manuale PDF.');
        } finally {
            setPdfGenerating(false);
        }
    }, [onLogout]);

    const activeToolMeta = visibleTools.find((t) => t.id === activeTool);

    return (
        <div className="flex h-screen bg-gray-950 text-white overflow-hidden font-sans">

            <aside className="hidden md:flex flex-col w-72 bg-gray-950 border-r border-gray-800 shadow-2xl z-20">
                <div className="p-6 border-b border-gray-900 flex items-center gap-3">
                    <div className="bg-indigo-600 p-1.5 rounded-lg shadow-lg shadow-indigo-900/50">
                        <LayoutGrid size={20} className="text-white" />
                    </div>
                    <span className="font-black text-indigo-400 italic tracking-widest uppercase text-sm">MENU MASTER</span>
                </div>

                <nav className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
                    {sidebarItems.map((item, idx) => renderSidebarItem(item, idx))}
                </nav>

                <div className="p-4 border-t border-gray-900 bg-gray-950">
                    <button type="button" onClick={onLogout} className="w-full flex items-center gap-3 p-3 rounded-xl font-bold text-red-500 hover:bg-red-500/10 transition-all mb-2">
                        <LogOut size={18} /><span className="text-xs uppercase tracking-wide">Logout</span>
                    </button>
                    <div className="text-center">
                        <BuildVersions className="text-gray-700" />
                    </div>
                </div>
            </aside>

            <Sidebar
                isOpen={isMenuOpen}
                onClose={() => setIsMenuOpen(false)}
                title="Menu Master"
                items={sidebarItems}
                onLogout={onLogout}
            />

            <div className="flex-1 flex flex-col min-w-0 overflow-hidden relative bg-gray-900">
                <GenericHeader
                    title="KOR 35"
                    subtitle={activeTool === 'home' ? 'Dashboard' : activeToolMeta?.label}
                    rightSlot={
                        <div className="flex items-center gap-2">
                            {activeTool !== 'home' && (
                                <button type="button" onClick={() => handleToolSelect('home')} className="p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-gray-400 transition-colors" title="Dashboard">
                                    <LayoutGrid size={20} />
                                </button>
                            )}
                            <button
                                type="button"
                                onClick={() => setIsMenuOpen(true)}
                                className="md:hidden p-2 bg-gray-800 hover:bg-gray-700 rounded-lg text-indigo-400 transition-colors"
                            >
                                <Menu size={24} />
                            </button>
                        </div>
                    }
                />

                <main className="flex-1 overflow-y-auto overflow-x-hidden relative p-0 custom-scrollbar">
                    {activeTool === 'home' && (
                        <div className="min-h-full p-6 animate-fadeIn">
                            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
                                <h2 className="text-2xl font-black text-gray-700 uppercase italic tracking-widest text-center sm:text-left">
                                    Strumenti Staff
                                </h2>
                                {canEditDashboardLayout && (
                                    <button
                                        type="button"
                                        onClick={() => setLayoutEditorOpen(true)}
                                        className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-violet-700 hover:bg-violet-600 text-white text-xs font-black uppercase tracking-wider shadow-lg shadow-violet-900/30 transition-colors"
                                    >
                                        <LayoutList size={18} />
                                        Organizza menu staff
                                    </button>
                                )}
                            </div>
                            <div className="mb-6 p-4 rounded-xl border border-indigo-500/30 bg-gray-900/70">
                                <h3 className="text-sm font-black uppercase tracking-wider text-indigo-300 mb-3">Manuale Wiki PDF</h3>
                                <div className="flex flex-col md:flex-row md:items-center gap-3">
                                    <button
                                        type="button"
                                        onClick={handleGenerateWikiPdf}
                                        disabled={pdfGenerating}
                                        className={`px-4 py-2 rounded-lg font-bold text-sm transition-colors ${pdfGenerating ? 'bg-gray-700 text-gray-300 cursor-not-allowed' : 'bg-indigo-600 text-white hover:bg-indigo-500'}`}
                                    >
                                        {pdfGenerating ? 'Generazione in corso...' : 'Genera Ultimo Manuale PDF'}
                                    </button>
                                    <a
                                        href={getWikiManualLatestPdfUrl()}
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        className="px-4 py-2 rounded-lg font-bold text-sm border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 transition-colors text-center"
                                    >
                                        Scarica Ultimo PDF
                                    </a>
                                </div>
                                {pdfGenMessage && (
                                    <p className="mt-2 text-xs text-gray-300">{pdfGenMessage}</p>
                                )}
                            </div>

                            {menuStructure.pinned.length > 0 && (
                                <section className="mb-8">
                                    <h3 className="text-xs font-black uppercase tracking-widest text-indigo-400 mb-3">Accesso rapido</h3>
                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                                        {menuStructure.pinned.map((tool) => (
                                            <button
                                                key={tool.id}
                                                type="button"
                                                onClick={() => handleToolSelect(tool.id)}
                                                className={`${tool.color} p-6 rounded-2xl shadow-xl hover:scale-[1.02] hover:shadow-2xl transition-all duration-200 flex flex-col items-center justify-center gap-4 aspect-square border-t border-white/10 group relative overflow-hidden active:scale-95`}
                                            >
                                                <div className="absolute inset-0 bg-linear-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                                <div className="text-white drop-shadow-md transform group-hover:-translate-y-1 transition-transform duration-300 z-10">
                                                    {React.createElement(tool.icon, { size: 40 })}
                                                </div>
                                                <span className="font-black text-white uppercase tracking-wider text-xs text-center z-10">{tool.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                </section>
                            )}

                            {menuStructure.sections.map((section) => (
                                <section key={section.id} className="mb-8">
                                    <h3 className="text-xs font-black uppercase tracking-widest text-gray-500 mb-3 flex items-center gap-2">
                                        <span className={`w-2 h-2 rounded-full shrink-0 ${section.tools[0]?.color || 'bg-slate-600'}`} />
                                        <section.icon size={14} className="text-gray-600" />
                                        {section.label}
                                    </h3>
                                    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                                        {section.tools.map((tool) => (
                                            <button
                                                key={tool.id}
                                                type="button"
                                                onClick={() => handleToolSelect(tool.id)}
                                                className={`${tool.color} p-6 rounded-2xl shadow-xl hover:scale-[1.02] hover:shadow-2xl transition-all duration-200 flex flex-col items-center justify-center gap-4 aspect-square border-t border-white/10 group relative overflow-hidden active:scale-95`}
                                            >
                                                <div className="absolute inset-0 bg-linear-to-br from-white/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300" />
                                                <div className="text-white drop-shadow-md transform group-hover:-translate-y-1 transition-transform duration-300 z-10">
                                                    {React.createElement(tool.icon, { size: 40 })}
                                                </div>
                                                <span className="font-black text-white uppercase tracking-wider text-xs text-center z-10">{tool.label}</span>
                                            </button>
                                        ))}
                                    </div>
                                </section>
                            ))}

                            <section className="mb-4">
                                <h3 className="text-xs font-black uppercase tracking-widest text-gray-500 mb-3">Collegamenti</h3>
                                <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
                                    <button
                                        type="button"
                                        onClick={onSwitchToPlayer}
                                        className="bg-gray-800 border-2 border-dashed border-gray-700 p-6 rounded-2xl hover:bg-gray-750 hover:border-gray-500 transition-all flex flex-col items-center justify-center gap-4 aspect-square group"
                                    >
                                        <Users size={40} className="text-gray-600 group-hover:text-gray-300 transition-colors" />
                                        <span className="font-bold text-gray-500 group-hover:text-white uppercase tracking-wider text-xs text-center">Vai a Personaggi</span>
                                    </button>
                                    <Link
                                        to="/"
                                        className="bg-gray-800 border-2 border-dashed border-gray-700 p-6 rounded-2xl hover:bg-gray-750 hover:border-gray-500 transition-all flex flex-col items-center justify-center gap-4 aspect-square group"
                                    >
                                        <BookOpen size={40} className="text-gray-600 group-hover:text-gray-300 transition-colors" />
                                        <span className="font-bold text-gray-500 group-hover:text-white uppercase tracking-wider text-xs text-center">Vai alla Wiki</span>
                                    </Link>
                                    <Link
                                        to="/app/social"
                                        className="bg-gray-800 border-2 border-dashed border-gray-700 p-6 rounded-2xl hover:bg-gray-750 hover:border-gray-500 transition-all flex flex-col items-center justify-center gap-4 aspect-square group"
                                    >
                                        <Sparkles size={40} className="text-gray-600 group-hover:text-pink-300 transition-colors" />
                                        <span className="font-bold text-gray-500 group-hover:text-white uppercase tracking-wider text-xs text-center">Apri InstaFame</span>
                                    </Link>
                                </div>
                            </section>
                        </div>
                    )}

                    {activeTool !== 'home' && (() => {
                        const tool = visibleTools.find((t) => t.id === activeTool);
                        if (!tool) return null;
                        const Component = tool.component;
                        if (DIRECT_LOAD_TOOLS.has(activeTool)) {
                            return (
                                <div className="h-full w-full flex flex-col animate-in slide-in-from-right-4 duration-300">
                                    <Component onLogout={onLogout} onBack={() => setActiveTool('home')} />
                                </div>
                            );
                        }
                        return (
                            <div className="h-full w-full flex flex-col animate-in slide-in-from-right-4 duration-300">
                                <Suspense fallback={<LoadingSpinner />}>
                                    <Component onLogout={onLogout} onBack={() => setActiveTool('home')} />
                                </Suspense>
                            </div>
                        );
                    })()}
                </main>
            </div>

            {layoutEditorOpen && (
                <StaffDashboardLayoutEditor
                    initialLayout={dashboardLayout}
                    onClose={() => setLayoutEditorOpen(false)}
                    onSaved={(layout) => {
                        setDashboardLayout(layout);
                        setLayoutEditorOpen(false);
                    }}
                    onLogout={onLogout}
                />
            )}
        </div>
    );
};

export default memo(StaffDashboard);
