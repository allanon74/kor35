/** Marker e layout immagini rubrica nel corpo articoli. */

export const RUBRICA_IMG_MARKER_RE =
  /\[\[rubrica-img:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})\]\]/g;

export const RUBRICA_IMG_LAYOUTS = [
  { id: 'full', label: 'Colonna' },
  { id: 'wide', label: 'Ampia' },
  { id: 'float_left', label: 'Sinistra' },
  { id: 'float_right', label: 'Destra' },
  { id: 'grid_pair', label: 'Metà' },
];

export const rubricaImgMarker = (id) => `[[rubrica-img:${id}]]`;

export const rubricaImgMarkerHtml = (id) =>
  `<p class="rubrica-img-marker">${rubricaImgMarker(id)}</p>`;

export const extractRubricaImgIds = (html) => {
  if (!html) return [];
  const ids = [];
  const re = new RegExp(RUBRICA_IMG_MARKER_RE.source, 'g');
  let match = re.exec(html);
  while (match) {
    ids.push(String(match[1]).toLowerCase());
    match = re.exec(html);
  }
  return ids;
};

/**
 * Spezza il corpo in segmenti HTML e slot immagine.
 * @returns {Array<{ type: 'html', html: string } | { type: 'image', id: string }>}
 */
export const splitCorpoByMarkers = (corpo) => {
  const text = String(corpo || '');
  if (!text) return [];
  const segments = [];
  const re = new RegExp(RUBRICA_IMG_MARKER_RE.source, 'g');
  let lastIndex = 0;
  let match = re.exec(text);
  while (match) {
    if (match.index > lastIndex) {
      segments.push({ type: 'html', html: text.slice(lastIndex, match.index) });
    }
    segments.push({ type: 'image', id: String(match[1]).toLowerCase() });
    lastIndex = match.index + match[0].length;
    match = re.exec(text);
  }
  if (lastIndex < text.length) {
    segments.push({ type: 'html', html: text.slice(lastIndex) });
  }
  return segments;
};

export const layoutFigureClass = (layout) => {
  switch (layout) {
    case 'wide':
      return 'rubrica-img rubrica-img--wide';
    case 'float_left':
      return 'rubrica-img rubrica-img--float-left';
    case 'float_right':
      return 'rubrica-img rubrica-img--float-right';
    case 'grid_pair':
      return 'rubrica-img rubrica-img--grid-pair';
    default:
      return 'rubrica-img rubrica-img--full';
  }
};
