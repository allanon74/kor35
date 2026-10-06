/**
 * Caratteristiche di scheda PG vs catalogo tecnico (componenti nave, condizioni).
 *
 * In prod tipo CA contiene anche i 10 colori nave 0C0–0C9 (Nero, Bianco, Rosso, …):
 * servono come caratteristica_associata dei mattoni 0CP, non come Forza/Destrezza.
 * Le voci «Tier 2 - Forza» ecc. sono tipo CO (Condizione), non CA.
 */

export function isColoreComponenteNave(punteggio) {
  const sigla = String(punteggio?.sigla || '').toUpperCase();
  return /^0C\d$/.test(sigla);
}

export function isCaratteristicaPersonaggio(punteggio) {
  if (!punteggio || punteggio.tipo !== 'CA') return false;
  return !isColoreComponenteNave(punteggio);
}

export function caratteristichePersonaggio(punteggi = []) {
  return (punteggi || []).filter(isCaratteristicaPersonaggio);
}
