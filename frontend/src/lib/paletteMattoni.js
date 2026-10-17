/**
 * Palette dei mattoni in visualizzazione.
 * Il database salva solo la caratteristica: il nome («Fuoco (DEX)») dipende dall'aura.
 *
 * Aura primaria che consente solo se stessa (Tecnologica, Innata): mattoni suoi.
 * Aura primaria che consente altre aure (Trasmutatore, Alchimia): mattoni dell'aura di infusione.
 */

export function auraDelegaMattoni(aura) {
  if (!aura) return false;
  const ids = aura.aure_infusione_consentite || [];
  return ids.some((id) => String(id) !== String(aura.id));
}

export function paletteAuraId({ isInfusion = false, primaria = null, secondariaId = null } = {}) {
  if (!isInfusion) {
    return primaria?.id ?? null;
  }
  if (auraDelegaMattoni(primaria)) {
    return secondariaId || null;
  }
  return primaria?.id ?? null;
}

export function etichettaMattone(nome, sigla) {
  const n = String(nome || '').trim();
  const s = String(sigla || '').trim();
  if (n && s) return `${n} (${s})`;
  return n || s;
}
