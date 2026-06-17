import React from 'react';
import { Crown, Gem, Star } from 'lucide-react';

const BADGE_CONFIG = {
  GOLD: {
    label: 'Utente Gold',
    textClass: 'text-amber-300',
    icons: [{ Icon: Star, key: 'star' }],
  },
  DIAMOND: {
    label: 'Utente Diamond',
    textClass: 'text-amber-300',
    icons: [
      { Icon: Gem, key: 'gem-l' },
      { Icon: Gem, key: 'gem-r' },
    ],
  },
  PREMIUM: {
    label: 'Utente Premium',
    textClass: 'text-slate-300',
    icons: [{ Icon: Crown, key: 'crown' }],
  },
};

export default function InstafameAuthorBadge({ badge, className = '', size = 'sm' }) {
  const key = String(badge || '').trim().toUpperCase();
  const cfg = BADGE_CONFIG[key];
  if (!cfg) return null;

  const textSize = size === 'md' ? 'text-[11px]' : 'text-[10px]';
  const iconSize = size === 'md' ? 12 : 11;
  const LeadingIcon = cfg.icons[0]?.Icon;
  const TrailingIcon = cfg.icons[1]?.Icon;

  return (
    <span
      className={`inline-flex items-center gap-1 font-semibold uppercase tracking-wide ${textSize} ${cfg.textClass} ${className}`}
    >
      {LeadingIcon && <LeadingIcon size={iconSize} className="shrink-0" aria-hidden />}
      <span>{cfg.label}</span>
      {TrailingIcon && <TrailingIcon size={iconSize} className="shrink-0" aria-hidden />}
    </span>
  );
}

export function InstafameSocialCariche({ cariche = [], className = '' }) {
  const rows = Array.isArray(cariche) ? cariche.filter((c) => c?.carica_nome) : [];
  if (!rows.length) return null;

  return (
    <ul className={`space-y-0.5 ${className}`}>
      {rows.map((row, idx) => (
        <li
          key={`${row.carriera_nome}-${row.carica_nome}-${idx}`}
          className="text-[11px] text-amber-100/85 leading-snug"
        >
          <span className="text-amber-200/70">{row.carriera_nome}</span>
          <span className="text-gray-500 mx-1">·</span>
          <span className="font-medium text-amber-50/90">{row.carica_nome}</span>
        </li>
      ))}
    </ul>
  );
}
