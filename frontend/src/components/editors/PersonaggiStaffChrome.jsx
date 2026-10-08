import React from 'react';
import {
  Award,
  Briefcase,
  Calendar,
  Coins,
  Dna,
  FileText,
  Mail,
  Package,
  QrCode,
  RotateCcw,
  ScrollText,
  Flame,
  Sparkles,
  StickyNote,
  Wand2,
  Wallet,
  Watch,
} from 'lucide-react';

export const PERSONAGGI_STAFF_TABS = [
  { id: 'bg', label: 'BG / Anagrafica', short: 'BG', icon: FileText },
  { id: 'qr', label: 'QR', short: 'QR', icon: QrCode },
  { id: 'membership', label: 'Carriere / KORP', short: 'KORP', icon: Briefcase },
  { id: 'abilita', label: 'Abilità', short: 'Abilità', icon: Award },
  { id: 'tecniche', label: 'Tecniche', short: 'Tecn.', icon: Flame },
  { id: 'razza-aura', label: 'Razza / Aura', short: 'Razza', icon: Dna },
  { id: 'risorse', label: 'Risorse', short: 'Risorse', icon: Coins },
  { id: 'economia', label: 'Economia', short: 'Eco', icon: Wallet },
  { id: 'inventario', label: 'Inventario', short: 'Inv.', icon: Package },
  { id: 'instafame', label: 'InstaFame', short: 'Fame', icon: Sparkles },
  { id: 'watch', label: 'Watch', short: 'Watch', icon: Watch },
  { id: 'log', label: 'Log / Diario', short: 'Log', icon: ScrollText },
  { id: 'eventi', label: 'Eventi', short: 'Eventi', icon: Calendar },
  { id: 'messaggio', label: 'Messaggio', short: 'Msg', icon: Mail },
  { id: 'creazione', label: 'Creazione guidata', short: 'Crea', icon: Wand2 },
  { id: 'note', label: 'Note master', short: 'Note', icon: StickyNote },
  { id: 'azioni', label: 'Azioni', short: 'Azioni', icon: RotateCcw },
];

export function personaggiExtraFiltersActive(filters) {
  if (!filters) return false;
  return (
    filters.tipo !== 'all' ||
    Boolean(filters.evento) ||
    Boolean(filters.era) ||
    Boolean(filters.carriera) ||
    (filters.morto && filters.morto !== 'vivo')
  );
}

/**
 * Tab della scheda personaggio: etichette corte su telefono, scorrimento orizzontale, tap ≥ 44px.
 */
export function PersonaggiStaffTabStrip({ tabs = PERSONAGGI_STAFF_TABS, active, onChange }) {
  return (
    <div
      data-testid="personaggi-staff-tabs"
      className="flex gap-1 overflow-x-auto overflow-y-hidden px-2 pb-2 pt-1"
    >
      {tabs.map(({ id, label, short, icon: Icon }) => {
        const isActive = active === id;
        return (
          <button
            key={id}
            type="button"
            onClick={() => onChange?.(id)}
            className={`inline-flex shrink-0 items-center gap-1.5 min-h-11 rounded-lg px-3 text-xs font-bold whitespace-nowrap ${
              isActive ? 'bg-teal-700 text-white' : 'bg-gray-800 text-gray-300'
            }`}
          >
            {Icon ? <Icon size={14} className="shrink-0" /> : null}
            <span className="sm:hidden">{short || label}</span>
            <span className="hidden sm:inline">{label}</span>
          </button>
        );
      })}
    </div>
  );
}

export function PersonaggiStaffDetailSubHeader({ nome, meta, tabs, active, onChange }) {
  return (
    <div data-testid="personaggi-staff-detail-header" className="min-w-0">
      <div className="px-3 pt-2 pb-1">
        <h3 className="text-base font-bold text-white break-words leading-snug">{nome}</h3>
        {meta ? <p className="mt-0.5 text-xs text-gray-400 break-words">{meta}</p> : null}
      </div>
      <PersonaggiStaffTabStrip tabs={tabs} active={active} onChange={onChange} />
    </div>
  );
}
