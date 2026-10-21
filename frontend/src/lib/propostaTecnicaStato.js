/** Stati proposta tecnica (infusione, tessitura, cerimoniale). */

export const STATO_PROPOSTA_BOZZA = 'BOZZA';
export const STATO_PROPOSTA_VALUTAZIONE = 'VALUTAZIONE';
export const STATO_PROPOSTA_APPROVATA = 'APPROVATA';
export const STATO_PROPOSTA_RIFIUTATA = 'RIFIUTATA';

/**
 * Bozza nuova o rifiuto legacy (admin impostava RIFIUTATA): il giocatore
 * può modificare e ripresentare. In valutazione e approvata sono bloccate.
 */
export function propostaModificabile(stato) {
  return stato == null || stato === STATO_PROPOSTA_BOZZA || stato === STATO_PROPOSTA_RIFIUTATA;
}

/** Sezione della lista giocatore. Il rifiuto esce da «valutazione» e torna in «bozze». */
export function sezioneProposta(proposta) {
  if (proposta?.stato === STATO_PROPOSTA_VALUTAZIONE) return 'valutazione';
  if (proposta?.stato === STATO_PROPOSTA_APPROVATA) return 'approvate';
  return 'bozze';
}

function testoNota(value) {
  return String(value || '').replace(/<[^>]*>/g, ' ').replace(/&nbsp;/g, ' ').trim();
}

/** Nota scritta dallo staff, nel campo legacy oppure nello storico datato. */
export function haNoteStaff(proposta) {
  if (testoNota(proposta?.note_staff)) return true;
  return (proposta?.note_log || []).some(
    (nota) => nota?.origine === 'STAFF' && testoNota(nota?.testo),
  );
}

export function etichettaStatoProposta(proposta) {
  if (proposta?.stato === STATO_PROPOSTA_VALUTAZIONE) return 'In valutazione';
  if (proposta?.stato === STATO_PROPOSTA_APPROVATA) return 'Approvata';
  if (haNoteStaff(proposta) || proposta?.stato === STATO_PROPOSTA_RIFIUTATA) return 'Bozza da rivedere';
  return 'Bozza';
}

export function propostaDaRivedere(proposta) {
  return sezioneProposta(proposta) === 'bozze' && (haNoteStaff(proposta) || proposta?.stato === STATO_PROPOSTA_RIFIUTATA);
}
