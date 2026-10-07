/** Costo forfait per riportare l'oggetto al massimo, indipendente dalle cariche mancanti. */
export function dettaglioRicarica(item) {
  const massime = Number(item?.cariche_massime || 0);
  const attuali = Number(item?.cariche_attuali || 0);
  const unitario = Number(item?.costo_ricarica || 0);
  const mancanti = Number.isFinite(massime) && Number.isFinite(attuali)
    ? Math.max(0, massime - attuali)
    : 0;
  const unit = Number.isFinite(unitario) ? unitario : 0;
  return {
    mancanti,
    unitario: unit,
    totale: mancanti > 0 ? unit : 0,
  };
}

export function patchCaricheInOggetti(oggetti, oggettoId, updater) {
  const id = String(oggettoId);
  return (oggetti || []).map((obj) => {
    if (String(obj.id) === id) return updater(obj);
    const mods = obj.potenziamenti_installati;
    if (!Array.isArray(mods) || mods.length === 0) return obj;
    let changed = false;
    const nextMods = mods.map((mod) => {
      if (String(mod.id) !== id) return mod;
      changed = true;
      return updater(mod);
    });
    return changed ? { ...obj, potenziamenti_installati: nextMods } : obj;
  });
}

export function findOggettoInInventario(oggetti, oggettoId) {
  const id = String(oggettoId);
  for (const obj of oggetti || []) {
    if (String(obj.id) === id) return obj;
    const nested = (obj.potenziamenti_installati || []).find((mod) => String(mod.id) === id);
    if (nested) return nested;
  }
  return null;
}
