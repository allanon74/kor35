/** Limite nickname InstaFame — allineato a backend/social/nickname_validation.py */
export const NICKNAME_MAX_GRAPHEMES = 40;

const segmenter =
  typeof Intl !== 'undefined' && Intl.Segmenter
    ? new Intl.Segmenter('it', { granularity: 'grapheme' })
    : null;

export function countGraphemes(text) {
  const value = String(text ?? '');
  if (!value) return 0;
  if (segmenter) {
    return [...segmenter.segment(value)].length;
  }
  return [...value].length;
}

export function truncateToGraphemes(text, max = NICKNAME_MAX_GRAPHEMES) {
  const value = String(text ?? '');
  if (!value || countGraphemes(value) <= max) return value;
  if (segmenter) {
    let out = '';
    let n = 0;
    for (const part of segmenter.segment(value)) {
      if (n >= max) break;
      out += part.segment;
      n += 1;
    }
    return out;
  }
  return [...value].slice(0, max).join('');
}
