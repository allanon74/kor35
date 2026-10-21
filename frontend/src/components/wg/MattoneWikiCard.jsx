import { resolveMediaUrl } from '../../api';
import RichHtml from '../RichHtml';

/**
 * Scheda mattone con gli stessi colori e la stessa struttura del widget wiki.
 * Se onMattoneClick è valorizzato, toccare l'intestazione (il mattone) chiude il popup.
 */
const MATTONE_COLOR_HEX = {
  porpora: '#860050',
  red: '#fa0000',
  rosso: '#fa0000',
  ochre: '#c79e0b',
  ocra: '#c79e0b',
  gray: '#b6cdd9',
  grigio: '#b6cdd9',
  blue: '#135cd1',
  blu: '#135cd1',
  white: '#ffffff',
  bianco: '#ffffff',
  purple: '#efaaff',
  viola: '#efaaff',
  green: '#92fa88',
  verde: '#92fa88',
  black: '#000000',
  nero: '#000000',
  yellow: '#faf610',
  giallo: '#faf610',
  default: '#b6cdd9',
};
const HEX_ALIASES = {
  '#860050': '#860050', '#fa0000': '#fa0000', '#c79e0b': '#c79e0b', '#b6cdd9': '#b6cdd9',
  '#135cd1': '#135cd1', '#ffffff': '#ffffff', '#efaaff': '#efaaff', '#92fa88': '#92fa88',
  '#000000': '#000000', '#faf610': '#faf610',
};

function normalizeHex(h) {
  if (h == null || h === '') return '';
  const s = String(h).trim().toLowerCase();
  return s.startsWith('#') ? s : `#${s}`;
}

function isColorDark(hex) {
  if (!hex) return false;
  const clean = String(hex).trim().replace('#', '');
  if (clean.length !== 6) return false;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
  return luminance < 150;
}

function getHeaderHex(colore) {
  const raw = (colore != null ? String(colore).trim() : '').toLowerCase();
  if (!raw) return MATTONE_COLOR_HEX.default;
  const withHash = normalizeHex(raw);
  if (HEX_ALIASES[withHash]) return HEX_ALIASES[withHash];
  const noHash = withHash.replace(/^#/, '');
  for (const [h, hex] of Object.entries(HEX_ALIASES)) {
    if (h.replace('#', '') === noHash) return hex;
  }
  if (/^#[0-9a-f]{6}$/.test(withHash)) return withHash;
  return MATTONE_COLOR_HEX[raw] || MATTONE_COLOR_HEX.default;
}

function cardStyleForMattone(colore) {
  const headerHex = getHeaderHex(colore);
  const darkBg = isColorDark(headerHex);
  const headerTextColor = darkBg ? '#ffffff' : '#111827';
  const iconFilter = darkBg ? 'brightness(0) invert(1)' : 'brightness(0)';
  const iconBoxClass = darkBg ? 'bg-white/20' : 'bg-black/10';
  return {
    headerStyle: { background: headerHex, color: headerTextColor },
    iconFilter,
    iconBoxClass,
    bodyClass: 'p-3 text-xs md:text-sm text-gray-800 bg-gray-50 prose prose-sm max-w-none leading-snug prose-p:my-1',
  };
}

function safeText(v) {
  return v == null ? '' : String(v);
}

function iconUrlForMattone(m) {
  return m?.icona_url || m?.aura?.icona_url || m?.caratteristica_associata?.icona_url || null;
}

export default function MattoneWikiCard({ mattone, onMattoneClick }) {
  const m = mattone || {};
  const { headerStyle, bodyClass, iconFilter, iconBoxClass } = cardStyleForMattone(m.colore);
  const iconUrl = resolveMediaUrl(iconUrlForMattone(m));
  const auraName = m?.aura?.nome || '—';
  const carName = m?.caratteristica_associata?.nome || '—';
  const tipoLabel = m?.tipo_display || m?.tipo || '—';
  const descrizione = m?.descrizione_mattone || m?.descrizione || '';
  const meta = m?.descrizione_metatalento || '';
  const mostraClassiArma = m?.mostra_classi_arma || 'nessuno';
  const classiArmaMateria = Array.isArray(m?.classi_arma_materia) ? m.classi_arma_materia : [];
  const classiArmaMod = Array.isArray(m?.classi_arma_mod) ? m.classi_arma_mod : [];
  const HeaderTag = onMattoneClick ? 'button' : 'div';

  return (
    <div className="bg-white border border-gray-300 rounded-lg shadow-sm flex flex-col overflow-hidden break-inside-avoid w-full min-w-0 text-left">
      <HeaderTag
        type={onMattoneClick ? 'button' : undefined}
        onClick={onMattoneClick}
        className="px-3 py-2 border-b border-gray-100 flex justify-between items-center gap-2 w-full min-h-11 text-left"
        style={headerStyle}
        aria-label={onMattoneClick ? `Chiudi ${m.nome || 'mattone'}` : undefined}
      >
        <div className="min-w-0 flex items-center gap-2">
          <div className={`shrink-0 rounded overflow-hidden ${iconBoxClass}`}>
            {iconUrl ? (
              <img
                src={iconUrl}
                alt=""
                className="h-7 w-7 object-contain p-0.5"
                style={{ filter: iconFilter }}
                loading="lazy"
              />
            ) : (
              <div className="h-7 w-7 flex items-center justify-center text-xs font-bold">
                {safeText(m?.sigla || m?.nome).slice(0, 1).toUpperCase()}
              </div>
            )}
          </div>
          <span className="font-bold text-sm md:text-base leading-tight break-words">
            {m.nome}
          </span>
        </div>
        <span className="text-xs font-mono bg-white/20 border border-current border-opacity-30 px-1.5 py-0.5 rounded whitespace-nowrap shrink-0">
          {tipoLabel}
        </span>
      </HeaderTag>

      <div className={`relative ${bodyClass}`}>
        <div className="mb-2 flex flex-wrap gap-2">
          <span className="text-[10px] md:text-xs bg-gray-200/90 border border-gray-300 px-2 py-0.5 rounded text-gray-800">
            Tipo: {tipoLabel}
          </span>
          <span className="text-[10px] md:text-xs bg-gray-200/90 border border-gray-300 px-2 py-0.5 rounded text-gray-800">
            Aura: {auraName}
          </span>
          <span className="text-[10px] md:text-xs bg-gray-200/90 border border-gray-300 px-2 py-0.5 rounded text-gray-800">
            Caratt.: {carName}
          </span>
        </div>

        {descrizione ? (
          <RichHtml
            content={descrizione}
            tone="onLight"
            className="prose prose-sm max-w-none leading-snug prose-inherit"
          />
        ) : (
          <p className="text-sm text-gray-600">Nessuna descrizione per questo mattone.</p>
        )}
        {meta ? (
          <div className="mt-3 border-t border-black/10 pt-2">
            <div className="text-[11px] md:text-xs font-bold opacity-80">Metatalento</div>
            <RichHtml
              content={meta}
              tone="onLight"
              className="prose prose-sm max-w-none leading-snug prose-inherit"
            />
          </div>
        ) : null}

        {mostraClassiArma === 'materia' && classiArmaMateria.length > 0 && (
          <div className="mt-3 border-t border-black/10 pt-2">
            <div className="text-[11px] md:text-xs font-bold opacity-80">Classi di armi con questo castone</div>
            <ul className="mt-1 text-xs md:text-sm text-gray-800 list-disc list-inside space-y-0.5">
              {classiArmaMateria.map((c) => (
                <li key={c.id}>{c.nome}</li>
              ))}
            </ul>
          </div>
        )}

        {mostraClassiArma === 'mod' && classiArmaMod.length > 0 && (
          <div className="mt-3 border-t border-black/10 pt-2">
            <div className="text-[11px] md:text-xs font-bold opacity-80">Classi di armi con questo Nodo e massimale di mod installabili per tipologia di nodo</div>
            <ul className="mt-1 text-xs md:text-sm text-gray-800 space-y-0.5">
              {classiArmaMod.map((c) => (
                <li key={c.id}>
                  <span className="font-medium">{c.nome}</span>
                  {c.max_installabili != null && (
                    <span className="ml-1 text-gray-600">— max {c.max_installabili} mod</span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </div>
  );
}
