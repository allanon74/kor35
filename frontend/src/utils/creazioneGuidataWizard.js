/**
 * Logica condivisa wizard creazione guidata (effetti, trail SPA, rewind).
 */

export function getPayload(scelta) {
  const p = scelta?.payload;
  return p && typeof p === 'object' ? p : {};
}

export function getRewindMode(scelta, passo) {
  const p = getPayload(scelta);
  const o = passo?.opzioni_ui || {};
  return p.modalita_rewind || o.modalita_rewind || 'ramo';
}

export function getGruppoId(scelta, passo) {
  const p = getPayload(scelta);
  const o = passo?.opzioni_ui || {};
  return p.gruppo_id || o.gruppo_id || null;
}

export function getPresentazione(passo) {
  const o = passo?.opzioni_ui || {};
  return o.presentazione || 'pulsanti';
}

/** Estrae tutti gli effetti da una scelta (combo: campo + abilità + modello aura). */
export function buildEffettiFromScelta(scelta) {
  const tipo = scelta?.tipo_azione;
  const payload = getPayload(scelta);
  const effetti = [];

  const field = payload.field;
  if (field || tipo === 'imposta_campo') {
    effetti.push({
      tipo: 'imposta_campo',
      field: field || payload.field,
      sync_id: payload.sync_id,
      value: payload.value,
      prefettura_esterna: payload.prefettura_esterna,
    });
  }

  const abilitaIds = payload.abilita_sync_ids;
  if ((abilitaIds && abilitaIds.length) || tipo === 'aggiungi_abilita') {
    effetti.push({
      tipo: 'aggiungi_abilita',
      abilita_sync_ids: Array.isArray(abilitaIds) ? abilitaIds : [],
    });
  }

  if (payload.modello_aura_sync_id) {
    effetti.push({
      tipo: 'seleziona_modello_aura',
      modello_aura_sync_id: payload.modello_aura_sync_id,
    });
  }

  if (tipo === 'combo' && effetti.length === 0) {
    if (payload.abilita_sync_ids?.length) {
      effetti.push({ tipo: 'aggiungi_abilita', abilita_sync_ids: payload.abilita_sync_ids });
    }
    if (payload.field) {
      effetti.push({ tipo: 'imposta_campo', ...payload });
    }
  }

  return effetti.filter(Boolean);
}

export function nextSlugFromScelta(scelta) {
  if (scelta?.passo_destinazione_slug) return scelta.passo_destinazione_slug;
  const payload = getPayload(scelta);
  if (payload.passo_slug) return payload.passo_slug;
  if (scelta?.tipo_azione === 'naviga' && payload.passo_destinazione_slug) {
    return payload.passo_destinazione_slug;
  }
  if (['naviga', 'combo'].includes(scelta?.tipo_azione) && scelta?.passo_destinazione) {
    return scelta.passo_destinazione_slug;
  }
  return null;
}

export function flattenEffettiFromTrail(trail) {
  const out = [];
  for (const entry of trail || []) {
    for (const e of entry.effetti || []) {
      out.push(e);
    }
  }
  return out;
}

/**
 * Applica scelta aggiornando trail.
 * @returns {{ trail, effetti, navigareSlug, fine }}
 */
export function applySceltaToTrail(trail, passo, scelta) {
  const effetti = buildEffettiFromScelta(scelta);
  const gruppoId = getGruppoId(scelta, passo);
  const rewindMode = getRewindMode(scelta, passo);
  const passoSlug = passo?.slug;

  let nextTrail = [...(trail || [])];

  if (gruppoId && rewindMode === 'toggle') {
    nextTrail = nextTrail.filter(
      (t) => !(t.gruppoId === gruppoId && t.passoSlug === passoSlug),
    );
  } else if (gruppoId && rewindMode === 'ramo') {
    const idx = nextTrail.findIndex((t) => t.gruppoId === gruppoId && t.passoSlug === passoSlug);
    if (idx >= 0) nextTrail = nextTrail.slice(0, idx);
  }

  if (scelta?.tipo_azione !== 'fine' || effetti.length) {
    nextTrail.push({
      passoSlug,
      passoTitolo: passo?.titolo,
      sceltaId: scelta?.id,
      sceltaEtichetta: scelta?.etichetta,
      effetti,
      gruppoId,
      rewindMode,
    });
  }

  const navigareSlug = scelta?.tipo_azione === 'fine' ? null : nextSlugFromScelta(scelta);
  const fine = scelta?.tipo_azione === 'fine';

  return {
    trail: nextTrail,
    effetti: flattenEffettiFromTrail(nextTrail),
    navigareSlug,
    fine,
  };
}

/** Torna al passo trail[index] (incluso), scartando scelte successive. */
export function trailSliceToIndex(trail, index) {
  if (index < 0) return { trail: [], effetti: [] };
  const sliced = trail.slice(0, index + 1);
  return { trail: sliced, effetti: flattenEffettiFromTrail(sliced) };
}

export function trailSliceBeforePasso(trail, passoSlug) {
  const idx = trail.findIndex((t) => t.passoSlug === passoSlug);
  if (idx < 0) return { trail: [...trail], effetti: flattenEffettiFromTrail(trail) };
  return trailSliceToIndex(trail, idx - 1);
}

/** Aggiorna / aggiunge scelta modello aura nel trail (toggle sul passo corrente). */
export function applyModelloAuraToTrail(trail, passo, modelloSyncId, modelloNome) {
  const passoSlug = passo?.slug;
  let nextTrail = trail.filter(
    (t) => !(t.passoSlug === passoSlug && t.sceltaId === 'modello_aura'),
  );
  nextTrail.push({
    passoSlug,
    passoTitolo: passo?.titolo,
    sceltaId: 'modello_aura',
    sceltaEtichetta: modelloNome || 'Modello di aura',
    effetti: [{ tipo: 'seleziona_modello_aura', modello_aura_sync_id: modelloSyncId }],
    gruppoId: 'modello_aura',
    rewindMode: 'toggle',
  });
  return { trail: nextTrail, effetti: flattenEffettiFromTrail(nextTrail) };
}
