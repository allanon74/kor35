/**
 * Valore effettivo statistica per sigla (allineato a Personaggio.get_valore_statistica).
 */
export function getStatValueBySigla(characterData, punteggiList, sigla) {
  if (!characterData || !sigla) return 0;
  const target = String(sigla).toUpperCase();
  const stat = (punteggiList || []).find(
    (s) => String(s.sigla || '').toUpperCase() === target,
  );
  if (!stat?.nome) return 0;
  const base = Number(characterData.punteggi_base?.[stat.nome] ?? 0);
  const param = stat.parametro;
  const mod = param && characterData.modificatori_calcolati?.[param]
    ? characterData.modificatori_calcolati[param]
    : { add: 0, mol: 1 };
  return Math.round((base + (Number(mod.add) || 0)) * (Number(mod.mol) || 1));
}

export const DEFAULT_STIVA_ACCESS_STAT_SIGLA = '0IN';
