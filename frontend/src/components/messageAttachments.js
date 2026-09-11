import { formatImportiCessione, importiDaMessaggio } from '../utils/creditiCessione';

/**
 * Anteprima testuale degli allegati di un Messaggio (crediti / oggetti).
 */
export function getMessageAttachmentsSummary(msg) {
  if (!msg) return null;
  const { corrente, deposito } = importiDaMessaggio(msg);
  const oggetti = Array.isArray(msg.oggetti_allegati_snapshot)
    ? msg.oggetti_allegati_snapshot
    : [];
  const parts = [];
  const creditiLabel = formatImportiCessione(corrente, deposito);
  if (corrente > 0 || deposito > 0) {
    parts.push(creditiLabel);
  }
  if (oggetti.length > 0) {
    const names = oggetti
      .map((o) => (o && (o.nome || o.name)) || null)
      .filter(Boolean);
    if (names.length === oggetti.length && names.length <= 3) {
      parts.push(names.join(', '));
    } else if (names.length > 0 && names.length <= 3) {
      const rest = oggetti.length - names.length;
      parts.push(
        rest > 0
          ? `${names.join(', ')} +${rest} oggett${oggetti.length === 1 ? 'o' : 'i'}`
          : names.join(', ')
      );
    } else {
      parts.push(`${oggetti.length} oggett${oggetti.length === 1 ? 'o' : 'i'}`);
    }
  }
  if (!parts.length) return null;
  return parts.join(' · ');
}

export function messageHasAttachments(msg) {
  return Boolean(getMessageAttachmentsSummary(msg));
}
