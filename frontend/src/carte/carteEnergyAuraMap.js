/**
 * Mappatura energia carta → sigla aura (Punteggio tipo AU).
 * Deve restare allineata a CARTA_ENERGIA_AURA_SIGLA nel backend.
 */
export const CARTA_ENERGIA_AURA_SIGLA = {
  MAR: 'AMZ',
  TEC: 'ATE',
  INN: 'AIN',
  MAG: 'AMA',
  SAC: 'ASA',
  PSI: 'APS',
  ARC: 'AAR',
};

const FALLBACK_COLORS = {
  MAR: '#4C36F5',
  TEC: '#FAF610',
  INN: '#C79E0B',
  MAG: '#000000',
  SAC: '#FFFFFF',
  PSI: '#EFAAFF',
  ARC: '#92FA88',
};

export function buildTemaEnergieFromPunteggi(punteggiList = []) {
  const auras = (punteggiList || []).filter((p) => p.tipo === 'AU');
  const bySigla = new Map(auras.map((a) => [String(a.sigla || '').toUpperCase(), a]));
  const tema = {};
  Object.entries(CARTA_ENERGIA_AURA_SIGLA).forEach(([energia, sigla]) => {
    const aura = bySigla.get(sigla.toUpperCase());
    if (aura) {
      tema[energia] = {
        colore: aura.colore,
        nome: aura.nome,
        sigla: aura.sigla,
        icona_url: aura.icona_url || aura.icona,
      };
    } else {
      tema[energia] = {
        colore: FALLBACK_COLORS[energia],
        nome: energia,
        sigla,
        icona_url: null,
      };
    }
  });
  return tema;
}

export function mergeTemaEnergie(apiTema, punteggiList) {
  const fromApi = apiTema && Object.keys(apiTema).length ? { ...apiTema } : {};
  const fromPunteggi = buildTemaEnergieFromPunteggi(punteggiList);
  return { ...fromPunteggi, ...fromApi };
}
