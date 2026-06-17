/** Allineato a social.models.HASHTAG_TOKEN_REGEX (backend). */
export const HASHTAG_BODY = String.raw`[A-Za-z0-9]+(?:[-_][A-Za-z0-9]+)*`;

/** Match #tag nel testo con delimitatore iniziale (per rendering cliccabile). */
export const HASHTAG_INLINE_REGEX = new RegExp(
  String.raw`(^|[\s.,;:!?()[\]{}])#(${HASHTAG_BODY})`,
  'g'
);

export const normalizeHashtagFilter = (tag) =>
  String(tag || '')
    .trim()
    .replace(/^#/, '')
    .toLowerCase();
