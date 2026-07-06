import React from 'react';
import { CreditCard, Sword, Heart, Gauge } from 'lucide-react';
import IconaPunteggio from '../components/IconaPunteggio';
import { resolveMediaUrl } from '../api';
import {
  CARTA_ENERGIA_LABEL,
  CARTA_RARITA_LABEL,
  CARTA_TIPO_LABEL,
} from './carteConstants';
import { useCardEnergyTheme } from './useCardEnergyTheme';
import CardRulesText from './CardRulesText';
import { LoreTextBlock } from './cardTextBlocks';

const SIZE_CLASS = {
  sm: 'w-[108px] min-h-[152px] text-[9px]',
  md: 'w-[168px] min-h-[236px] text-[10px]',
  lg: 'w-[220px] min-h-[308px] text-xs',
  xl: 'w-[min(100%,360px)] min-h-[500px] text-sm',
};

const ART_HEIGHT = {
  sm: 'h-14',
  md: 'h-24',
  lg: 'h-32',
  xl: 'h-52',
};

function CardStatBadges({ attacco, salute, iniziativa, compact = false }) {
  const iconSize = compact ? 10 : 12;
  const badgeClass =
    'inline-flex items-center gap-0.5 rounded-md border border-white/15 bg-black/45 px-1 py-0.5 text-[9px] font-bold text-gray-100';
  return (
    <div className="mx-2 mb-2 mt-1 flex flex-wrap justify-end gap-1">
      {attacco != null && (
        <span className={badgeClass} title="Attacco">
          <Sword size={iconSize} className="text-red-300" aria-hidden />
          <span>{attacco}</span>
        </span>
      )}
      {salute != null && (
        <span className={badgeClass} title="Salute">
          <Heart size={iconSize} className="text-rose-300" aria-hidden />
          <span>{salute}</span>
        </span>
      )}
      {iniziativa != null && (
        <span className={badgeClass} title="Iniziativa">
          <Gauge size={iconSize} className="text-sky-300" aria-hidden />
          <span>{iniziativa}</span>
        </span>
      )}
    </div>
  );
}

export default function CardFrame({
  item,
  carta: cartaProp,
  selected = false,
  onClick,
  compact = false,
  size: sizeProp,
  temaEnergie: temaProp,
  keywords = [],
  showRules = true,
  showLoreText = false,
  expandRules = false,
  rulesTextOverride = null,
  reliquiarioMode = false,
  onLoreExpand = null,
  loreClamp = true,
  className = '',
}) {
  const c = cartaProp || item?.carta || item;
  if (!c) return null;

  const size = sizeProp || (reliquiarioMode ? 'md' : (compact ? 'sm' : 'md'));
  const { getTheme, getFrameStyles } = useCardEnergyTheme(temaProp);
  const energy = getTheme(c.energia);
  const styles = getFrameStyles(c.energia);
  const img = c.immagine_url ? resolveMediaUrl(c.immagine_url) : null;
  const hasStats = c.attacco != null || c.salute != null || c.iniziativa != null;
  const rulesText = rulesTextOverride != null
    ? rulesTextOverride
    : (reliquiarioMode ? '—' : (c.testo_gioco || '—'));
  const rulesTextClass = expandRules
    ? 'text-[13px] leading-relaxed'
    : size === 'xl'
      ? 'text-xs leading-snug'
      : 'text-[10px] leading-snug';

  const inner = (
  <>
    <div
      className={`flex items-center justify-between gap-1 px-2 py-1 font-bold ${size === 'xl' ? 'py-2 text-base' : ''}`}
      style={styles.header}
    >
      <span
        className={`flex shrink-0 items-center justify-center rounded-full font-black ${size === 'xl' ? 'h-7 w-7 text-sm' : 'h-5 w-5 text-[10px]'}`}
        style={{ backgroundColor: 'rgba(0,0,0,0.25)', color: styles.header.color }}
      >
        {c.costo_gioco ?? 0}
      </span>
      <span className="min-w-0 flex-1 truncate text-center">{c.nome}</span>
      <span className="flex shrink-0 items-center gap-0.5">
        {energy.icona_url ? (
          <IconaPunteggio url={energy.icona_url} color={energy.colore} size="xs" mode="cerchio_inv" />
        ) : (
          <span className="rounded px-1 text-[8px] uppercase">{c.energia}</span>
        )}
      </span>
    </div>

    <div className={`relative mx-2 mt-2 overflow-hidden rounded-md border border-black/40 bg-black/30 ${ART_HEIGHT[size]}`}>
      {img ? (
        <img src={img} alt="" className="h-full w-full object-cover" />
      ) : (
        <div className="flex h-full items-center justify-center text-gray-600">
          <CreditCard size={compact ? 22 : 32} />
        </div>
      )}
      <div
        className="absolute bottom-0 left-0 right-0 px-1 py-0.5 text-[8px] font-bold uppercase tracking-wide"
        style={{ backgroundColor: 'rgba(0,0,0,0.55)', color: energy.colore }}
      >
        {CARTA_RARITA_LABEL[c.rarita] || c.rarita}
      </div>
    </div>

    <div
      className={`mx-2 mt-1.5 rounded border px-1.5 py-0.5 font-semibold uppercase tracking-wide ${size === 'xl' ? 'px-2 py-1 text-[11px]' : 'text-[8px]'}`}
      style={styles.typeLine}
    >
      {CARTA_TIPO_LABEL[c.tipo] || c.tipo}
      {' · '}
      {CARTA_ENERGIA_LABEL[c.energia] || energy.nome}
    </div>

    {showRules && (!compact || reliquiarioMode) && (
      <div
        className={`mx-2 mt-1.5 flex min-h-0 flex-1 flex-col rounded border px-2 py-2 ${expandRules ? 'overflow-y-auto' : ''} ${rulesTextClass}`}
        style={styles.rulesBox}
      >
        {reliquiarioMode && (
          <p className="mb-1 text-[8px] font-bold uppercase tracking-wide text-indigo-300/90">
            Abilità reliquiario
          </p>
        )}
        <div className={expandRules ? '' : 'line-clamp-4'}>
          <p className="whitespace-pre-wrap">
            <CardRulesText
              text={rulesText}
              keywords={keywords}
              maxLineLength={expandRules ? 120 : 90}
            />
          </p>
          {showLoreText && c.testo_lore?.trim() && (
            expandRules && !loreClamp ? (
              <p className="mt-2 whitespace-pre-wrap text-[12px] leading-relaxed italic text-gray-400/95">
                {c.testo_lore.trim()}
              </p>
            ) : (
              <LoreTextBlock
                text={c.testo_lore}
                onExpand={onLoreExpand}
              />
            )
          )}
        </div>
      </div>
    )}

    {hasStats && !reliquiarioMode && (
      <CardStatBadges
        attacco={c.attacco}
        salute={c.salute}
        iniziativa={c.iniziativa}
        compact={compact}
      />
    )}
  </>
  );

  const baseClass = `relative flex flex-col overflow-hidden rounded-xl border-[3px] text-left transition-transform ${SIZE_CLASS[size]} ${selected ? 'ring-2 ring-white/80 scale-[1.02]' : ''} ${onClick ? 'cursor-pointer hover:scale-[1.02]' : ''} ${className}`;

  if (onClick) {
    return (
      <button type="button" onClick={() => onClick(item || c)} className={baseClass} style={styles.wrapper}>
        {inner}
      </button>
    );
  }

  return (
    <div className={baseClass} style={styles.wrapper}>
      {inner}
    </div>
  );
}
