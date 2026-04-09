import React, { useMemo, useState } from 'react';
import { Dialog, DialogBackdrop, DialogPanel } from '@headlessui/react';
import { X } from 'lucide-react';
import PunteggioDisplay from '../PunteggioDisplay';
import { resolveMediaUrl } from '../../api';

/** Colori hex dalla scheda (caratteristica 1, 2, 3) per sfondo header */
function getAbilityColors(item) {
  const out = [];
  if (item.caratteristica?.colore) out.push(normalizeHex(item.caratteristica.colore));
  if (item.caratteristica_2?.colore) out.push(normalizeHex(item.caratteristica_2.colore));
  if (item.caratteristica_3?.colore) out.push(normalizeHex(item.caratteristica_3.colore));
  return out;
}

function normalizeHex(v) {
  const s = String(v).trim();
  return s.startsWith('#') ? s : `#${s}`;
}

function gradientStyle(colors) {
  if (!Array.isArray(colors) || colors.length === 0) return null;
  const list = colors.filter(c => c && String(c).trim());
  if (list.length === 0) return null;
  if (list.length === 1) return list[0];
  return `linear-gradient(135deg, ${list.join(', ')})`;
}

function isColorDark(hex) {
  if (!hex) return false;
  const clean = String(hex).trim().replace(/^#/, '');
  if (clean.length !== 6) return false;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
  return luminance < 150;
}

function isGradientDark(colors) {
  if (!Array.isArray(colors) || colors.length === 0) return false;
  const valid = colors.map(c => String(c).trim()).filter(Boolean);
  if (valid.length === 0) return false;
  const darkCount = valid.filter(isColorDark).length;
  return darkCount >= valid.length / 2;
}

function getItemHeaderStyle(item, chromaticStyle) {
  const colors = getAbilityColors(item);
  if (colors.length === 0) {
    const headerStyleOverride = chromaticStyle?.headerStyle;
    const headerBgColor = chromaticStyle?.headerBgColor;
    const headerTextColor = chromaticStyle?.headerTextColor;
    if (headerStyleOverride) return headerStyleOverride;
    if (headerBgColor != null && headerTextColor != null) return { background: headerBgColor, color: headerTextColor };
    return undefined;
  }
  const bg = colors.length === 1 ? colors[0] : gradientStyle(colors);
  const textColor = colors.length === 1
    ? (isColorDark(colors[0]) ? '#ffffff' : '#111827')
    : (isGradientDark(colors) ? '#ffffff' : '#111827');
  return { background: bg, color: textColor };
}

function getItemIsDark(item) {
  const colors = getAbilityColors(item);
  if (colors.length === 0) return false;
  if (colors.length === 1) return isColorDark(colors[0]);
  return isGradientDark(colors);
}

function getAbilityCostLine(item) {
  const pcRaw = item?.costo_pc_calc ?? item?.costo_pc ?? 0;
  const crRaw = item?.costo_crediti_calc ?? item?.costo_crediti ?? 0;
  const pc = Number(pcRaw) || 0;
  const cr = Number(crRaw) || 0;

  const hasExplicitCosts =
    item?.costo_pc_calc != null ||
    item?.costo_crediti_calc != null ||
    item?.costo_pc != null ||
    item?.costo_crediti != null;

  // Se abbiamo i campi costo_* usiamo la logica combinata richiesta.
  if (hasExplicitCosts) {
    if (pc <= 0 && cr <= 0) return null;
    const parts = [];
    if (pc > 0) parts.push(`${pc} PC`);
    if (cr > 0) parts.push(`${cr} Cr`);
    return `Costo: ${parts.join(' + ')}`;
  }

  // Fallback (es. API wiki legacy): costo già formattato dal backend
  const raw = item?.costo;
  if (raw == null) return null;
  const s = String(raw).trim();
  if (!s || s === '0') return null;
  return /^costo\s*:/i.test(s) ? s : `Costo: ${s}`;
}

export default function AbilitaTable({ list, chromaticStyle, soloList = false }) {
  const [selectedAbility, setSelectedAbility] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);

  const cardBorder = chromaticStyle?.border ?? 'border-gray-200';
  const headerBg = chromaticStyle?.headerBg ?? 'bg-gray-50';
  const headerText = chromaticStyle?.headerText ?? 'text-red-900';
  const bodyBg = chromaticStyle?.bg ?? null;
  const bodyText = chromaticStyle?.text ?? 'text-gray-700';
  const bodyClass = bodyBg ? `bg-gradient-to-b ${bodyBg} ${bodyText}` : bodyText;
  const bodyTextColor = chromaticStyle?.bodyTextColor;
  const bodyStyle = bodyTextColor ? { color: bodyTextColor } : undefined;

  const cardHeaderClass = 'px-3 py-2 border-b border-gray-100 flex justify-between items-center gap-2';

  const openAbility = (item) => {
    setSelectedAbility(item);
    setIsModalOpen(true);
  };

  const closeAbility = () => {
    setIsModalOpen(false);
    setSelectedAbility(null);
  };

  const abilityListItems = useMemo(() => {
    if (!list || list.length === 0) return null;
    return list.map((item) => {
      const headerStyle = getItemHeaderStyle(item, chromaticStyle);
      const isDark = getItemIsDark(item);
      const iconFilter = isDark ? 'brightness(0) invert(1)' : 'brightness(0)';
      const iconBoxClass = isDark ? 'bg-white/20' : 'bg-black/10';
      const iconUrl = resolveMediaUrl(item?.caratteristica?.icona_url);
      const iconTextColor = headerStyle?.color ?? (isDark ? '#ffffff' : '#111827');
      const costLine = getAbilityCostLine(item);

      return (
        <button
          key={item.id}
          type="button"
          onClick={() => openAbility(item)}
          className={`w-full text-left bg-white border ${cardBorder} rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden break-inside-avoid`}
        >
          <div className="flex items-center gap-3 p-3" style={headerStyle || undefined}>
            <div className={`h-8 w-8 rounded flex items-center justify-center ${iconBoxClass} shrink-0 overflow-hidden`}>
              {iconUrl ? (
                <img
                  src={iconUrl}
                  alt=""
                  className="h-6 w-6 object-contain p-0.5"
                  style={{ filter: iconFilter }}
                  loading="lazy"
                />
              ) : (
                <span style={{ color: iconTextColor, fontWeight: 800, fontSize: 12 }}>
                  {String(item?.caratteristica?.sigla || item?.caratteristica?.nome || item.nome || '?').slice(0, 1).toUpperCase()}
                </span>
              )}
            </div>
            <div className="min-w-0 flex flex-col">
              <span className="font-bold text-sm md:text-base leading-tight truncate" style={{ color: iconTextColor }}>
                {item.nome}
              </span>
              {costLine && (
                <span className="text-[10px] md:text-xs opacity-80 leading-tight mt-0.5" style={{ color: iconTextColor }}>
                  {costLine}
                </span>
              )}
            </div>
          </div>
        </button>
      );
    });
  }, [list, chromaticStyle, cardBorder]);

  if (!list || list.length === 0) return <p className="text-gray-500 italic text-sm p-2">Nessuna abilità elencata.</p>;

  return (
    <>
      {soloList ? (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-2">
          {abilityListItems}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-2">
          {list.map((item) => {
            const cardHeaderStyle = getItemHeaderStyle(item, chromaticStyle);
            const costLine = getAbilityCostLine(item);
            return (
              <div
                key={item.id}
                className={`bg-white border ${cardBorder} rounded-lg shadow-sm flex flex-col overflow-hidden hover:shadow-md transition-shadow break-inside-avoid`}
              >
                <div
                  className={cardHeaderStyle ? cardHeaderClass : `${cardHeaderClass} ${headerBg} ${headerText}`}
                  style={cardHeaderStyle || undefined}
                >
                  <div className="min-w-0 flex flex-col">
                    <span className="font-bold text-sm md:text-base leading-tight truncate">
                      {item.nome}
                    </span>
                    {costLine && (
                      <span className="text-[10px] md:text-xs opacity-80 leading-tight mt-0.5">
                        {costLine}
                      </span>
                    )}
                  </div>
                </div>

                <div
                  className={`p-3 text-xs md:text-sm relative ${bodyClass} prose prose-sm max-w-none leading-snug prose-p:my-1`}
                  style={bodyStyle}
                >
                  {/* Badge caratteristiche 1, 2, 3 (se valorizzate) */}
                  {(item.caratteristica || item.caratteristica_2 || item.caratteristica_3) && (
                    <div className="float-right ml-2 mb-1 flex flex-wrap gap-1 justify-end">
                      {item.caratteristica && typeof item.caratteristica === 'object' && (
                        <PunteggioDisplay punteggio={item.caratteristica} value={null} size="badge" readOnly={true} iconType="inv_circle" />
                      )}
                      {item.caratteristica_2 && typeof item.caratteristica_2 === 'object' && (
                        <PunteggioDisplay punteggio={item.caratteristica_2} value={null} size="badge" readOnly={true} iconType="inv_circle" />
                      )}
                      {item.caratteristica_3 && typeof item.caratteristica_3 === 'object' && (
                        <PunteggioDisplay punteggio={item.caratteristica_3} value={null} size="badge" readOnly={true} iconType="inv_circle" />
                      )}
                    </div>
                  )}

                  <div
                    className="prose prose-sm max-w-none leading-snug prose-inherit"
                    dangerouslySetInnerHTML={{ __html: item.descrizione || '' }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}

      <Dialog open={isModalOpen} onClose={closeAbility} className="relative z-50">
        <DialogBackdrop className="fixed inset-0 bg-black/80" />
        <div className="fixed inset-0 flex items-center justify-center p-4">
          <DialogPanel className="w-full max-w-2xl rounded-lg bg-white shadow-2xl border border-gray-200 overflow-hidden">
            {selectedAbility && (
              <>
                {/*
                  Header per-item con testo chiaro/scuro in base al colore (o gradiente).
                  È lo stesso stile usato nelle card, ma rimpicciolito/centralizzato per il modal.
                */}
                {(() => {
                  const headerStyle = getItemHeaderStyle(selectedAbility, chromaticStyle);
                  const isDark = getItemIsDark(selectedAbility);
                  const iconFilter = isDark ? 'brightness(0) invert(1)' : 'brightness(0)';
                  const iconBoxClass = isDark ? 'bg-white/20' : 'bg-black/10';
                  const iconUrl = resolveMediaUrl(selectedAbility?.caratteristica?.icona_url);
                  const headerTextColor = headerStyle?.color ?? (isDark ? '#ffffff' : '#111827');
                  const costLine = getAbilityCostLine(selectedAbility);
                  return (
                    <div style={headerStyle || undefined} className="px-4 py-3 border-b border-white/10">
                      <div className="flex items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className={`h-10 w-10 rounded flex items-center justify-center ${iconBoxClass} shrink-0 overflow-hidden`}>
                            {iconUrl ? (
                              <img
                                src={iconUrl}
                                alt=""
                                className="h-8 w-8 object-contain p-0.5"
                                style={{ filter: iconFilter }}
                                loading="lazy"
                              />
                            ) : (
                              <span style={{ color: headerTextColor, fontWeight: 800, fontSize: 14 }}>
                                {String(selectedAbility?.caratteristica?.sigla || selectedAbility?.caratteristica?.nome || selectedAbility.nome || '?').slice(0, 1).toUpperCase()}
                              </span>
                            )}
                          </div>
                          <div className="min-w-0">
                            <div className="font-bold text-lg leading-tight truncate" style={{ color: headerTextColor }}>
                              {selectedAbility.nome}
                            </div>
                            {costLine && (
                              <div className="text-xs" style={{ color: headerTextColor, opacity: 0.9 }}>
                                {costLine}
                              </div>
                            )}
                          </div>
                        </div>

                        <button
                          type="button"
                          onClick={closeAbility}
                          className="p-2 rounded hover:brightness-110 transition-colors"
                          aria-label="Chiudi"
                        >
                          <X size={18} />
                        </button>
                      </div>
                    </div>
                  );
                })()}

                <div className={`p-4 text-xs md:text-sm relative ${bodyClass} prose prose-sm max-w-none leading-snug prose-p:my-1`} style={bodyStyle}>
                  {/* Badge caratteristiche 1, 2, 3 */}
                  {(selectedAbility.caratteristica || selectedAbility.caratteristica_2 || selectedAbility.caratteristica_3) && (
                    <div className="flex flex-wrap gap-2 justify-end mb-2">
                      {selectedAbility.caratteristica && (
                        <PunteggioDisplay punteggio={selectedAbility.caratteristica} value={null} size="badge" readOnly={true} iconType="inv_circle" />
                      )}
                      {selectedAbility.caratteristica_2 && (
                        <PunteggioDisplay punteggio={selectedAbility.caratteristica_2} value={null} size="badge" readOnly={true} iconType="inv_circle" />
                      )}
                      {selectedAbility.caratteristica_3 && (
                        <PunteggioDisplay punteggio={selectedAbility.caratteristica_3} value={null} size="badge" readOnly={true} iconType="inv_circle" />
                      )}
                    </div>
                  )}

                  <div
                    className="prose prose-sm max-w-none leading-snug prose-inherit"
                    dangerouslySetInnerHTML={{ __html: selectedAbility.descrizione || '' }}
                  />
                </div>
              </>
            )}
          </DialogPanel>
        </div>
      </Dialog>
    </>
  );
}