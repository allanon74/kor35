import {
  Map,
  Scroll,
  FlaskConical,
  Gavel,
  Feather,
  Shield,
  MessageSquare,
  ClipboardCheck,
  Skull,
  BookOpen,
  Layers,
  Globe2,
  Image,
  Package,
  QrCode,
  Sparkles,
  Gem,
  BookText,
  Navigation,
  Settings,
  Users,
} from 'lucide-react';

/** Icone consentite per i gruppi del menu (allineate al backend). */
export const STAFF_GROUP_ICON_MAP = {
  Map,
  BookOpen,
  Users,
  MessageSquare,
  Settings,
  Layers,
  Globe2,
  Package,
  QrCode,
  Sparkles,
};

export const STAFF_TOOL_ICON_MAP = {
  Map,
  Scroll,
  FlaskConical,
  Gavel,
  Feather,
  Shield,
  MessageSquare,
  ClipboardCheck,
  Skull,
  BookOpen,
  Layers,
  Globe2,
  Image,
  Package,
  QrCode,
  Sparkles,
  Gem,
  BookText,
  Navigation,
  Settings,
  Users,
};

/**
 * Metadati statici degli strumenti staff (componenti lazy in StaffDashboard).
 * @type {Record<string, { id: string, label: string, icon: import('react').ComponentType, color: string, componentKey: string }>}
 */
export const STAFF_TOOLS_REGISTRY = {
  plot: { id: 'plot', label: 'Gestione plot', icon: Map, color: 'bg-indigo-600', componentKey: 'plot' },
  'qr-debug': { id: 'qr-debug', label: 'QR debug', icon: QrCode, color: 'bg-yellow-600', componentKey: 'qr-debug' },
  mostri: { id: 'mostri', label: 'Mostri', icon: Skull, color: 'bg-red-700', componentKey: 'mostri' },
  abilita: { id: 'abilita', label: 'Abilità', icon: BookOpen, color: 'bg-blue-700', componentKey: 'abilita' },
  cerimoniali: { id: 'cerimoniali', label: 'Cerimoniali', icon: Scroll, color: 'bg-amber-700', componentKey: 'cerimoniali' },
  tessiture: { id: 'tessiture', label: 'Tessiture', icon: Feather, color: 'bg-cyan-700', componentKey: 'tessiture' },
  infusioni: { id: 'infusioni', label: 'Infusioni', icon: FlaskConical, color: 'bg-purple-700', componentKey: 'infusioni' },
  proposte: { id: 'proposte', label: 'Valutazione proposte', icon: ClipboardCheck, color: 'bg-orange-600', componentKey: 'proposte' },
  oggetti: { id: 'oggetti', label: 'Oggetti', icon: Gavel, color: 'bg-stone-600', componentKey: 'oggetti' },
  'oggetti-base': { id: 'oggetti-base', label: 'Oggetti base', icon: Shield, color: 'bg-stone-800', componentKey: 'oggetti-base' },
  tabelle: { id: 'tabelle', label: 'Tabelle', icon: Layers, color: 'bg-pink-700', componentKey: 'tabelle' },
  immagini: { id: 'immagini', label: 'Immagini wiki', icon: Image, color: 'bg-teal-700', componentKey: 'immagini' },
  inventari: { id: 'inventari', label: 'Inventari', icon: Package, color: 'bg-slate-700', componentKey: 'inventari' },
  manifesti: { id: 'manifesti', label: 'QR — Manifesti', icon: BookText, color: 'bg-amber-900', componentKey: 'manifesti' },
  nodi: { id: 'nodi', label: 'QR — Nodi', icon: Sparkles, color: 'bg-cyan-900', componentKey: 'nodi' },
  'innesco-timer': { id: 'innesco-timer', label: 'QR — Innesco timer', icon: Sparkles, color: 'bg-orange-900', componentKey: 'innesco-timer' },
  pilotaggio: { id: 'pilotaggio', label: 'Console pilotaggio', icon: Navigation, color: 'bg-sky-700', componentKey: 'pilotaggio' },
  'effetti-casuali': { id: 'effetti-casuali', label: 'Effetti casuali', icon: Sparkles, color: 'bg-amber-700', componentKey: 'effetti-casuali' },
  'social-report': { id: 'social-report', label: 'Report social eventi', icon: Sparkles, color: 'bg-fuchsia-700', componentKey: 'social-report' },
  'risorse-pool': { id: 'risorse-pool', label: 'Risorse pool (Fortuna)', icon: Gem, color: 'bg-amber-800', componentKey: 'risorse-pool' },
  'ere-prefetture': { id: 'ere-prefetture', label: 'Ere e prefetture', icon: Globe2, color: 'bg-violet-700', componentKey: 'ere-prefetture' },
  'creazione-guidata': { id: 'creazione-guidata', label: 'Creazione guidata PG', icon: Sparkles, color: 'bg-violet-900', componentKey: 'creazione-guidata' },
  'dichiarazioni-glossario': { id: 'dichiarazioni-glossario', label: 'Dichiarazioni e glossario', icon: BookText, color: 'bg-emerald-700', componentKey: 'dichiarazioni-glossario' },
  'arcana-profiles': { id: 'arcana-profiles', label: 'Profili Arcana SSO', icon: Shield, color: 'bg-indigo-800', componentKey: 'arcana-profiles' },
  campagne: { id: 'campagne', label: 'Campagne', icon: Globe2, color: 'bg-emerald-800', componentKey: 'campagne' },
  maintenance: { id: 'maintenance', label: 'Maintenance mode', icon: Shield, color: 'bg-amber-700', componentKey: 'maintenance' },
  messaggi: { id: 'messaggi', label: 'Messaggi staff', icon: MessageSquare, color: 'bg-emerald-600', componentKey: 'messaggi' },
};

export const DEFAULT_STAFF_DASHBOARD_LAYOUT = {
  version: 1,
  tool_labels: {},
  groups: [
    {
      id: 'evento',
      label: 'Evento in campo',
      icon: 'Map',
      palette: 'indigo',
      order: 0,
      collapsed_default: false,
      tool_ids: ['plot', 'pilotaggio', 'manifesti', 'nodi', 'innesco-timer', 'qr-debug'],
    },
    {
      id: 'database',
      label: 'Database regole',
      icon: 'BookOpen',
      palette: 'blue',
      order: 1,
      collapsed_default: true,
      tool_ids: [
        'mostri', 'abilita', 'cerimoniali', 'tessiture', 'infusioni',
        'oggetti', 'oggetti-base', 'tabelle', 'effetti-casuali',
        'ere-prefetture', 'dichiarazioni-glossario',
      ],
    },
    {
      id: 'giocatori',
      label: 'Giocatori e contenuti',
      icon: 'Users',
      palette: 'teal',
      order: 2,
      collapsed_default: true,
      tool_ids: ['creazione-guidata', 'inventari', 'proposte', 'immagini', 'risorse-pool'],
    },
    {
      id: 'comunicazione',
      label: 'Comunicazione',
      icon: 'MessageSquare',
      palette: 'emerald',
      order: 3,
      collapsed_default: false,
      tool_ids: ['messaggi', 'social-report'],
    },
    {
      id: 'sistema',
      label: 'Sistema',
      icon: 'Settings',
      palette: 'slate',
      order: 4,
      collapsed_default: true,
      tool_ids: ['campagne', 'arcana-profiles', 'maintenance'],
    },
  ],
  pinned_tool_ids: ['plot', 'messaggi'],
};

const GLOBAL_ONLY_TOOLS = new Set(['arcana-profiles', 'campagne', 'maintenance']);
const STAFFER_TOOLS = new Set(['messaggi', 'plot']);
const MASTER_EXCLUDED = new Set(['campagne', 'arcana-profiles', 'maintenance']);
const HEAD_EXCLUDED = new Set(['arcana-profiles', 'maintenance']);

/**
 * Filtra gli id strumenti visibili in base al ruolo (stessa logica di StaffDashboard).
 */
export function getVisibleStaffToolIds({
  isGlobalSuperuser,
  isCampaignStaffer,
  isCampaignMaster,
  isCampaignHeadMaster,
}) {
  const allIds = Object.keys(STAFF_TOOLS_REGISTRY);
  if (isGlobalSuperuser && !isCampaignStaffer) {
    return allIds.filter((id) => GLOBAL_ONLY_TOOLS.has(id));
  }
  if (isCampaignStaffer && !isCampaignMaster && !isCampaignHeadMaster) {
    return allIds.filter((id) => STAFFER_TOOLS.has(id));
  }
  if (isCampaignMaster && !isCampaignHeadMaster && !isGlobalSuperuser) {
    return allIds.filter((id) => !MASTER_EXCLUDED.has(id));
  }
  if (isCampaignHeadMaster && !isGlobalSuperuser) {
    return allIds.filter((id) => !HEAD_EXCLUDED.has(id));
  }
  return allIds;
}

export function buildVisibleStaffTools(roleFlags, componentMap) {
  const ids = getVisibleStaffToolIds(roleFlags);
  return ids
    .map((id) => {
      const meta = STAFF_TOOLS_REGISTRY[id];
      if (!meta) return null;
      const component = componentMap[meta.componentKey];
      if (!component) return null;
      return {
        ...meta,
        component,
        // meta.icon è il componente Lucide (non JSX: file .js)
      };
    })
    .filter(Boolean);
}
