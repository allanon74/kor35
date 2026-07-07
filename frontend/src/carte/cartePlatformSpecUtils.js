/**
 * Helper client per contratti Card Studio / Card Arena (allineati a carte_platform_specs.py).
 */

export function emptyPlayableCardSpec() {
  return {
    version: '1',
    source: 'kor35',
    gameplay: {},
    keywords: [],
    effects: [],
  };
}

export function buildPlayableSpecFromForm(form, espansioni = []) {
  const spec = emptyPlayableCardSpec();
  const esp = espansioni.find((e) => e.id === form.espansione);
  spec.gameplay = {
    codice: form.codice,
    nome: form.nome,
    tipo: form.tipo,
    energia: form.energia,
    rarita: form.rarita,
    costo_gioco: form.costo_gioco ?? 0,
    attacco: form.attacco,
    salute: form.salute,
    iniziativa: form.iniziativa,
    testo_gioco: form.testo_gioco || '',
    legale_duello: form.legale_duello !== false,
    bandita: !!form.bandita,
    duplicabile: !!form.duplicabile,
    layout_versione: form.layout_versione || 'STD',
  };
  if (form.effect_scripts?.length) {
    spec.effects = form.effect_scripts;
  }
  if (esp?.slug) {
    spec.espansione_slug = esp.slug;
  }
  return spec;
}
