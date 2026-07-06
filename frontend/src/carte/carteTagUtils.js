/**
 * Etichette tag meccanici per visualizzazione carte.
 */

export function resolveCartaTagLabels(carta, tagsGlossary = []) {
  const raw = carta?.tags || [];
  if (!raw.length) return [];

  const byCodice = new Map(
    (tagsGlossary || []).map((t) => [
      String(t.codice || '').toUpperCase(),
      (t.nome || t.codice || '').trim(),
    ]),
  );

  return raw
    .map((t) => {
      if (typeof t === 'string') {
        const code = t.toUpperCase();
        return byCodice.get(code) || code;
      }
      return (t.nome || t.codice || '').trim();
    })
    .filter(Boolean);
}
